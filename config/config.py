# -*- coding: utf-8 -*-
"""
龙虾调研助手 - 配置管理
===========================
统一管理 config.json（系统/用户配置）和 portfolio.json（持仓数据）。

用法：
  # 查看全部配置
  python config/config.py show

  # 查看某个分组
  python config/config.py show user
  python config/config.py show output

  # 设置配置项（用点号路径）
  python config/config.py set user.investment_style aggressive
  python config/config.py set output.report_style blue

  # 重置为默认值
  python config/config.py reset

  # ── 持仓管理 ──
  # 查看持仓
  python config/config.py portfolio show

  # 添加持仓
  python config/config.py portfolio add --code 000063 --name 中兴通讯 --cost 32.50 --shares 500

  # 删除持仓
  python config/config.py portfolio remove --code 000063

  # 更新账户信息
  python config/config.py portfolio account --total 80000 --cash 12000

  # 导出持仓（给持仓诊断报告用）
  python config/config.py portfolio export

  # 刷新持仓盈亏（拉取最新行情）
  python config/config.py portfolio refresh

  # ── 代码中使用 ──
  from config.config import get, get_portfolio, save, save_portfolio

  style = get("output.report_style")
  positions = get_portfolio()["positions"]
"""
from __future__ import annotations

import sys
import os
import io
import json
import copy
import argparse
from datetime import datetime
from typing import Any, Optional

# UTF-8
if getattr(sys.stdout, "encoding", None) != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════
# 路径
# ═══════════════════════════════════════════════════════════
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CONFIG_DIR)
_CONFIG_JSON = os.path.join(_CONFIG_DIR, "config.json")
_PORTFOLIO_JSON = os.path.join(_CONFIG_DIR, "portfolio.json")
_SETTINGS_JSON = os.path.join(_CONFIG_DIR, "settings.json")


# ═══════════════════════════════════════════════════════════
# 默认配置（首次初始化用）
# ═══════════════════════════════════════════════════════════
_DEFAULT_CONFIG = {
    "_version": "2.2",
    "_updated": "",
    "user": {
        "country": "CN",
        "language": "zh-CN",
        "investment_style": "value",
        "total_assets_range": "below_10w",
        "operation_freq": "short",
        "experience_level": "entry",
        "risk_level": "steady",
        "allow_cross_sector_switch": True,
    },
    "output": {
        "mode": "expert",
        "format": "markdown",
        "report_style": "blue",
        "color_type": "liquid",
        "layout": "rounded",
        "default_dir": "output",
    },
    "market": {
        "index_codes": {
            "sh000001": "上证指数",
            "sz399001": "深证成指",
            "sz399006": "创业板指",
            "sh000688": "科创50",
        },
        "focus_stocks": ["上证指数", "深证成指", "创业板指"],
        "focus_news_types": ["全球科技", "新能源", "AI"],
    },
    "api": {
        "timeout": 10,
        "search_fresh_seconds": 604800,
        "prosearch_base": "http://localhost:19000/proxy/prosearch/search",
        "headers": {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    },
    "system": {
        "run_mode": "skill",
        "encoding": "utf-8",
        "win_encoding": "gbk",
        "compress_data_context": False,
        "compress_agent_context": False,
    },
    "alone": {
        "output_mode": "cli",
        "preferred_api": "kimi",
    },
    "labels": {
        "investment_style": {
            "value": "价值(低估值、传统大盘蓝筹、稳业绩)",
            "growth": "成长(高景气赛道、高增速科技新兴行业)",
            "band": "波段(活跃度高、有箱体震荡、有资金轮动)",
            "trend": "趋势(有持续资金流入、走明确上升通道)",
        },
        "total_assets_range": {
            "below_10w": "10万以下",
            "10w_to_50w": "10-50万",
            "50w_to_100w": "50-100万",
            "above_100w": "100万以上",
        },
        "operation_freq": {
            "ultra_short": "超短线(1~5天)",
            "short": "短期(6~15天)",
            "medium": "中期(16~30天)",
            "long": "长期(30天以上)",
        },
        "experience_level": {
            "beginner": "小白(完全新手，几乎没投过理财/股票/基金)",
            "entry": "入门(1年以内零星投资，知道基础涨跌)",
            "intermediate": "进阶(1~3年经验，了解宏观/行业逻辑，会仓位配置)",
            "professional": "专业(3年以上，有完整交易体系与风控意识)",
        },
        "risk_level": {
            "conservative": "保守(±5%)",
            "steady": "稳健(±10%)",
            "aggressive": "积极(±18%)",
            "bold": "进取(±25%)",
        },
        "output_mode": {
            "normal": "普通",
            "expert": "专家",
        },
        "output_format": {
            "message": "消息",
            "markdown": "结构化文档",
            "pdf": "PDF文档",
        },
        "color_type": {
            "solid":    "纯色（纯色封面/纯白cover/纯色摘要）",
            "gradient": "渐变（渐变封面/纯白cover/渐变摘要）",
            "liquid":   "液态（渐变+光晕/毛玻璃cover/渐变摘要）",
        },
        "layout": {
            "rounded": "圆角（大圆角柔阴影）",
            "square":  "方正（直角弱阴影）",
            "minimal": "极简（无线无影无边框）",
        },
        "run_mode": {
            "skill": "Skill 模式（Agent 手动填充）",
            "alone": "Alone 模式（自动调用 LLM API）",
        },
        "alone_output_mode": {
            "cli": "CLI 纯文本输出",
            "report": "生成报告文件（HTML+PDF）",
        },
    },
    "delivery": {
        "enabled": False,
        "workbuddy_path": "",
        "openclaw_path": "",
    },
}

_DEFAULT_PORTFOLIO = {
    "_version": "3.0",
    "_updated": "",
    "account": {
        "total_assets": 0,
        "available_cash": 0,
        "currency": "CNY",
    },
    "positions": [],
    "summary": {
        "total_market_value": 0,
        "total_profit_loss": 0,
        "total_profit_loss_pct": 0,
        "position_count": 0,
    },
}


# ═══════════════════════════════════════════════════════════
# 核心读写函数（供代码 import 使用）
# ═══════════════════════════════════════════════════════════
def _load_json(path: str, default: dict) -> dict:
    """加载 JSON 文件，不存在则创建默认文件"""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    else:
        data = copy.deepcopy(default)
        data["_updated"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data


def _save_json(path: str, data: dict):
    """保存 JSON 文件"""
    data["_updated"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get(path: str = "", default: Any = None) -> Any:
    """
    读取配置项。支持点号路径。

    用法：
        get()                          → 全部配置 dict
        get("user")                    → user 分组 dict
        get("output.report_style")     → "liquid"
        get("user.investment_style")   → "balanced"
        get("non.exist", "fallback")   → "fallback"
    """
    cfg = _load_json(_CONFIG_JSON, _DEFAULT_CONFIG)
    if not path:
        return cfg
    keys = path.split(".")
    node = cfg
    for k in keys:
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            return default
    return node


def set_config(path: str, value: Any) -> bool:
    """
    设置配置项。支持点号路径。

    用法：
        set_config("user.investment_style", "aggressive")
        set_config("output.report_style", "blue")
    """
    cfg = _load_json(_CONFIG_JSON, _DEFAULT_CONFIG)
    keys = path.split(".")
    node = cfg
    for k in keys[:-1]:
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            print(f"❌ 路径无效: {path}（在 '{k}' 处断裂）")
            return False
    last_key = keys[-1]
    if not isinstance(node, dict):
        print(f"❌ 路径无效: {path}（'{last_key}' 的父级不是对象）")
        return False

    # 类型转换
    raw_value = value
    if isinstance(node.get(last_key), bool):
        raw_value = value.lower() in ("true", "1", "yes")
    elif isinstance(node.get(last_key), int):
        try:
            raw_value = int(value)
        except ValueError:
            try:
                raw_value = float(value)
            except ValueError:
                pass
    elif isinstance(node.get(last_key), float):
        try:
            raw_value = float(value)
        except ValueError:
            pass

    node[last_key] = raw_value
    _save_json(_CONFIG_JSON, cfg)
    return True


def save(data: dict):
    """直接覆盖整个 config.json（高级用法）"""
    _save_json(_CONFIG_JSON, data)


def get_portfolio() -> dict:
    """读取 portfolio.json 全部内容"""
    return _load_json(_PORTFOLIO_JSON, _DEFAULT_PORTFOLIO)


def save_portfolio(data: dict):
    """直接覆盖整个 portfolio.json"""
    _save_json(_PORTFOLIO_JSON, data)


def get_config_path() -> str:
    """返回 config.json 的绝对路径"""
    return os.path.abspath(_CONFIG_JSON)


def get_portfolio_path() -> str:
    """返回 portfolio.json 的绝对路径"""
    return os.path.abspath(_PORTFOLIO_JSON)


def get_settings_path() -> str:
    """返回 settings.json 的绝对路径"""
    return os.path.abspath(_SETTINGS_JSON)


def get_settings(path: str = "", default: Any = None) -> Any:
    """
    读取 settings.json 配置项。支持点号路径。

    用法：
        get_settings()                                → 全部 dict
        get_settings("websearch_pro")                 → websearch_pro 分组 dict
        get_settings("websearch_pro.engines.primary") → "360"
        get_settings("websearch_pro.apis.tavily_api_key") → API key
        get_settings("non.exist", "fallback")         → "fallback"
    """
    if os.path.exists(_SETTINGS_JSON):
        with open(_SETTINGS_JSON, encoding="utf-8") as f:
            settings = json.load(f)
    else:
        settings = {}
    if not path:
        return settings
    keys = path.split(".")
    node = settings
    for k in keys:
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            return default
    return node


def set_settings(path: str, value: Any) -> bool:
    """
    设置 settings.json 配置项。支持点号路径。

    用法：
        set_settings("websearch_pro.engines.primary", "bing")
        set_settings("websearch_pro.apis.tavily_api_key", "tvly-xxx")
    """
    if os.path.exists(_SETTINGS_JSON):
        with open(_SETTINGS_JSON, encoding="utf-8") as f:
            settings = json.load(f)
    else:
        settings = {"_version": "1.0", "_updated": "", "_description": "工具配置和 API Keys"}

    keys = path.split(".")
    node = settings
    for k in keys[:-1]:
        if isinstance(node, dict):
            node = node.setdefault(k, {})
        else:
            print(f"  路径无效: {path}（在 '{k}' 处断裂）")
            return False
    node[keys[-1]] = value
    settings["_updated"] = datetime.now().isoformat()
    with open(_SETTINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    return True


def save_settings(data: dict):
    """直接覆盖整个 settings.json"""
    data["_updated"] = datetime.now().isoformat()
    with open(_SETTINGS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_project_root() -> str:
    """返回项目根目录"""
    return _PROJECT_ROOT


# ═══════════════════════════════════════════════════════════
# 持仓操作函数
# ═══════════════════════════════════════════════════════════
def portfolio_add(code: str, name: str, cost_price: float, shares: int,
                  exchange: str = "", buy_date: str = "") -> bool:
    """添加一个持仓"""
    pf = get_portfolio()
    # 检查是否已存在
    for p in pf["positions"]:
        if p["code"] == code:
            print(f"❌ 已存在持仓: {code} {p['name']}，请先删除再添加")
            return False

    pos = {
        "code": code,
        "name": name,
        "exchange": exchange or _guess_exchange(code),
        "cost_price": round(cost_price, 3),
        "current_price": 0,
        "shares": int(shares),
        "market_value": 0,
        "profit_loss": 0,
        "profit_loss_pct": 0,
        "buy_date": buy_date or datetime.now().strftime("%Y-%m-%d"),
    }
    pos["market_value"] = round(pos["current_price"] * pos["shares"], 2)
    pf["positions"].append(pos)
    _recalc_summary(pf)
    save_portfolio(pf)
    return True


def portfolio_remove(code: str) -> bool:
    """删除一个持仓"""
    pf = get_portfolio()
    before = len(pf["positions"])
    pf["positions"] = [p for p in pf["positions"] if p["code"] != code]
    if len(pf["positions"]) == before:
        print(f"❌ 未找到持仓: {code}")
        return False
    _recalc_summary(pf)
    save_portfolio(pf)
    return True


def portfolio_update_account(total_assets: Optional[float] = None,
                             available_cash: Optional[float] = None) -> bool:
    """更新账户资金"""
    pf = get_portfolio()
    if total_assets is not None:
        pf["account"]["total_assets"] = round(total_assets, 2)
    if available_cash is not None:
        pf["account"]["available_cash"] = round(available_cash, 2)
    _recalc_summary(pf)
    save_portfolio(pf)
    return True


def portfolio_update_price(code: str, current_price: float) -> bool:
    """更新某个持仓的最新价"""
    pf = get_portfolio()
    for p in pf["positions"]:
        if p["code"] == code:
            p["current_price"] = round(current_price, 3)
            p["market_value"] = round(p["current_price"] * p["shares"], 2)
            p["profit_loss"] = round((p["current_price"] - p["cost_price"]) * p["shares"], 2)
            if p["cost_price"] > 0:
                p["profit_loss_pct"] = round(
                    (p["current_price"] - p["cost_price"]) / p["cost_price"] * 100, 2
                )
            _recalc_summary(pf)
            save_portfolio(pf)
            return True
    print(f"❌ 未找到持仓: {code}")
    return False


def portfolio_export() -> dict:
    """导出持仓数据（供持仓诊断报告使用）"""
    pf = get_portfolio()
    export = {
        "account": pf["account"],
        "positions": [],
        "summary": pf["summary"],
        "exported_at": datetime.now().isoformat(),
    }
    for p in pf["positions"]:
        export["positions"].append({
            "code": p["code"],
            "name": p["name"],
            "exchange": p["exchange"],
            "cost_price": p["cost_price"],
            "current_price": p["current_price"],
            "shares": p["shares"],
            "market_value": p["market_value"],
            "profit_loss": p["profit_loss"],
            "profit_loss_pct": p["profit_loss_pct"],
            "buy_date": p["buy_date"],
        })
    return export


def _recalc_summary(pf: dict):
    """重新计算持仓汇总"""
    total_mv = 0
    total_pl = 0
    total_cost = 0
    for p in pf["positions"]:
        total_mv += p["market_value"]
        total_pl += p["profit_loss"]
        total_cost += p["cost_price"] * p["shares"]
    pf["summary"]["total_market_value"] = round(total_mv, 2)
    pf["summary"]["total_profit_loss"] = round(total_pl, 2)
    pf["summary"]["total_profit_loss_pct"] = round(total_pl / total_cost * 100, 2) if total_cost > 0 else 0
    pf["summary"]["position_count"] = len(pf["positions"])


def _guess_exchange(code: str) -> str:
    """根据代码猜测交易所"""
    code = code.upper().replace(".SZ", "").replace(".SH", "")
    if code.isdigit():
        if code.startswith(("6", "5", "9")):
            return "SH"
        elif code.startswith(("0", "3", "2")):
            return "SZ"
        elif code.startswith(("4", "8")):
            return "BJ"
    return "SZ"


# ═══════════════════════════════════════════════════════════
# 持仓行情刷新（TaskRunner 调用）
# ═══════════════════════════════════════════════════════════
def refresh_portfolio_live() -> dict:
    """
    批量刷新所有持仓的最新价，计算盈亏，结果直接写回 portfolio.json。
    供 TaskRunner 在执行持仓诊断任务时调用。

    返回结构：
      {
        "success": True/False,
        "updated_count": N,       # 成功更新价格的数量
        "failed_count": N,
        "failed_codes": ["XXXX"], # 更新失败的代码
        "summary": { ... },        # 更新后的汇总
        "positions": [ ... ],      # 更新后的持仓明细（带最新价）
      }
    """
    pf = get_portfolio()
    if not pf["positions"]:
        return {"success": True, "updated_count": 0, "failed_count": 0,
                "failed_codes": [], "summary": pf["summary"], "positions": []}

    import urllib.request

    # 构造新浪行情批量查询 URL
    codes = []
    for p in pf["positions"]:
        exchange = p.get("exchange", "").lower()
        code = p["code"]
        if exchange == "sh":
            codes.append(f"sh{code}")
        elif exchange == "sz":
            codes.append(f"sz{code}")
        elif exchange == "bj":
            codes.append(f"bj{code}")
        else:
            codes.append(f"sz{code}")   # 默认深圳

    updated = 0
    failed_codes = []
    price_map = {}   # name -> price

    # 批量拉一次
    try:
        url = "https://hq.sinajs.cn/list=" + ",".join(codes)
        req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("gbk", errors="replace")

        for line in content.strip().split("\n"):
            if not line.strip():
                continue
            try:
                parts = line.split('"')
                if len(parts) < 2:
                    continue
                data_str = parts[1]
                fields = data_str.split(",")
                if len(fields) < 4:
                    continue
                name = fields[0]
                current_price = float(fields[3])   # 当前价
                price_map[name] = current_price
            except (ValueError, IndexError):
                continue

    except Exception as e:
        # 批量失败，用单股兜底
        price_map = {}

    # 更新每个持仓
    for p in pf["positions"]:
        price = price_map.get(p["name"]) or price_map.get(f"sh{p['code']}")

        # 兜底：逐个单独拉
        if price is None:
            try:
                exchange = p.get("exchange", "").lower()
                prefix = {"sh": "sh", "sz": "sz", "bj": "bj"}.get(exchange, "sz")
                single_url = f"https://hq.sinajs.cn/list={prefix}{p['code']}"
                req = urllib.request.Request(single_url,
                                              headers={"Referer": "https://finance.sina.com.cn"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw = resp.read().decode("gbk", errors="replace")
                fields = raw.split('"')[1].split(",")
                price = float(fields[3])
            except Exception:
                price = None

        if price and price > 0:
            p["current_price"] = round(price, 3)
            p["market_value"] = round(price * p["shares"], 2)
            p["profit_loss"] = round((price - p["cost_price"]) * p["shares"], 2)
            if p["cost_price"] > 0:
                p["profit_loss_pct"] = round(
                    (price - p["cost_price"]) / p["cost_price"] * 100, 2
                )
            updated += 1
        else:
            failed_codes.append(p["code"])

    _recalc_summary(pf)
    save_portfolio(pf)

    return {
        "success": updated > 0,
        "updated_count": updated,
        "failed_count": len(failed_codes),
        "failed_codes": failed_codes,
        "summary": pf["summary"],
        "positions": pf["positions"],
    }


# ═══════════════════════════════════════════════════════════
# CLI 显示辅助
# ═══════════════════════════════════════════════════════════
def _label(key: str, value: Any) -> str:
    """尝试把枚举值翻译成中文标签"""
    labels = get("labels", {})
    # 找对应的 label 组
    for group_name, group_labels in labels.items():
        if isinstance(group_labels, dict) and str(value) in group_labels:
            return group_labels[str(value)]
    return str(value)


def _format_value(value: Any, indent: int = 0) -> str:
    """格式化单个值用于显示"""
    prefix = "  " * indent
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if k.startswith("_"):
                continue
            label = _label(k, v)
            display = label if label != str(v) else str(v)
            if isinstance(v, dict):
                lines.append(f"{prefix}{k}: ")
                lines.append(_format_value(v, indent + 1))
            else:
                lines.append(f"{prefix}{k}: {display}")
        return "\n".join(lines)
    elif isinstance(value, list):
        if not value:
            return f"{prefix}（空）"
        lines = []
        for item in value:
            if isinstance(item, dict):
                for k, v in item.items():
                    lines.append(f"{prefix}  {k}: {v}")
            else:
                lines.append(f"{prefix}  - {item}")
        return "\n".join(lines)
    else:
        return f"{prefix}{value}"


# ═══════════════════════════════════════════════════════════
# CLI 命令处理
# ═══════════════════════════════════════════════════════════
def _cmd_show(section: str = ""):
    """显示配置"""
    cfg = get()
    if section:
        data = cfg.get(section)
        if data is None:
            print(f"❌ 未找到配置分组: {section}")
            print(f"   可用分组: {', '.join(k for k in cfg if not k.startswith('_'))}")
            return
    else:
        data = cfg

    print(f"\n{'='*50}")
    print(f"  🦞 龙虾调研助手 - 配置")
    print(f"  更新时间: {cfg.get('_updated', '未知')}")
    print(f"{'='*50}\n")
    print(_format_value(data))
    print()


def _cmd_set(path: str, value: str):
    """设置配置项"""
    ok = set_config(path, value)
    if ok:
        actual = get(path)
        label = _label(path.split(".")[-1], actual)
        display = label if label != str(actual) else str(actual)
        print(f"✅ 已设置 {path} = {display}")


def _cmd_reset():
    """重置为默认值"""
    _save_json(_CONFIG_JSON, copy.deepcopy(_DEFAULT_CONFIG))
    _save_json(_PORTFOLIO_JSON, copy.deepcopy(_DEFAULT_PORTFOLIO))
    print("✅ 配置已重置为默认值（包括持仓数据已清空）")


def _cmd_portfolio_show():
    """显示持仓"""
    pf = get_portfolio()
    acc = pf["account"]
    summary = pf["summary"]

    print(f"\n{'='*55}")
    print(f"  💼 持仓概览")
    print(f"  更新时间: {pf.get('_updated', '未知')}")
    print(f"{'='*55}\n")

    print(f"  📊 账户")
    print(f"     总资产:       ¥{acc['total_assets']:>12,.2f}")
    print(f"     可用资金:     ¥{acc['available_cash']:>12,.2f}")
    print(f"     持仓市值:     ¥{summary['total_market_value']:>12,.2f}")
    print(f"     总盈亏:       ¥{summary['total_profit_loss']:>12,.2f} ({summary['total_profit_loss_pct']:+.2f}%)")
    print(f"     持仓数量:     {summary['position_count']}")

    positions = pf["positions"]
    if not positions:
        print(f"\n  📭 暂无持仓")
    else:
        print(f"\n  {'代码':<10} {'名称':<10} {'成本价':>8} {'现价':>8} {'持仓量':>8} {'市值':>12} {'盈亏':>12} {'盈亏%':>8}")
        print(f"  {'─'*90}")
        for p in positions:
            pl_sign = "+" if p["profit_loss"] >= 0 else ""
            pl_pct_sign = "+" if p["profit_loss_pct"] >= 0 else ""
            print(f"  {p['code']:<10} {p['name']:<10} {p['cost_price']:>8.2f} {p['current_price']:>8.2f} "
                  f"{p['shares']:>8} {p['market_value']:>12,.2f} "
                  f"{pl_sign}{p['profit_loss']:>11,.2f} {pl_pct_sign}{p['profit_loss_pct']:>7.2f}%")
    print()


def _cmd_portfolio_add(args):
    """添加持仓"""
    cost = float(args.cost)
    shares = int(args.shares)
    exchange = args.exchange or ""
    buy_date = args.buy_date or ""
    ok = portfolio_add(args.code, args.name, cost, shares, exchange, buy_date)
    if ok:
        print(f"✅ 已添加持仓: {args.code} {args.name} × {shares}股，成本价 {cost}")


def _cmd_portfolio_remove(args):
    """删除持仓"""
    ok = portfolio_remove(args.code)
    if ok:
        print(f"✅ 已删除持仓: {args.code}")


def _cmd_portfolio_account(args):
    """更新账户"""
    total = float(args.total) if args.total else None
    cash = float(args.cash) if args.cash else None
    if total is None and cash is None:
        print("❌ 请至少指定 --total 或 --cash")
        return
    ok = portfolio_update_account(total, cash)
    if ok:
        pf = get_portfolio()
        acc = pf["account"]
        print(f"✅ 账户已更新: 总资产 ¥{acc['total_assets']:,.2f}，可用资金 ¥{acc['available_cash']:,.2f}")


def _cmd_portfolio_export(args):
    """导出持仓"""
    data = portfolio_export()
    output = args.output or "portfolio_export.json"
    output_path = os.path.join(_PROJECT_ROOT, output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ 持仓已导出: {output_path}")
    print(f"   包含 {data['summary']['position_count']} 个持仓，"
          f"总市值 ¥{data['summary']['total_market_value']:,.2f}")


def _cmd_portfolio_refresh(args):
    """刷新持仓行情（拉最新价）"""
    pf = get_portfolio()
    if not pf["positions"]:
        print("📭 暂无持仓，无需刷新")
        return

    print(f"🔄 正在刷新 {len(pf['positions'])} 个持仓的最新行情...")
    # 构造代码列表用于查询
    codes = []
    for p in pf["positions"]:
        full_code = f"{p['code']}.{p['exchange']}" if p.get("exchange") else p["code"]
        codes.append(full_code)

    try:
        # 尝试用新浪接口批量拉行情
        import urllib.request
        sina_url = "https://hq.sinajs.cn/list=" + ",".join(codes)
        req = urllib.request.Request(sina_url, headers={"Referer": "https://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("gbk")

        updated = 0
        for line in content.strip().split("\n"):
            if not line.strip():
                continue
            try:
                # 解析: var hq_str_sh000001="上证指数,3000.00,..."
                parts = line.split('"')
                if len(parts) < 2:
                    continue
                data_str = parts[1]
                fields = data_str.split(",")
                if len(fields) < 4:
                    continue
                name = fields[0]
                current_price = float(fields[3])  # 当前价
                # 匹配持仓
                for p in pf["positions"]:
                    if p["name"] == name or p["code"] in line:
                        p["current_price"] = current_price
                        p["market_value"] = round(current_price * p["shares"], 2)
                        p["profit_loss"] = round((current_price - p["cost_price"]) * p["shares"], 2)
                        if p["cost_price"] > 0:
                            p["profit_loss_pct"] = round(
                                (current_price - p["cost_price"]) / p["cost_price"] * 100, 2
                            )
                        updated += 1
                        break
            except (ValueError, IndexError):
                continue

        if updated > 0:
            _recalc_summary(pf)
            save_portfolio(pf)
            print(f"✅ 已刷新 {updated} 个持仓的最新行情")
            _cmd_portfolio_show()
        else:
            print("⚠️  未能解析到行情数据（可能是周末休市）")
            print("   提示: 可以手动用 portfolio price --code XXXX --price XX.XX 更新")

    except Exception as e:
        print(f"❌ 行情刷新失败: {e}")
        print("   提示: 可以手动用 portfolio price --code XXXX --price XX.XX 更新")


def _cmd_portfolio_price(args):
    """手动更新某个持仓的最新价"""
    ok = portfolio_update_price(args.code, float(args.price))
    if ok:
        p = None
        for pos in get_portfolio()["positions"]:
            if pos["code"] == args.code:
                p = pos
                break
        if p:
            sign = "+" if p["profit_loss"] >= 0 else ""
            pct_sign = "+" if p["profit_loss_pct"] >= 0 else ""
            print(f"  {p['code']} {p['name']} 现价更新为 {p['current_price']:.2f}")
            print(f"   盈亏: {sign}{p['profit_loss']:,.2f} ({pct_sign}{p['profit_loss_pct']:.2f}%)")


# ═══════════════════════════════════════════════════════════
# Settings 命令处理
# ═══════════════════════════════════════════════════════════
def _cmd_settings_show(section: str = ""):
    """显示工具配置"""
    settings = get_settings()
    if section:
        data = settings.get(section)
        if data is None:
            print(f"  未找到配置分组: {section}")
            available = [k for k in settings if not k.startswith("_")]
            print(f"   可用分组: {', '.join(available)}")
            return
    else:
        data = settings

    print(f"\n{'='*55}")
    print(f"  🛠 工具配置 (settings.json)")
    print(f"  更新时间: {settings.get('_updated', '未知')}")
    print(f"{'='*55}\n")
    print(_format_value(data))
    print()


def _cmd_settings_set(path: str, value: str):
    """设置工具配置项"""
    ok = set_settings(path, value)
    if ok:
        actual = get_settings(path)
        # API key 只显示前6位
        if isinstance(actual, str) and len(actual) > 12 and "key" in path.lower():
            display = actual[:6] + "..." + actual[-4:]
        else:
            display = str(actual)
        print(f"  已设置 {path} = {display}")


# ═══════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        prog="python config/config.py",
        description="🦞 龙虾调研助手 - 配置管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python config/config.py show
  python config/config.py show user
  python config/config.py set user.investment_style aggressive
  python config/config.py set output.report_style blue
  python config/config.py reset

  python config/config.py portfolio show
  python config/config.py portfolio add --code 000063 --name 中兴通讯 --cost 32.50 --shares 500
  python config/config.py portfolio remove --code 000063
  python config/config.py portfolio account --total 80000 --cash 12000
  python config/config.py portfolio export
  python config/config.py portfolio refresh
  python config/config.py portfolio price --code 000063 --price 36.38

  python config/config.py settings show
  python config/config.py settings show websearch_pro
  python config/config.py settings set websearch_pro.engines.primary bing
  python config/config.py settings set websearch_pro.apis.tavily_api_key tvly-xxx

  python config/config.py emu show
  python config/config.py emu ops
  python config/config.py emu reflect
  python config/config.py emu init
  python config/config.py emu reset

  python config/config.py set emu.enabled true
  python config/config.py set emu.follow_user_prefs true
  python config/config.py set emu.independent_capital 200000
        """
    )

    sub = parser.add_subparsers(dest="command")

    # show
    p_show = sub.add_parser("show", help="显示配置")
    p_show.add_argument("section", nargs="?", default="", help="配置分组（可选）")

    # set
    p_set = sub.add_parser("set", help="设置配置项")
    p_set.add_argument("path", help="配置路径，如 user.investment_style")
    p_set.add_argument("value", help="配置值")

    # reset
    sub.add_parser("reset", help="重置所有配置为默认值")

    # portfolio
    p_pf = sub.add_parser("portfolio", help="持仓管理")
    pf_sub = p_pf.add_subparsers(dest="pf_command")

    # portfolio show
    pf_sub.add_parser("show", help="查看持仓")

    # portfolio add
    p_add = pf_sub.add_parser("add", help="添加持仓")
    p_add.add_argument("--code", "-c", required=True, help="股票代码，如 000063")
    p_add.add_argument("--name", "-n", required=True, help="股票名称")
    p_add.add_argument("--cost", required=True, help="成本价")
    p_add.add_argument("--shares", "-s", required=True, help="持仓数量")
    p_add.add_argument("--exchange", "-e", default="", help="交易所（SZ/SH/BJ，可自动猜测）")
    p_add.add_argument("--buy-date", "-d", default="", help="买入日期（YYYY-MM-DD）")

    # portfolio remove
    p_rm = pf_sub.add_parser("remove", help="删除持仓")
    p_rm.add_argument("--code", "-c", required=True, help="股票代码")

    # portfolio account
    p_acc = pf_sub.add_parser("account", help="更新账户资金")
    p_acc.add_argument("--total", "-t", default=None, help="总资产")
    p_acc.add_argument("--cash", default=None, help="可用资金")

    # portfolio export
    p_exp = pf_sub.add_parser("export", help="导出持仓数据")
    p_exp.add_argument("--output", "-o", default="portfolio_export.json", help="输出文件名")

    # portfolio refresh
    pf_sub.add_parser("refresh", help="刷新持仓最新行情")

    # portfolio price
    p_price = pf_sub.add_parser("price", help="手动设置某个持仓的最新价")
    p_price.add_argument("--code", "-c", required=True, help="股票代码")
    p_price.add_argument("--price", "-p", required=True, help="最新价格")

    # settings
    p_st = sub.add_parser("settings", help="工具配置管理（API Keys 等）")
    st_sub = p_st.add_subparsers(dest="settings_command")

    p_st_show = st_sub.add_parser("show", help="查看工具配置")
    p_st_show.add_argument("section", nargs="?", default="", help="配置分组（如 websearch_pro）")

    p_st_set = st_sub.add_parser("set", help="设置工具配置项")
    p_st_set.add_argument("path", help="配置路径，如 websearch_pro.engines.primary")
    p_st_set.add_argument("value", help="配置值")

    # emu — 模拟持仓
    p_emu = sub.add_parser("emu", help="模拟持仓管理")
    emu_sub = p_emu.add_subparsers(dest="emu_command")
    emu_sub.add_parser("show", help="查看模拟持仓")
    emu_sub.add_parser("ops", help="查看操作记录")
    emu_sub.add_parser("reflect", help="运行反思复盘")
    emu_sub.add_parser("init", help="初始化模拟持仓")
    emu_sub.add_parser("reset", help="重置模拟持仓")

    args = parser.parse_args()

    if args.command == "show":
        _cmd_show(args.section)
    elif args.command == "set":
        _cmd_set(args.path, args.value)
    elif args.command == "reset":
        _cmd_reset()
    elif args.command == "portfolio":
        if args.pf_command == "show":
            _cmd_portfolio_show()
        elif args.pf_command == "add":
            _cmd_portfolio_add(args)
        elif args.pf_command == "remove":
            _cmd_portfolio_remove(args)
        elif args.pf_command == "account":
            _cmd_portfolio_account(args)
        elif args.pf_command == "export":
            _cmd_portfolio_export(args)
        elif args.pf_command == "refresh":
            _cmd_portfolio_refresh(args)
        elif args.pf_command == "price":
            _cmd_portfolio_price(args)
        else:
            p_pf.print_help()
    elif args.command == "settings":
        if args.settings_command == "show":
            _cmd_settings_show(args.section)
        elif args.settings_command == "set":
            _cmd_settings_set(args.path, args.value)
        else:
            p_st.print_help()
    elif args.command == "emu":
        try:
            _SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
            if _SCRIPTS_DIR not in sys.path:
                sys.path.insert(0, _SCRIPTS_DIR)
            from emu_manager import cmd_show, cmd_ops, cmd_reflect, cmd_reset
            from emu_manager import init_emu_portfolio
        except ImportError as e:
            print(f"❌ 模拟持仓模块未安装: {e}")
            return
        if args.emu_command == "show":
            cmd_show()
        elif args.emu_command == "ops":
            cmd_ops()
        elif args.emu_command == "reflect":
            cmd_reflect()
        elif args.emu_command == "init":
            init_emu_portfolio(force=True)
            print("✅ 模拟持仓已初始化")
        elif args.emu_command == "reset":
            cmd_reset()
        else:
            p_emu.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
