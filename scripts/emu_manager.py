# -*- coding: utf-8 -*-
"""
🦞 模拟持仓管理器 (Emu Manager)
================================
职责：管理模拟盘持仓、执行交易决策、记录操作、反思复盘、策略进化。

核心流程:
  1. 持仓诊断报告生成后 → 读取诊断建议
  2. 决策引擎 → 生成买卖操作
  3. 执行交易 → 更新模拟持仓
  4. 记录操作 → 记录盈亏
  5. 反思复盘 → 分析决策质量
  6. 策略进化 → 更新策略参数

数据文件（config/ 目录下持久化存储）:
  emu_portfolio.json   模拟盘当前持仓
  emu_operations.json  操作流水
  emu_reflections.json 反思复盘记录
"""

import os, sys, json, random
from datetime import datetime, date
from copy import deepcopy
from typing import Optional, List, Dict, Any, Tuple

# ── 项目根 ──
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

_CONFIG_DIR = os.path.join(_PROJECT_ROOT, "config")
from modules.logger import get_logger

log = get_logger("emu")


# ═══════════════════════════════════════════════════════════════════════
#  路径常量
# ═══════════════════════════════════════════════════════════════════════

EMU_PORTFOLIO_PATH     = os.path.join(_CONFIG_DIR, "emu_portfolio.json")
EMU_OPERATIONS_PATH    = os.path.join(_CONFIG_DIR, "emu_operations.json")
EMU_REFLECTIONS_PATH   = os.path.join(_CONFIG_DIR, "emu_reflections.json")

# ═══════════════════════════════════════════════════════════════════════
#  数据读写
# ═══════════════════════════════════════════════════════════════════════


def _read_json(path: str, default: dict = None) -> dict:
    """读 JSON 文件，不存在返回 default"""
    if not os.path.exists(path):
        return default or {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default or {}


def _write_json(path: str, data: dict):
    """写入 JSON 文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════════════════
#  Emu 配置
# ═══════════════════════════════════════════════════════════════════════


def get_emu_config() -> dict:
    """
    从 config.json 读取模拟盘配置。
    直接读取 JSON 文件（避免循环导入问题）。
    """
    config_path = os.path.join(_CONFIG_DIR, "config.json")
    config = _read_json(config_path, {})
    emu_cfg = config.get("emu", {})
    default = {
        "enabled": False,
        "follow_user_prefs": True,
        "independent_capital": 100000.0,
        "independent_freq": "short",
        "independent_style": "value",
        "independent_risk": "steady",
        "evolution": {"enabled": True},
    }
    # 合并默认值
    for k, v in default.items():
        if k not in emu_cfg:
            emu_cfg[k] = v
    return emu_cfg


def get_resolved_emu_config() -> dict:
    """
    解析最终生效的 Emu 配置：
    如果 follow_user_prefs=True，则从用户配置中读取资金/频率/风格/风险。
    否则使用独立配置。
    """
    emu = get_emu_config()
    config_path = os.path.join(_CONFIG_DIR, "config.json")
    config = _read_json(config_path, {})

    if not emu.get("enabled", False):
        return emu  # 未启用

    if emu.get("follow_user_prefs", True):
        user = config.get("user", {})
        assets_map = {
            "below_10w": 50000, "10w_to_50w": 200000,
            "50w_to_100w": 600000, "above_100w": 1000000,
        }
        assets = assets_map.get(user.get("total_assets_range", "below_10w"), 50000)
        emu["effective_capital"] = float(assets)
        emu["effective_freq"]    = user.get("operation_freq", "short")
        emu["effective_style"]   = user.get("investment_style", "value")
        emu["effective_risk"]    = user.get("risk_level", "steady")
    else:
        emu["effective_capital"] = emu.get("independent_capital", 100000.0)
        emu["effective_freq"]    = emu.get("independent_freq", "short")
        emu["effective_style"]   = emu.get("independent_style", "value")
        emu["effective_risk"]    = emu.get("independent_risk", "steady")

    return emu


# ═══════════════════════════════════════════════════════════════════════
#  仓位 & 参数工具
# ═══════════════════════════════════════════════════════════════════════


def _get_max_position_pct(risk_level: str) -> float:
    """根据风险等级返回单票最大仓位占比"""
    return {"conservative": 0.10, "steady": 0.20, "aggressive": 0.30, "bold": 0.40}.get(risk_level, 0.20)


def _get_max_sector_pct(risk_level: str) -> float:
    """根据风险等级返回单行业最大仓位占比"""
    return {"conservative": 0.20, "steady": 0.35, "aggressive": 0.50, "bold": 0.65}.get(risk_level, 0.35)


def _get_stop_loss_pct(risk_level: str) -> float:
    """根据风险等级返回止损比例"""
    return {"conservative": 0.05, "steady": 0.08, "aggressive": 0.12, "bold": 0.15}.get(risk_level, 0.08)


def _get_take_profit_pct(risk_level: str) -> float:
    """根据风险等级返回止盈比例"""
    return {"conservative": 0.08, "steady": 0.12, "aggressive": 0.18, "bold": 0.25}.get(risk_level, 0.12)


def _recalc_summary(pf: dict):
    """重新计算持仓汇总"""
    positions = pf.get("positions", [])
    total_mv = sum(p.get("market_value", 0) for p in positions)
    total_cost = sum(p.get("cost_price", 0) * p.get("shares", 0) for p in positions)
    total_pl = sum(p.get("profit_loss", 0) for p in positions)
    pf["summary"] = {
        "total_market_value": round(total_mv, 2),
        "total_profit_loss": round(total_pl, 2),
        "total_profit_loss_pct": round((total_pl / total_cost * 100) if total_cost else 0, 2),
        "position_count": len(positions),
    }
    # 更新 account
    cash = pf.get("account", {}).get("available_cash", 0)
    pf["account"]["total_assets"] = round(cash + total_mv, 2)


# ═══════════════════════════════════════════════════════════════════════
#  初始化：从用户持仓同步 / 按偏好创建
# ═══════════════════════════════════════════════════════════════════════


def init_emu_portfolio(force: bool = False) -> dict:
    """
    初始化模拟持仓：
    1. 如果已存在且未 force → 返回现有
    2. 如果有用户真实持仓 → 同步
    3. 没有 → 按用户偏好创建空仓
    """
    existing = _read_json(EMU_PORTFOLIO_PATH)
    if existing and not force:
        return existing  # 已有持仓，不覆盖

    emu_cfg = get_resolved_emu_config()
    if not emu_cfg.get("enabled", False):
        return {}

    # 尝试从用户真实持仓同步
    user_pf = _read_json(os.path.join(_CONFIG_DIR, "portfolio.json"))
    if user_pf and user_pf.get("positions"):
        log.info("📋 从用户真实持仓同步到模拟盘")
        pf = deepcopy(user_pf)
        pf["_meta"] = {"version": "1.0", "created": datetime.now().isoformat(), "source": "user_sync"}
        _write_json(EMU_PORTFOLIO_PATH, pf)

        # ── 记录初始建仓操作 ──
        ops = _read_json(EMU_OPERATIONS_PATH, {"_meta": {"version": "1.0"}, "operations": []})
        existing_codes = {op["code"] for op in ops.get("operations", []) if op.get("date")}
        for pos in pf.get("positions", []):
            if pos["code"] not in existing_codes:
                buy_cost = pos["cost_price"] * pos["shares"]
                ops["operations"].append({
                    "id": f"OP-INIT-{pos['code']}",
                    "date": pos.get("buy_date", pf.get("_meta", {}).get("created", "")[:10]),
                    "type": "buy",
                    "code": pos["code"], "name": pos["name"],
                    "price": pos["cost_price"], "shares": pos["shares"],
                    "amount": round(buy_cost, 2), "pl": 0,
                    "reason": "初始建仓（模拟验证，基于用户偏好配置）",
                    "task_id": "init_sync",
                })
        _write_json(EMU_OPERATIONS_PATH, ops)

        # ── 初始反思：建仓依据 ──
        refs = _read_json(EMU_REFLECTIONS_PATH, {"reflections": []})
        if not refs["reflections"]:
            emu_cfg_display = get_resolved_emu_config()
            style_label = {"value":"价值","growth":"成长","band":"波段","trend":"趋势"}.get(
                emu_cfg_display.get("effective_style",""), emu_cfg_display.get("effective_style",""))
            risk_label = {"conservative":"保守","steady":"稳健","aggressive":"积极","bold":"进取"}.get(
                emu_cfg_display.get("effective_risk",""), emu_cfg_display.get("effective_risk",""))
            pos_details = ", ".join([f"{p['name']}({p['code']}): {p['shares']}股@{p['cost_price']:.2f}"
                                      for p in pf["positions"]])
            refs["reflections"].append({
                "id": "REF-INIT",
                "date": date.today().isoformat(),
                "task_id": "init_sync",
                "type": "initialization",
                "note": f"模拟盘初始化：{pf['summary']['position_count']} 只持仓，"
                        f"总资产 {pf['account']['total_assets']:.0f} 元，"
                        f"风格={style_label}，风险={risk_label}。"
                        f"持仓: {pos_details}。"
                        f"初始策略：跟随用户真实持仓+偏好配置，"
                        f"后续通过诊断报告驱动调仓决策。",
                "performance": {
                    "trades_this_round": len(pf["positions"]),
                    "buys": len(pf["positions"]), "sells": 0,
                    "wins": 0, "losses": 0, "win_rate": 0,
                    "net_pnl": round(pf["summary"].get("total_profit_loss", 0), 2),
                    "closed_trades": 0,
                },
                "strategy_adjustments": {"aggressiveness": 1.0, "win_rate": 0.5, "total_trades": 0},
            })
            _write_json(EMU_REFLECTIONS_PATH, refs)
            log.info(f"📝 初始反思记录已创建")

        return pf

    # 按偏好创建空仓（仅有现金）
    capital = emu_cfg.get("effective_capital", 100000)
    pf = {
        "_meta": {"version": "1.0", "created": datetime.now().isoformat(), "source": "auto_create"},
        "account": {"total_assets": capital, "available_cash": capital, "currency": "CNY"},
        "positions": [],
        "summary": {"total_market_value": 0, "total_profit_loss": 0, "total_profit_loss_pct": 0, "position_count": 0},
    }
    _write_json(EMU_PORTFOLIO_PATH, pf)

    # ── 空仓也记一条初始反思 ──
    refs = _read_json(EMU_REFLECTIONS_PATH, {"reflections": []})
    if not refs["reflections"]:
        emu_cfg_display = get_resolved_emu_config()
        style_label = {"value":"价值","growth":"成长","band":"波段","trend":"趋势"}.get(
            emu_cfg_display.get("effective_style",""), emu_cfg_display.get("effective_style",""))
        risk_label = {"conservative":"保守","steady":"稳健","aggressive":"积极","bold":"进取"}.get(
            emu_cfg_display.get("effective_risk",""), emu_cfg_display.get("effective_risk",""))
        refs["reflections"].append({
            "id": "REF-INIT",
            "date": date.today().isoformat(),
            "task_id": "init_sync",
            "type": "initialization",
            "note": f"模拟盘初始化：空仓，总资产 {capital:.0f} 元，"
                    f"风格={style_label}，风险={risk_label}。"
                    f"初始策略：等待首次持仓诊断后建仓。",
            "performance": {"trades_this_round": 0, "buys": 0, "sells": 0,
                            "wins": 0, "losses": 0, "win_rate": 0,
                            "net_pnl": 0, "closed_trades": 0},
            "strategy_adjustments": {"aggressiveness": 1.0, "win_rate": 0.5, "total_trades": 0},
        })
        _write_json(EMU_REFLECTIONS_PATH, refs)
        log.info(f"📝 初始反思记录（空仓）已创建")

    log.info(f"💰 新建模拟持仓：{capital:.0f} 元")
    return pf


def sync_from_user_portfolio() -> dict:
    """从用户真实持仓同步最新行情"""
    user_pf = _read_json(os.path.join(_CONFIG_DIR, "portfolio.json"))
    emu_pf  = _read_json(EMU_PORTFOLIO_PATH)

    if not user_pf or not user_pf.get("positions"):
        log.info("ℹ️  用户无真实持仓，跳过同步")
        return emu_pf

    if not emu_pf:
        emu_pf = init_emu_portfolio()

    # 同步持仓数据（代码/名称/持仓量/成本价保持不变，价格从用户持仓取）
    user_pos = {p["code"]: p for p in user_pf["positions"]}
    for ep in emu_pf.get("positions", []):
        if ep["code"] in user_pos:
            up = user_pos[ep["code"]]
            ep["current_price"] = up.get("current_price", ep.get("current_price", 0))
            ep["market_value"] = round(ep["shares"] * ep["current_price"], 2)
            ep["profit_loss"] = round((ep["current_price"] - ep["cost_price"]) * ep["shares"], 2)
            ep["profit_loss_pct"] = round((ep["current_price"] - ep["cost_price"]) / ep["cost_price"] * 100, 2) if ep["cost_price"] else 0

    # 同步账户资金
    emu_pf["account"]["total_assets"] = user_pf.get("account", {}).get("total_assets", emu_pf["account"]["total_assets"])
    emu_pf["account"]["available_cash"] = user_pf.get("account", {}).get("available_cash", emu_pf["account"]["available_cash"])

    _recalc_summary(emu_pf)
    _write_json(EMU_PORTFOLIO_PATH, emu_pf)
    log.info("🔄 已从用户持仓同步行情")
    return emu_pf


# ═══════════════════════════════════════════════════════════════════════
#  交易决策引擎
# ═══════════════════════════════════════════════════════════════════════


def make_trading_decisions(diagnosis_data: dict, task_meta: dict = None) -> List[dict]:
    """
    根据持仓诊断报告生成交易决策。
    读取诊断报告中的建议 + 反思进化参数 → 生成具体操作。

    返回操作列表:
    [{"action": "buy"|"sell"|"hold", "code": "000063", "name": "...",
      "shares": 100, "reason": "...", "confidence": 0.8}, ...]
    """
    emu_cfg = get_resolved_emu_config()
    if not emu_cfg.get("enabled", False):
        return []

    pf = _read_json(EMU_PORTFOLIO_PATH)
    if not pf:
        return []

    # 读取反思进化参数
    reflections = _read_json(EMU_REFLECTIONS_PATH, {"reflections": []})
    evolution = _compute_evolution_params(reflections)

    # 从诊断报告中提取建议
    decisions = []
    sections = diagnosis_data.get("sections", [])

    # 查找"核心结论与执行清单"或"综合投资建议"章节
    for sec in sections:
        title = sec.get("title", "")
        if "结论" in title or "建议" in title or "执行" in title or "策略" in title:
            for sub in sec.get("subsections", []):
                content = sub.get("content", "")
                tables = []
                # 提取表格数据
                if sub.get("table"):
                    tables.append(sub["table"])
                # 解析内容
                parsed = _parse_diagnosis_content(content, tables, pf, emu_cfg, evolution)
                decisions.extend(parsed)

    # 如果没有解析到具体操作，按规则自动生成
    if not decisions:
        decisions = _auto_generate_decisions(pf, emu_cfg, evolution)

    return decisions


def _parse_diagnosis_content(content: str, tables: list, pf: dict,
                              cfg: dict, evolution: dict) -> List[dict]:
    """从诊断报告文本中解析出买卖操作"""
    decisions = []
    stop_loss = _get_stop_loss_pct(cfg.get("effective_risk", "steady"))
    evolution_factor = evolution.get("aggressiveness", 1.0)  # 进化因子

    # 检查现有持仓是否需要止损
    for pos in pf.get("positions", []):
        pl_pct = pos.get("profit_loss_pct", 0)
        if pl_pct < -stop_loss * 100 * evolution_factor:
            decisions.append({
                "action": "sell", "code": pos["code"], "name": pos["name"],
                "shares": pos["shares"],  # 全仓止损
                "reason": f"止损触发 (亏损{pl_pct:.1f}% > {stop_loss*100:.0f}%)",
                "confidence": 0.9,
            })

    # 从表格中解析操作建议
    for table in tables:
        rows = table.get("rows", [])
        for row in rows:
            if len(row) >= 4:
                op = str(row[0])
                cond = str(row[1])
                target = str(row[3]) if len(row) > 3 else ""
                if "买入" in op or "建仓" in op or "加仓" in op:
                    # 尝试从条件中提取股票
                    code, name = _extract_stock_from_cond(cond)
                    if code and name:
                        amount = _calc_buy_amount(pf, cfg, evolution)
                        price = _get_current_price(code)
                        if price and amount > 0:
                            shares = int(amount / price / 100) * 100
                            if shares > 0:
                                decisions.append({
                                    "action": "buy", "code": code, "name": name,
                                    "shares": shares, "price": price,
                                    "reason": f"诊断建议: {cond}",
                                    "confidence": 0.7,
                                })
                elif "卖出" in op or "减仓" in op or "清仓" in op:
                    code, name = _extract_stock_from_cond(cond)
                    if code and name:
                        pos = _find_position(pf, code)
                        if pos:
                            shares = pos["shares"] if "清仓" in op else pos["shares"] // 2
                            decisions.append({
                                "action": "sell", "code": code, "name": name,
                                "shares": shares,
                                "reason": f"诊断建议: {op}",
                                "confidence": 0.7,
                            })

    return decisions


def _auto_generate_decisions(pf: dict, cfg: dict, evolution: dict) -> List[dict]:
    """当诊断报告未明确操作时，按规则自动生成"""
    decisions = []
    max_pos_pct = _get_max_position_pct(cfg.get("effective_risk", "steady"))
    max_sector_pct = _get_max_sector_pct(cfg.get("effective_risk", "steady"))
    stop_loss = _get_stop_loss_pct(cfg.get("effective_risk", "steady"))
    evolution_factor = evolution.get("aggressiveness", 1.0)

    total = pf.get("account", {}).get("total_assets", 0)
    positions = pf.get("positions", [])
    total_mv = sum(p.get("market_value", 0) for p in positions)
    cash = pf.get("account", {}).get("available_cash", total - total_mv)

    # 止损检查
    for pos in positions:
        pl_pct = pos.get("profit_loss_pct", 0)
        if pl_pct < -stop_loss * 100 * evolution_factor:
            decisions.append({
                "action": "sell", "code": pos["code"], "name": pos["name"],
                "shares": pos["shares"],
                "reason": f"自动止损 ({pl_pct:.1f}%)",
                "confidence": 0.85,
            })

    # 单票超仓检查
    for pos in positions:
        pos_pct = pos.get("market_value", 0) / total if total else 0
        if pos_pct > max_pos_pct * 1.2:
            reduce_shares = int(pos["shares"] * (1 - max_pos_pct / pos_pct))
            reduce_shares = (reduce_shares // 100) * 100
            if reduce_shares > 0:
                decisions.append({
                    "action": "sell", "code": pos["code"], "name": pos["name"],
                    "shares": reduce_shares,
                    "reason": f"仓位过重 ({pos_pct*100:.0f}% > {max_pos_pct*100:.0f}%)",
                    "confidence": 0.75,
                })

    return decisions


def _extract_stock_from_cond(cond: str) -> Tuple[Optional[str], Optional[str]]:
    """从条件文本中提取股票代码和名称"""
    import re
    # 尝试匹配 6位代码
    m = re.search(r'(\d{6})', cond)
    code = m.group(1) if m else None
    # 尝试匹配中文名称（2-4个中文字符）
    m2 = re.search(r'([\u4e00-\u9fff]{2,4})', cond)
    name = m2.group(1) if m2 else None
    return code, name


def _find_position(pf: dict, code: str) -> Optional[dict]:
    for p in pf.get("positions", []):
        if p["code"] == code:
            return p
    return None


def _calc_buy_amount(pf: dict, cfg: dict, evolution: dict) -> float:
    """计算买入金额"""
    total = pf.get("account", {}).get("total_assets", 0)
    positions = pf.get("positions", [])
    cash = pf.get("account", {}).get("available_cash", 0)
    max_pos_pct = _get_max_position_pct(cfg.get("effective_risk", "steady"))
    # 单笔最多 max_pos_pct% 且不超过现金的 80%
    amount = min(total * max_pos_pct * 0.5, cash * 0.8)
    return max(amount, 0)


def _get_current_price(code: str) -> Optional[float]:
    """获取股票当前价格（从 ticktime 模块）"""
    try:
        from scripts.ticktime import get_realtime_stock
        data = get_realtime_stock(code)
        if data:
            return data.get("price") or data.get("current_price")
    except Exception:
        pass
    return None


def _compute_evolution_params(reflections: dict) -> dict:
    """
    从反思记录中计算进化参数。
    这些参数影响交易决策的激进程度。
    """
    refs = reflections.get("reflections", [])
    if not refs:
        return {"aggressiveness": 1.0, "win_rate": 0.5, "total_trades": 0}

    total_trades = sum(r.get("performance", {}).get("trades_this_round", 0) for r in refs)
    total_wins = sum(r.get("performance", {}).get("wins", 0) for r in refs)
    total_losses = sum(r.get("performance", {}).get("losses", 0) for r in refs)
    win_rate = total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0.5

    # 进化因子：胜率越高越激进（但对冲，不超 1.5 倍）
    aggressiveness = min(1.0 + (win_rate - 0.5) * 0.5, 1.5)
    # 连续亏损降低激进程度
    recent_refs = refs[-3:]
    recent_losses = sum(1 for r in recent_refs if r.get("performance", {}).get("wins", 0) < r.get("performance", {}).get("losses", 0))
    if recent_losses >= 2:
        aggressiveness = max(aggressiveness * 0.8, 0.6)

    return {
        "aggressiveness": round(aggressiveness, 2),
        "win_rate": round(win_rate, 2),
        "total_trades": total_trades,
    }


# ═══════════════════════════════════════════════════════════════════════
#  执行交易
# ═══════════════════════════════════════════════════════════════════════


def execute_decisions(decisions: List[dict], task_id: str = "") -> dict:
    """执行交易决策，更新模拟持仓，记录操作"""
    if not decisions:
        return {"executed": 0, "skipped": 0}

    pf = _read_json(EMU_PORTFOLIO_PATH)
    if not pf:
        return {"error": "模拟持仓未初始化"}

    ops = _read_json(EMU_OPERATIONS_PATH, {"_meta": {"version": "1.0"}, "operations": []})
    op_id_counter = len(ops.get("operations", [])) + 1

    executed = 0
    skipped = 0

    for dec in decisions:
        action = dec.get("action")
        code = dec.get("code")
        name = dec.get("name")
        shares = dec.get("shares", 0)
        price = dec.get("price", 0)
        reason = dec.get("reason", "")

        if not code or shares <= 0:
            skipped += 1
            continue

        if action == "sell":
            # 查找持仓并卖出
            pos = _find_position(pf, code)
            if not pos or pos["shares"] < shares:
                skipped += 1
                continue

            # 获取当前价格
            current_price = price or _get_current_price(code)
            if not current_price or current_price == 0:
                # 尝试从持仓取
                current_price = pos.get("current_price", pos["cost_price"])

            sell_amount = round(current_price * shares, 2)
            pl = round((current_price - pos["cost_price"]) * shares, 2)

            # 更新持仓
            pos["shares"] -= shares
            pos["market_value"] = round(pos["shares"] * current_price, 2)
            pos["profit_loss"] = round((current_price - pos["cost_price"]) * pos["shares"], 2)
            pos["profit_loss_pct"] = round((current_price - pos["cost_price"]) / pos["cost_price"] * 100, 2) if pos["cost_price"] else 0

            # 更新现金
            pf["account"]["available_cash"] = round(pf["account"]["available_cash"] + sell_amount, 2)

            # 记录操作
            ops["operations"].append({
                "id": f"OP-{op_id_counter:04d}",
                "date": date.today().isoformat(),
                "type": "sell", "code": code, "name": name,
                "price": round(current_price, 2), "shares": shares,
                "amount": sell_amount, "pl": round(pl, 2),
                "reason": reason, "task_id": task_id,
            })
            op_id_counter += 1

            # 移除空仓
            if pos["shares"] <= 0:
                pf["positions"] = [p for p in pf["positions"] if p["code"] != code]

            executed += 1
            log.info(f"📉 卖出 {name}({code}): {shares}股 × {current_price:.2f} = {sell_amount:.0f}")

        elif action == "buy":
            # 获取当前价格
            current_price = price or _get_current_price(code)
            if not current_price or current_price == 0:
                skipped += 1
                continue

            buy_cost = round(current_price * shares, 2)
            cash = pf["account"]["available_cash"]
            if buy_cost > cash:
                # 调整买入量
                shares = int(cash / current_price / 100) * 100
                buy_cost = round(current_price * shares, 2)
                if shares <= 0:
                    skipped += 1
                    continue

            # 检查是否已有持仓
            existing = _find_position(pf, code)
            if existing:
                # 加仓：加权平均成本
                total_cost = existing["cost_price"] * existing["shares"] + current_price * shares
                total_shares = existing["shares"] + shares
                existing["cost_price"] = round(total_cost / total_shares, 2)
                existing["shares"] = total_shares
                existing["current_price"] = current_price
                existing["market_value"] = round(current_price * total_shares, 2)
                existing["profit_loss"] = round((current_price - existing["cost_price"]) * total_shares, 2)
                existing["profit_loss_pct"] = round((current_price - existing["cost_price"]) / existing["cost_price"] * 100, 2) if existing["cost_price"] else 0
            else:
                # 新建持仓
                pf["positions"].append({
                    "code": code, "name": name,
                    "exchange": "SZ" if not code.startswith(("6", "5", "9")) else "SH",
                    "cost_price": round(current_price, 2),
                    "current_price": current_price,
                    "shares": shares,
                    "market_value": buy_cost,
                    "profit_loss": 0,
                    "profit_loss_pct": 0,
                    "buy_date": date.today().isoformat(),
                })

            # 扣减现金
            pf["account"]["available_cash"] = round(pf["account"]["available_cash"] - buy_cost, 2)

            # 记录操作
            ops["operations"].append({
                "id": f"OP-{op_id_counter:04d}",
                "date": date.today().isoformat(),
                "type": "buy", "code": code, "name": name,
                "price": round(current_price, 2), "shares": shares,
                "amount": buy_cost, "pl": 0,
                "reason": reason, "task_id": task_id,
            })
            op_id_counter += 1
            executed += 1
            log.info(f"📈 买入 {name}({code}): {shares}股 × {current_price:.2f} = {buy_cost:.0f}")

    # 重新计算汇总
    _recalc_summary(pf)

    # 保存
    _write_json(EMU_PORTFOLIO_PATH, pf)
    _write_json(EMU_OPERATIONS_PATH, ops)

    log.info(f"✅ 交易执行完成: {executed} 笔成功, {skipped} 笔跳过")
    return {"executed": executed, "skipped": skipped}




# ═══════════════════════════════════════════════════════════════════════
#  反思与进化
# ═══════════════════════════════════════════════════════════════════════


def run_reflection(task_id: str = "") -> dict:
    """运行反思复盘，分析交易质量，更新进化参数"""
    cfg = get_emu_config()
    if not cfg.get("evolution", {}).get("enabled", True):
        return {"reflected": False, "reason": "evolution_disabled"}

    ops_data = _read_json(EMU_OPERATIONS_PATH, {"operations": []})
    pf = _read_json(EMU_PORTFOLIO_PATH)
    refs_data = _read_json(EMU_REFLECTIONS_PATH, {"reflections": []})

    operations = ops_data.get("operations", [])
    # 只分析最近一次诊断后的操作
    recent_ops = [op for op in operations if op.get("task_id") == task_id] if task_id else operations[-10:]

    if not recent_ops:
        return {"reflected": False, "reason": "no_recent_ops"}

    # 统计
    buys = [op for op in recent_ops if op["type"] == "buy"]
    sells = [op for op in recent_ops if op["type"] == "sell"]
    closed_pl = [op.get("pl", 0) for op in sells if op.get("pl") is not None]
    wins = sum(1 for pl in closed_pl if pl > 0)
    losses = sum(1 for pl in closed_pl if pl < 0)

    net_pnl = sum(closed_pl)
    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0

    # 生成反思文本
    ref_note = ""
    mistakes = []
    improvements = []

    if net_pnl < 0:
        ref_note = f"本轮回合亏损 {net_pnl:.0f} 元，需审视止损纪律和执行准确性。"
        mistakes.append("止损执行不及时")
        improvements.append("收紧止损线，触发即执行")
    else:
        ref_note = f"本轮回合盈利 {net_pnl:.0f} 元，胜率 {win_rate*100:.0f}%。"
        if win_rate < 0.5:
            mistakes.append("胜率不足 50%")
            improvements.append("减少交易频率，提高选股质量")
        else:
            improvements.append("保持当前策略框架")

    # 检查错误类型
    for dec in recent_ops:
        if dec.get("type") == "sell" and dec.get("pl", 0) > 0 and dec.get("reason", "").startswith("止损"):
            mistakes.append(f"过早止损 {dec['name']}")
            improvements.append("给予持仓更宽波动容忍度")

    # 记录反思
    reflection = {
        "id": f"REF-{len(refs_data['reflections']) + 1:04d}",
        "date": date.today().isoformat(),
        "task_id": task_id,
        "note": ref_note,
        "mistakes": mistakes,
        "improvements": improvements,
        "performance": {
            "trades_this_round": len(recent_ops),
            "buys": len(buys),
            "sells": len(sells),
            "wins": wins, "losses": losses,
            "win_rate": round(win_rate, 2),
            "net_pnl": round(net_pnl, 2),
            "closed_trades": len(closed_pl),
        },
        "strategy_adjustments": _compute_evolution_params(refs_data),
    }

    refs_data["reflections"].append(reflection)
    _write_json(EMU_REFLECTIONS_PATH, refs_data)
    log.info(f"🧠 反思完成: {ref_note}")
    return reflection


# ═══════════════════════════════════════════════════════════════════════
#  一键执行：持仓诊断 → 交易 → 复盘 → 进化
# ═══════════════════════════════════════════════════════════════════════


def run_full_cycle(diagnosis_data: dict, task_meta: dict = None) -> dict:
    """
    完整模拟盘周期：
    1. 检查是否启用
    2. 初始化/同步持仓
    3. 生成交易决策
    4. 执行交易
    5. 反思复盘
    """
    cfg = get_emu_config()
    if not cfg.get("enabled", False):
        return {"enabled": False, "reason": "emu_disabled"}

    task_id = task_meta.get("task_id", "") if task_meta else ""
    log.section("🦞 模拟持仓周期")

    # 初始化/同步
    pf = init_emu_portfolio()
    sync_from_user_portfolio()

    # 生成决策
    decisions = make_trading_decisions(diagnosis_data, task_meta)
    if not decisions:
        log.info("ℹ️  无交易决策")
        return {"decisions": 0, "executed": 0}

    log.info(f"📋 生成 {len(decisions)} 条交易决策")

    # 执行交易
    result = execute_decisions(decisions, task_id)

    # 反思
    reflection = run_reflection(task_id)

    # 获取进化参数
    evolution = _compute_evolution_params(_read_json(EMU_REFLECTIONS_PATH, {"reflections": []}))

    return {
        "decisions": len(decisions),
        "executed": result.get("executed", 0),
        "skipped": result.get("skipped", 0),
        "reflection_id": reflection.get("id", "") if isinstance(reflection, dict) else "",
        "aggressiveness": evolution.get("aggressiveness", 1.0),
        "win_rate": evolution.get("win_rate", 0),
    }


# ═══════════════════════════════════════════════════════════════════════
#  CLI 入口
# ═══════════════════════════════════════════════════════════════════════


def cmd_show():
    """显示模拟持仓"""
    pf = _read_json(EMU_PORTFOLIO_PATH)
    if not pf or not pf.get("positions"):
        pf = init_emu_portfolio()
    if not pf or not pf.get("positions"):
        print("📭 模拟持仓为空")
        return

    print(f"\n{'='*60}")
    print(f"  模拟持仓 ({pf.get('_meta',{}).get('source','?')})")
    print(f"{'='*60}")
    print(f"  总资产: {pf['account']['total_assets']:.2f}")
    print(f"  可用现金: {pf['account']['available_cash']:.2f}")
    print(f"  持仓数: {pf['summary']['position_count']} 只")
    print(f"  总盈亏: {pf['summary']['total_profit_loss']:+.2f} ({pf['summary']['total_profit_loss_pct']:+.2f}%)")
    print(f"\n  {'代码':<8} {'名称':<10} {'成本':<8} {'现价':<8} {'持仓':<6} {'市值':<10} {'盈亏%':<8}")
    print(f"  {'-'*58}")
    for p in pf.get("positions", []):
        print(f"  {p['code']:<8} {p['name']:<10} {p['cost_price']:<8.2f} {p['current_price']:<8.2f} "
              f"{p['shares']:<6} {p['market_value']:<10.2f} {p['profit_loss_pct']:+.2f}%")
    print()


def cmd_ops(limit: int = 10):
    """显示操作记录"""
    ops = _read_json(EMU_OPERATIONS_PATH, {"operations": []})
    recent = ops.get("operations", [])[-limit:]
    if not recent:
        print("📭 无操作记录")
        return
    print(f"\n{'='*70}")
    print(f"  最近 {len(recent)} 条操作")
    print(f"{'='*70}")
    for op in reversed(recent):
        arrow = "📈" if op["type"] == "buy" else "📉"
        pl_str = f" ({op['pl']:+.0f})" if op.get("pl") else ""
        print(f"  {arrow} {op['date']} {op['name']}({op['code']}) "
              f"{'买入' if op['type']=='buy' else '卖出'} {op['shares']}股 "
              f"@{op['price']:.2f} = {op['amount']:.0f}{pl_str}")
        if op.get("reason"):
            print(f"     原因: {op['reason']}")
    print()


def cmd_reflect():
    """运行反思"""
    result = run_reflection()
    if isinstance(result, dict):
        print(f"  🧠 {result.get('note', '完成')}")


def cmd_reset():
    """重置模拟持仓"""
    if os.path.exists(EMU_PORTFOLIO_PATH):
        os.remove(EMU_PORTFOLIO_PATH)
    if os.path.exists(EMU_OPERATIONS_PATH):
        os.remove(EMU_OPERATIONS_PATH)
    if os.path.exists(EMU_REFLECTIONS_PATH):
        os.remove(EMU_REFLECTIONS_PATH)
    print("✅ 模拟持仓已重置")
    init_emu_portfolio(force=True)
    print("✅ 已重新初始化")


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "show":
        cmd_show()
    elif cmd == "ops":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_ops(limit)
    elif cmd == "reflect":
        cmd_reflect()
    elif cmd == "reset":
        cmd_reset()
    elif cmd == "init":
        init_emu_portfolio(force=True)
        print("✅ 已初始化")
    else:
        print(f"未知命令: {cmd}")
        print("可用命令: show, ops, reflect, reset, init")
