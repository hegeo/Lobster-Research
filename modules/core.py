# -*- coding: utf-8 -*-
"""
龙虾调研助手 - 核心算法与基础常量（精简优化版）
【2026-04-17 优化】从1756行精简至~400行，保留核心算法，提升AI Agent性能

核心保留模块：
1. 信号灯体系（量化阈值）
2. 均线系统趋势判定
3. 情绪雷达六维
4. 五维个股评分
5. 红线预警检测
6. 入场时机判定
7. 三维选股框架
8. 基础计算工具
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════
#  一、信号灯体系（量化阈值版）
# ═══════════════════════════════════════════════════════════════════════

CHANGE_THRESHOLDS = {"strong_up": 1.0, "strong_down": -1.0}

def signal_emoji_change(pct: float) -> str:
    """涨跌信号灯：>1%🟢 <-1%🔴 其他🟡"""
    if pct > CHANGE_THRESHOLDS["strong_up"]: return "🟢"
    if pct < CHANGE_THRESHOLDS["strong_down"]: return "🔴"
    return "🟡"

def signal_emoji_level(value: float, thresholds: tuple) -> str:
    """通用三级信号灯 (低阈值, 高阈值)"""
    low, high = thresholds
    if value < low: return "🟢"
    if value > high: return "🔴"
    return "🟡"

def pe_signal(pe: float, industry_pe: float = None) -> str:
    """估值信号"""
    if pe is None: return "🟡"
    if industry_pe and pe < industry_pe * 0.8: return "🟢低估"
    if pe < 20: return "🟢偏低"
    if pe < 40: return "🟡合理"
    return "🔴偏高"

# ═══════════════════════════════════════════════════════════════════════
#  二、核心计算工具
# ═══════════════════════════════════════════════════════════════════════

def calc_rsi_approx(prev_close: float, price: float) -> float:
    """RSI估算（简化版）"""
    if not prev_close or prev_close == 0: return 50.0
    daily_chg = (price - prev_close) / prev_close * 100
    if abs(daily_chg) < 0.5: return 50.0
    return min(80.0, max(20.0, 50 + daily_chg * 4))

def calc_chg_from_high_low(price: float, high: float, low: float) -> tuple:
    """距52周高低点百分比"""
    if not high or not low or high == low: return 0.0, 0.0
    return round((price - high) / high * 100, 2), round((price - low) / low * 100, 2)

def normalize_code(code: str) -> tuple:
    """股票代码 → (完整代码, 交易所前缀)"""
    code = str(code).strip().upper()
    if code.startswith(("6", "9")): return code, "sh"
    if code.startswith(("0", "3")): return code, "sz"
    if code.startswith(("4", "8")): return code, "bj"
    if len(code) <= 5 and code.isdigit(): return code, "hk"
    return code, "us"

def tencent_full_code(code: str, exchange: str = None) -> str:
    """生成腾讯行情完整代码"""
    if not exchange:
        code, exchange = normalize_code(code)
    prefix = {"sh": "sh", "sz": "sz", "hk": "hk", "us": "us"}.get(exchange.lower(), "sh")
    return f"{prefix}{code}"

# ═══════════════════════════════════════════════════════════════════════
#  三、均线系统趋势判定（核心算法）
# ═══════════════════════════════════════════════════════════════════════

MA_SYSTEM = {
    "sticky_threshold_pct": 3.0,    # 均线粘合阈值
    "volume_ratio_healthy": 1.2,   # 放量标准
    "volume_ratio_weak": 0.8,      # 缩量标准
}

TREND_POSITION = {
    "强趋势（上涨）": (80, 100, "持有，回调加仓"),
    "震荡（区间）":   (40, 60,  "控仓，高抛低吸"),
    "下跌趋势":       (0, 20,    "离场或极小试探"),
    "混沌（无方向）": (0, 0,     "空仓观望"),
}

def trend_by_ma_system(price: float, ma5: float, ma10: float, ma20: float,
                       ma60: float = None, ma120: float = None,
                       vol5: float = None, vol20: float = None) -> dict:
    """
    均线系统趋势判定
    返回: {trend_type, signal, position_range, basis, vol_signal}
    """
    all_ma = [x for x in [price, ma5, ma10, ma20, ma60, ma120] if x is not None]

    # 判断排列
    is_bullish = len(all_ma) >= 3 and all(all_ma[i] >= all_ma[i+1] for i in range(len(all_ma)-1))
    is_bearish = len(all_ma) >= 3 and all(all_ma[i] <= all_ma[i+1] for i in range(len(all_ma)-1))

    # 均线粘合
    sticky = False
    if ma5 and ma20 and ma20 != 0:
        sticky = abs(ma5 - ma20) / ma20 * 100 < MA_SYSTEM["sticky_threshold_pct"]

    # 量能判断
    vol_signal = "🟡"
    if vol5 and vol20 and vol20 > 0:
        ratio = vol5 / vol20
        vol_signal = "🟢" if ratio >= MA_SYSTEM["volume_ratio_healthy"] else ("🔴" if ratio <= MA_SYSTEM["volume_ratio_weak"] else "🟡")

    # 综合判定
    if is_bullish and not sticky:
        trend_type, signal = "强趋势（上涨）", "🟢"
    elif is_bearish and not sticky:
        trend_type, signal = "下跌趋势", "🔴"
    elif sticky:
        trend_type, signal = "震荡（区间）", "🟡"
    else:
        trend_type, signal = "混沌（无方向）", "⚫"

    pos = TREND_POSITION.get(trend_type, (40, 60, "观望"))

    return {
        "trend_type": trend_type,
        "signal": signal,
        "trend_emoji": signal,
        "position_range": pos[:2],
        "basis": f"{'多头' if is_bullish else ('空头' if is_bearish else ('粘合' if sticky else '混沌'))}排列，{vol_signal}量能",
        "vol_signal": vol_signal,
    }

# ═══════════════════════════════════════════════════════════════════════
#  四、情绪雷达六维（核心算法）
# ═══════════════════════════════════════════════════════════════════════

SENTIMENT_RADAR = {
    "up_down_ratio": {"bull": 2.0, "overheat": 4.0, "bear": 1.0},
    "limit_up_down": {"up_healthy": 50, "up_overheat": 150, "down_danger": 50},
    "consecutive_boards": {"healthy_min": 5, "overheat_max": 8, "weak_max": 3},
    "explode_rate": {"healthy_max": 30, "danger_max": 40},
    "yesterday_limit_perf": {"healthy_min": 2.0, "overheat_min": 5.0, "danger_max": 0.0},
    "margin_change": {"healthy_max": 5, "overheat_min": 10, "cold_max": -10},
}

def sentiment_radar(up_down_ratio: float = None, limit_up: int = None, limit_down: int = None,
                    consecutive_boards: int = None, explode_rate: float = None,
                    yesterday_limit_perf: float = None, margin_change_pct: float = None) -> dict:
    """
    情绪雷达六维指标
    返回: {signals: [(维度, 数值, 信号灯, 说明)], overall: 综合判断, action: 操作建议}
    """
    cfg = SENTIMENT_RADAR
    signals = []

    # 1. 涨跌家数比
    if up_down_ratio is not None:
        if up_down_ratio >= cfg["up_down_ratio"]["overheat"]: sig, label = "🔴", f"过热({up_down_ratio}:1)"
        elif up_down_ratio >= cfg["up_down_ratio"]["bull"]: sig, label = "🟢", f"健康({up_down_ratio}:1)"
        elif up_down_ratio < cfg["up_down_ratio"]["bear"]: sig, label = "🔴", f"过冷({up_down_ratio}:1)"
        else: sig, label = "🟡", f"中性({up_down_ratio}:1)"
        signals.append(("涨跌家数比", f"{up_down_ratio}:1", sig, label))

    # 2. 涨跌停家数
    if limit_up is not None or limit_down is not None:
        if limit_up and limit_up >= cfg["limit_up_down"]["up_overheat"]: sig, label = "🔴", f"涨停过热({limit_up}家)"
        elif limit_up and limit_up >= cfg["limit_up_down"]["up_healthy"]: sig, label = "🟢", f"涨停健康({limit_up}家)"
        elif limit_down and limit_down >= cfg["limit_up_down"]["down_danger"]: sig, label = "🔴", f"跌停危险({limit_down}家)"
        else: sig, label = "🟡", f"中性(涨{limit_up or 0}/跌{limit_down or 0}家)"
        signals.append(("涨跌停", f"{limit_up or 0}/{limit_down or 0}", sig, label))

    # 3. 连板高度
    if consecutive_boards is not None:
        t = cfg["consecutive_boards"]
        if consecutive_boards >= t["overheat_max"]: sig, label = "🔴", f"过热({consecutive_boards}板)"
        elif consecutive_boards >= t["healthy_min"]: sig, label = "🟢", f"健康({consecutive_boards}板)"
        else: sig, label = "🔴", f"弱势({consecutive_boards}板)"
        signals.append(("连板高度", f"{consecutive_boards}板", sig, label))

    # 4. 炸板率
    if explode_rate is not None:
        t = cfg["explode_rate"]
        if explode_rate >= t["danger_max"]: sig, label = "🔴", f"危险({explode_rate}%)"
        elif explode_rate <= t["healthy_max"]: sig, label = "🟢", f"健康({explode_rate}%)"
        else: sig, label = "🟡", f"中性({explode_rate}%)"
        signals.append(("炸板率", f"{explode_rate}%", sig, label))

    # 5. 昨日涨停今表现
    if yesterday_limit_perf is not None:
        t = cfg["yesterday_limit_perf"]
        if yesterday_limit_perf >= t["overheat_min"]: sig, label = "🔴", f"过热(+{yesterday_limit_perf}%)"
        elif yesterday_limit_perf >= t["healthy_min"]: sig, label = "🟢", f"健康(+{yesterday_limit_perf}%)"
        elif yesterday_limit_perf < t["danger_max"]: sig, label = "🔴", f"危险({yesterday_limit_perf}%)"
        else: sig, label = "🟡", f"中性({yesterday_limit_perf}%)"
        signals.append(("昨日涨停表现", f"{yesterday_limit_perf}%", sig, label))

    # 6. 融资余额变化
    if margin_change_pct is not None:
        t = cfg["margin_change"]
        if margin_change_pct >= t["overheat_min"]: sig, label = "🔴", f"过热(+{margin_change_pct}%)"
        elif abs(margin_change_pct) <= t["healthy_max"]: sig, label = "🟢", f"健康(±{t['healthy_max']}%内)"
        elif margin_change_pct <= t["cold_max"]: sig, label = "🔴", f"过冷({margin_change_pct}%)"
        else: sig, label = "🟡", f"中性({margin_change_pct}%)"
        signals.append(("融资余额变化", f"{margin_change_pct}%", sig, label))

    # 综合评估
    red = sum(1 for s in signals if "🔴" in s[2])
    green = sum(1 for s in signals if "🟢" in s[2])

    if red >= 4: overall, action = "过热", "降低仓位，规避高风险"
    elif green >= 4: overall, action = "健康", "可积极参与"
    elif red >= 2: overall, action = "偏冷", "控制仓位，谨慎开新仓"
    elif green >= 2: overall, action = "偏暖", "适度参与，回调买入"
    else: overall, action = "中性", "控仓观望"

    return {"signals": signals, "overall": overall, "action": action}

# ═══════════════════════════════════════════════════════════════════════
#  五、五维个股量化评分（核心算法）
# ═══════════════════════════════════════════════════════════════════════

FIVE_DIM_WEIGHTS = {"trend": 0.30, "fundamental": 0.25, "valuation": 0.20, "fund": 0.15, "catalyst": 0.10}

def five_dim_stock_score(price: float, ma20: float, ma60: float,
                         industry_rank_pct: float = None,
                         roe: float = None, profit_growth: float = None,
                         pe: float = None, pe_hist_pct: float = None, industry_pe: float = None,
                         main_flow_20d: float = None, north_change_pct: float = None,
                         has_earning_event: bool = False, has_policy_event: bool = False, 
                         has_order_event: bool = False) -> dict:
    """
    五维个股量化评分
    档位: ≥80核心仓位 | 60-79卫星 | 40-59观察 | <40强制替换
    """
    # 1. 趋势评分(30)
    trend_score = 30 if price > ma60 else (18 if price > ma20 else 5)
    if trend_score == 30 and industry_rank_pct and industry_rank_pct <= 30:
        trend_logic = [f"价格>MA60,行业前{int(industry_rank_pct)}%"]
    else:
        trend_logic = ["价格>MA60" if trend_score == 30 else ("价格>MA20" if trend_score == 18 else "价格<MA20")]

    # 2. 基本面评分(25)
    fund_score = 0
    if roe:
        fund_score += 12 if roe >= 15 else (8 if roe >= 10 else (4 if roe >= 5 else 0))
    if profit_growth:
        fund_score += 8 if profit_growth >= 30 else (5 if profit_growth >= 10 else (2 if profit_growth >= 0 else 0))
    fund_score = min(25, fund_score)
    fund_logic = [f"ROE={roe}%" if roe else "", f"利润增速={profit_growth}%" if profit_growth else ""]

    # 3. 估值评分(20)
    val_score = 0
    if pe_hist_pct is not None:
        val_score = 20 if pe_hist_pct <= 30 else (15 if pe_hist_pct <= 50 else (10 if pe_hist_pct <= 70 else (5 if pe_hist_pct <= 80 else 0)))
        if pe and industry_pe and industry_pe > 0:
            ratio = pe / industry_pe
            if ratio < 0.7: val_score = min(20, val_score + 3)
            elif ratio > 1.5: val_score = max(0, val_score - 5)
    val_logic = [f"PE历史{pe_hist_pct}%分位" if pe_hist_pct is not None else ""]

    # 4. 资金评分(15)
    fund_m_score, inflow = 0, 0
    if main_flow_20d and main_flow_20d > 0:
        fund_m_score, inflow = 10, inflow + 1
    if north_change_pct and north_change_pct > 0:
        fund_m_score, inflow = min(15, fund_m_score + 5), inflow + 1
    if inflow == 0: fund_m_score = 0
    fund_m_logic = [f"主力净流入{main_flow_20d}亿" if main_flow_20d else "", f"北向+{north_change_pct}%" if north_change_pct else ""]

    # 5. 催化剂评分(10)
    catalyst_count = sum([has_earning_event, has_policy_event, has_order_event])
    catalyst_score = 10 if catalyst_count >= 3 else (7 if catalyst_count == 2 else (4 if catalyst_count == 1 else 0))
    catalyst_logic = [e for e, v in [("业绩", has_earning_event), ("政策", has_policy_event), ("订单", has_order_event)] if v]

    # 加权总分
    total = min(100, round(trend_score * 0.30 + fund_score * 0.25 + val_score * 0.20 + fund_m_score * 0.15 + catalyst_score * 0.10))

    # 档位
    tier = "核心仓位" if total >= 80 else ("卫星仓位" if total >= 60 else ("观察仓位" if total >= 40 else "强制替换"))
    action = {"核心仓位": "🟢可超配至20%", "卫星仓位": "🟢标准配置10%", "观察仓位": "🟡减仓至5%或替换", "强制替换": "🔴必须替换"}[tier]

    return {
        "total": total, "tier": tier, "signal": tier[0].replace("核","🟢").replace("卫","🟢").replace("观","🟡").replace("强","🔴"),
        "action": action,
        "dimensions": [
            ("趋势质量", trend_score, 30, trend_logic),
            ("基本面健康", fund_score, 25, fund_logic),
            ("估值安全垫", val_score, 20, val_logic),
            ("资金共识", fund_m_score, 15, fund_m_logic),
            ("催化剂密度", catalyst_score, 10, catalyst_logic),
        ]
    }

# ═══════════════════════════════════════════════════════════════════════
#  六、红线预警检测（核心算法）
# ═══════════════════════════════════════════════════════════════════════

RED_LINE = {"single_over": 25, "sector_over": 40, "cash_under": 5, "portfolio_dd": 20, "score_min": 40}

def red_line_check(stock_count: int, cash_pct: float, max_single: float, max_sector: float,
                   total_pnl: float = None, stock_scores: list = None) -> dict:
    """
    红线预警检测
    触发即强制处理
    """
    alerts = []

    if max_single > RED_LINE["single_over"]:
        alerts.append({"level": "🔴", "item": "个股集中", "value": f"{max_single}%", "action": f"减仓至≤{RED_LINE['single_over']-5}%"})

    if max_sector > RED_LINE["sector_over"]:
        alerts.append({"level": "🔴", "item": "行业集中", "value": f"{max_sector}%", "action": "启动板块轮换"})

    if cash_pct < RED_LINE["cash_under"]:
        alerts.append({"level": "🔴", "item": "现金不足", "value": f"{cash_pct}%", "action": "必须减仓释放现金"})

    if stock_scores:
        forced = [{"code": c, "score": s} for c, s in stock_scores if s < RED_LINE["score_min"]]
        if forced:
            alerts.append({"level": "🔴", "item": "低评分个股", "value": f"{len(forced)}只", "action": "强制替换", "replacements": forced})

    return {"is_safe": len(alerts) == 0, "alerts": alerts, "alert_count": len(alerts), "risk_level": "极高" if len(alerts) >= 3 else ("高" if alerts else "正常")}

# ═══════════════════════════════════════════════════════════════════════
#  七、持仓健康评分
# ═══════════════════════════════════════════════════════════════════════

def portfolio_score(stock_count: int, cash_pct: float, max_single: float,
                    max_sector: float, total_pnl: float) -> tuple:
    """五维持仓健康评分，返回: (总得分, 各维度得分, 评级)"""
    scores = [
        ("集中度", 20 if 5 <= stock_count <= 15 else (10 if stock_count < 5 else max(0, 20 - (stock_count - 15) * 2))),
        ("现金比例", 20 if cash_pct >= 20 else (15 if cash_pct >= 10 else max(0, int(cash_pct * 1.5)))),
        ("个股集中", 20 if max_single <= 15 else (15 if max_single <= 20 else max(0, 20 - (max_single - 20) * 2))),
        ("行业分散", 20 if max_sector <= 25 else (15 if max_sector <= 35 else max(0, 20 - (max_sector - 35)))),
        ("浮动盈亏", 20 if total_pnl >= 20 else (15 if total_pnl >= 5 else (10 if total_pnl >= 0 else max(0, int(10 + total_pnl))))),
    ]
    total = sum(s[1] for s in scores)
    rating = "极优" if total >= 85 else ("良好" if total >= 70 else ("一般" if total >= 55 else "较差"))
    return total, scores, rating

# ═══════════════════════════════════════════════════════════════════════
#  八、入场时机判定（核心算法）
# ═══════════════════════════════════════════════════════════════════════

def entry_timing_check(enter_ind_phase: bool = False, enter_earn_accel: bool = False,
                       enter_reverse: bool = False, enter_expectation: bool = False,
                       avoid_post_event: bool = False, avoid_sentiment_peak: bool = False,
                       avoid_tech_breakdown: bool = False, avoid_fund_worsening: bool = False) -> dict:
    """
    入场时机判定矩阵
    满足≥2个入场信号 → 可积极建仓
    满足≥1个回避信号 → 降仓/离场
    两者同时满足 → 回避优先
    """
    enter = [e for e, v in [("产业爆发前", enter_ind_phase), ("业绩加速前", enter_earn_accel), 
                            ("困境反转前", enter_reverse), ("预期修复前", enter_expectation)] if v]
    avoid = [a for a, v in [("业绩兑现后", avoid_post_event), ("情绪高潮后", avoid_sentiment_peak),
                            ("技术破位后", avoid_tech_breakdown), ("预期恶化后", avoid_fund_worsening)] if v]

    if len(avoid) >= 2: conclusion, position, level = "强烈建议回避", (0, 20), "🔴"
    elif len(avoid) == 1: conclusion, position, level = "建议减仓", (20, 40), "🔴"
    elif len(enter) >= 3: conclusion, position, level = "强烈建议建仓", (60, 80), "🟢"
    elif len(enter) >= 2: conclusion, position, level = "可积极建仓", (50, 70), "🟢"
    elif len(enter) == 1: conclusion, position, level = "可考虑建仓", (30, 50), "🟡"
    else: conclusion, position, level = "观望为主", (20, 40), "🟡"

    return {
        "enter_signals": enter, "avoid_signals": avoid,
        "conclusion": conclusion, "position_range": position, "level": level,
        "timing_score": len(enter) - len(avoid)
    }

# ═══════════════════════════════════════════════════════════════════════
#  九、三维选股框架
# ═══════════════════════════════════════════════════════════════════════

def assess_industry_cycle(penetration: float, growth: float) -> dict:
    """评估产业生命周期阶段"""
    if penetration < 10 and growth > 50: return {"stage": "爆发期", "emoji": "🟢", "action": "重仓布局"}
    elif 10 <= penetration <= 30 and growth > 30: return {"stage": "成长期", "emoji": "🟢", "action": "优选龙头"}
    elif penetration > 30 and growth > 10: return {"stage": "成熟期", "emoji": "🟡", "action": "波段操作"}
    else: return {"stage": "衰退期", "emoji": "🔴", "action": "坚决回避"}

def assess_competition_pattern(market_share: float, price_power: bool, has_moat: bool) -> dict:
    """评估竞争格局"""
    if market_share >= 40 or (market_share >= 20 and price_power and has_moat):
        return {"pattern": "垄断/寡头", "emoji": "🟢", "action": "首选，长期持有"}
    elif has_moat and market_share >= 10:
        return {"pattern": "差异化竞争", "emoji": "🟡", "action": "次选，关注迭代"}
    else:
        return {"pattern": "同质化竞争", "emoji": "🔴", "action": "回避，价格战"}

def assess_validation_stage(revenue_growth: float, profit_growth: float) -> dict:
    """评估业绩验证阶段"""
    if revenue_growth <= 0: return {"stage": "概念期", "emoji": "🔴", "action": "不参与"}
    elif profit_growth <= 0 and revenue_growth > 0: return {"stage": "放量期", "emoji": "🟢", "action": "核心持仓"}
    elif profit_growth >= revenue_growth and revenue_growth > 20: return {"stage": "利润期", "emoji": "🟡", "action": "持有为主"}
    else: return {"stage": "成熟期", "emoji": "🟡", "action": "收息配置"}

def calc_expectation_differential(market_exp: str, your_judgment: str) -> str:
    """预期差分析"""
    mapping = {
        ("乐观", "更乐观"): "重仓买入", ("乐观", "中性"): "回避", ("乐观", "悲观"): "做空或回避",
        ("中性", "乐观"): "买入（最佳机会）", ("中性", "悲观"): "回避",
        ("悲观", "乐观"): "逆向买入", ("悲观", "更悲观"): "坚决回避",
    }
    return mapping.get((market_exp, your_judgment), "中性观望")

# ═══════════════════════════════════════════════════════════════════════
#  十、目标价估算
# ═══════════════════════════════════════════════════════════════════════

def estimate_target_price(price: float, pe_current: float, pe_target: float = None,
                          pb_current: float = None, pb_target: float = None, roe: float = None) -> dict:
    """综合目标价估算"""
    results = []
    if pe_target and pe_current and pe_current > 0:
        results.append(("PE估值", round(price * pe_target / pe_current, 2), 50))
    if pb_target and roe and roe > 0 and pb_current and pb_current > 0:
        results.append(("PB-ROE", round(price / pb_current * pb_target, 2), 30))
    if pb_target and pb_current and pb_current > 0 and not roe:
        results.append(("PB估值", round(price / pb_current * pb_target, 2), 20))

    if not results: return {"target_price": price, "upside": 0, "method": "无足够数据"}

    total_weight = sum(r[2] for r in results)
    weighted = sum(r[1] * r[2] for r in results) / total_weight
    upside = round((weighted - price) / price * 100, 2)

    return {
        "target_price": round(weighted, 2), "upside": upside,
        "methods": [(r[0], r[1], f"{r[2]}%") for r in results]
    }

# ═══════════════════════════════════════════════════════════════════════
#  十一、常量配置
# ═══════════════════════════════════════════════════════════════════════

INDUSTRY_STOCKS = {
    "AI算力/CPO": ["300308", "300502", "300394", "002281"],
    "半导体":     ["002371", "688012", "688396", "603986"],
    "锂电/储能":  ["300750", "300014", "300274", "002594"],
    "液冷/数据中心": ["002837", "603171", "300820"],
    "消费电子":   ["002475", "000725", "688007"],
    "军工":       ["600893", "002025", "300699"],
    "黄金/有色":  ["601899", "600547", "000975"],
    "煤炭":       ["601088", "601225", "600188"],
    "石油石化":   ["600028", "600971", "601857"],
    "医药":       ["600276", "000538", "300760"],
    "白酒":       ["600519", "000858", "603369"],
    "房地产":     ["000002", "001979", "600048"],
    "银行":       ["600036", "601398", "601328"],
    "非银金融":   ["600030", "300059", "601688"],
    "光伏":       ["300274", "601012", "002459"],
    "汽车零部件": ["002594", "300124", "601799"],
    "AI软件":     ["300059", "002230", "300496"],
    "通信设备":   ["000063", "600570", "002463"],
    "军工电子":   ["002025", "600760", "002916"],
    "化工":       ["600309", "002064", "601216"],
}

ETF_THRESHOLDS = {
    "min_scale_yi": 5, "min_daily_vol_yi": 0.5, "max_fee_pct": 0.6,
    "max_tracking_err": 0.3, "max_premium_pct": 3.0, "max_mini_scale_yi": 2,
}

INVESTMENT_RATINGS = {
    "🔥买入": (">20%", "积极建仓"), "✅增持": ("10-20%", "适度参与"),
    "⚪中性": ("-10%~10%", "观望为主"), "❌减持": ("<-10%", "降低仓位"),
}

SPECIAL_MODES = {
    "crisis": {"vix_gt": 30, "drop_gt": 5.0},
    "euphoria": {"greed_gt": 90, "margin_pct_gt": 90},
    "bottom": {"erp_pct_gt": 90, "volume_pct_lt": 50},
}

def special_mode_detect(vix: float = None, single_day_drop: float = None,
                        greed_index: float = None, margin_pct: float = None,
                        erp_pct: float = None, volume_pct: float = None) -> dict:
    """特殊模式检测：危机/狂热/磨底"""
    cfg = SPECIAL_MODES
    results = {}

    # 危机模式
    crisis = (vix and vix > cfg["crisis"]["vix_gt"]) or (single_day_drop and single_day_drop < -cfg["crisis"]["drop_gt"])
    results["crisis"] = {"triggered": crisis, "action": "清仓/降至20%仓位" if crisis else "标准仓位"}

    # 狂热模式
    euphoria = (greed_index and greed_index > cfg["euphoria"]["greed_gt"]) or (margin_pct and margin_pct > cfg["euphoria"]["margin_pct_gt"])
    results["euphoria"] = {"triggered": euphoria, "action": "分批止盈" if euphoria else "标准仓位"}

    # 磨底模式
    bottom = erp_pct and volume_pct and erp_pct > cfg["bottom"]["erp_pct_gt"] and volume_pct < cfg["bottom"]["volume_pct_lt"]
    results["bottom"] = {"triggered": bottom, "action": "逆向布局" if bottom else "标准仓位"}

    return results
