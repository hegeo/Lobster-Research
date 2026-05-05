# -*- coding: utf-8 -*-
"""
龙虾调研助手 - 研报模板扩展库
（本文件供 OUTPUT_MODE=normal 时使用，模板路径统一管理，方便扩展）

新增研报类型步骤（只需改本文件）：
  1. 在 REPORT_TYPES 中添加一条 entry
  2. 在本文件末尾添加对应的 TEMPLATE_XXX 模板字符串
  3. 无需改动 core.py 或任何调用方

【2026-04-16 优化】基于投资经验框架更新，新增：
  - 三维选股框架常量（INDUSTRY_LIFECYCLE / COMPETITION_PATTERNS / VALIDATION_STAGES）
  - 预期差分析（EXPECTATION_DIFFERENTIAL）
  - 入场时机判定（ENTRY_TIMING / AVOID_TIMING）
  - 投资纪律铁律（INVESTMENT_DISCIPLINE）
  - 信息层级（INFO_HIERARCHY）
  - 仓位分配标准（POSITION_STANDARDS）
  - 行为误区检测（BEHAVIORAL_BIASES）
  - 更新LOBSTER_QUOTES语料库
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════
#  研报类型注册表
# ═══════════════════════════════════════════════════════════
# key = 内部 ID（英文）
# label = 用户可见中文名称
# trigger_keywords = 命中关键词（任意一个即触发）
# template_key = 对应模板变量名（不含 TEMPLATE_ 前缀）
# mode_hint = 建议模式（normal=普通/expert=专家/free=均可）
# risk_note = 风险说明（None=受用户风险级别约束）
# 字数基准 = 估算字数，用于提示

REPORT_TYPES = {
    "kuaisu_kuaibao": {
        "label":         "快速快报",
        "trigger_keywords": ["快报", "今日速览", "市场概要", "今日行情一句话", "速览"],
        "template_key":  "BULLETIN",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~800字",
    },
    "dapan_ribao": {
        "label":         "大盘日报",
        "trigger_keywords": ["大盘分析", "市场日报", "今日行情", "上证", "创业板", "科创", "大盘"],
        "template_key":  "MARKET_DAILY",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~3000字",
    },
    "gegu_fenxi": {
        "label":         "个股深度分析",
        "trigger_keywords": ["分析股票", "个股诊断", "帮我看", "走势", "个股", "股票"],
        "template_key":  "STOCK_ANALYSIS",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~3000字",
    },
    "chicang_fenxi": {
        "label":         "持仓诊断",
        "trigger_keywords": ["持仓分析", "诊断持仓", "我的持仓", "持仓诊断"],
        "template_key":  "PORTFOLIO",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~2500字",
    },
    "kuaixuan_xuangu": {
        "label":         "快速选股",
        "trigger_keywords": ["快速选股", "今日推荐", "买什么", "选股"],
        "template_key":  "STOCK_PICK",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~2000字",
    },
    "kuazichan_fenxi": {
        "label":         "跨资产联动",
        "trigger_keywords": ["黄金", "比特币", "美元", "宏观", "跨资产", "BTC", "DXY"],
        "template_key":  "CROSS_ASSET",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~2000字",
    },
    "hangye_baogao": {
        "label":         "行业研报",
        "trigger_keywords": ["行业分析", "行业研究", "XXX行业", "行业研报", "板块"],
        "template_key":  "INDUSTRY",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~4000字",
    },
    "qiye_baogao": {
        "label":         "企业研报",
        "trigger_keywords": ["企业研报", "尽调", "商业尽调", "调查", "企业调查", "公司调查"],
        "template_key":  "COMPANY",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~5000字",
    },
    "duanxian_zhushou": {
        "label":         "短线助手",
        "trigger_keywords": ["短线", "打板", "涨停", "情绪", "盘前策略", "短线助手"],
        "template_key":  "SHORT_TERM",
        "mode_hint":     "normal",
        "risk_note":     "⚠️ 本身为高风险，不受用户风险级别约束",
        "word_count":    "~1500字",
    },
    "etf_youxuan": {
        "label":         "ETF优选",
        "trigger_keywords": ["ETF", "ETF优选", "基金配置", "定投", "宽基", "行业ETF", "红利ETF", "黄金ETF", "跨境ETF"],
        "template_key":  "ETF",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~3500字",
    },
    "jishu_baogao": {
        "label":         "技术研报",
        "trigger_keywords": ["技术研报", "前沿技术", "科技前沿", "AI前沿", "技术分析深度"],
        "template_key":  "TECH",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~4000字",
    },
    "keji_fengxiangbiao": {
        "label":         "科技风向标",
        "trigger_keywords": ["科技风向", "科技动态", "科技热点", "科技前沿动态"],
        "template_key":  "TECH_TREND",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~2000字",
    },
    "qihuo_miaoshou": {
        "label":         "期货妙手",
        "trigger_keywords": ["期货", "期货分析", "大宗商品", "原油", "黄金期货"],
        "template_key":  "FUTURES",
        "mode_hint":     "normal",
        "risk_note":     "⚠️ 本身为高风险，不受用户风险级别约束",
        "word_count":    "~2000字",
    },
    "shehui_fazhan_baogao": {
        "label":         "社会发展报告",
        "trigger_keywords": ["社会发展", "社会趋势", "人口", "消费趋势", "社会变化"],
        "template_key":  "SOCIAL_DEV",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~2500字",
    },
    "shehui_jinrong_baogao": {
        "label":         "社会金融报告",
        "trigger_keywords": ["社会金融", "金融趋势", "支付趋势", "信贷", "财富管理趋势"],
        "template_key":  "SOCIAL_FINANCE",
        "mode_hint":     "normal",
        "risk_note":     None,
        "word_count":    "~2500字",
    },
}


def match_report_type(user_input: str) -> str:
    """
    根据用户输入内容匹配最合适的研报类型。
    返回 REPORT_TYPES 中的 key，若无匹配返回 "kuaisu_kuaibao"。
    """
    if not user_input:
        return "kuaisu_kuaibao"
    user_lower = user_input.lower()
    best_key = "kuaisu_kuaibao"
    best_score = 0
    for key, info in REPORT_TYPES.items():
        score = sum(
            1 for kw in info["trigger_keywords"]
            if kw.lower() in user_lower
        )
        if score > best_score:
            best_score = score
            best_key = key
    return best_key


def get_template(key: str) -> str:
    """根据 template_key 获取模板，兼容新旧命名"""
    _templates = {
        "BULLETIN":       TEMPLATE_BULLETIN,
        "MARKET_DAILY":   TEMPLATE_MARKET_DAILY,
        "STOCK_ANALYSIS": TEMPLATE_STOCK_ANALYSIS,
        "PORTFOLIO":      TEMPLATE_PORTFOLIO,
        "STOCK_PICK":     TEMPLATE_STOCK_PICK,
        "CROSS_ASSET":    TEMPLATE_CROSS_ASSET,
        "INDUSTRY":       TEMPLATE_INDUSTRY,
        "COMPANY":        TEMPLATE_COMPANY,
        "SHORT_TERM":     TEMPLATE_SHORT_TERM,
        "ETF":            TEMPLATE_ETF,
        "TECH":           TEMPLATE_TECH,
        "TECH_TREND":     TEMPLATE_TECH_TREND,
        "FUTURES":        TEMPLATE_FUTURES,
        "SOCIAL_DEV":     TEMPLATE_SOCIAL_DEV,
        "SOCIAL_FINANCE": TEMPLATE_SOCIAL_FINANCE,
    }
    return _templates.get(key, TEMPLATE_BULLETIN)


# ═══════════════════════════════════════════════════════════
#  【新增 2026-04-16】龙虾投资经验框架常量
#  来源：D:\评估优化.txt 经验总结
# ═══════════════════════════════════════════════════════════

# ── 一、三维选股框架 ───────────────────────────────────────

# 第一维：产业生命周期
INDUSTRY_LIFECYCLE = {
    "爆发期": {
        "emoji": "🟢",
        "stars": "★★★★★",
        "渗透率": "<10%",
        "增速": ">50%",
        "关键词": "0-1阶段、技术突破、政策强推",
        "案例": "2023年AI算力",
        "策略": "重仓，积极建仓",
    },
    "成长期": {
        "emoji": "🟢",
        "stars": "★★★★☆",
        "渗透率": "10-30%",
        "增速": "30-50%",
        "关键词": "渗透率提升、竞争加剧、马太效应",
        "案例": "当前机器人/固态电池",
        "策略": "优选龙头，适度配置",
    },
    "成熟期": {
        "emoji": "🟡",
        "stars": "★★★☆☆",
        "渗透率": ">30%",
        "增速": "10-20%",
        "关键词": "竞争激烈、格局稳定、分红为主",
        "案例": "工程机械出海",
        "策略": "波段操作，高抛低吸",
    },
    "衰退期": {
        "emoji": "🔴",
        "stars": "★★☆☆☆",
        "渗透率": "见顶/下滑",
        "增速": "<10%",
        "关键词": "产能过剩、价格战、亏损",
        "案例": "传统地产链",
        "策略": "回避，不参与",
    },
}

# 第二维：竞争格局
COMPETITION_PATTERNS = {
    "垄断/寡头": {
        "emoji": "🟢",
        "特征": "1-3家控制市场，定价权强",
        "策略": "首选，长期持有",
        "护城河要求": "极高",
    },
    "差异化竞争": {
        "emoji": "🟡",
        "特征": "各有特色，细分市场",
        "策略": "次选，看产品迭代速度",
        "护城河要求": "中高",
    },
    "同质化竞争": {
        "emoji": "🔴",
        "特征": "价格战，毛利率低",
        "策略": "回避，除非成本绝对领先",
        "护城河要求": "不可行",
    },
    "洗牌期": {
        "emoji": "🟡",
        "特征": "格局未定，烧钱大战",
        "策略": "观望，等赢家出现后再参与",
        "护城河要求": "观察",
    },
}

# 第三维：业绩验证阶段
VALIDATION_STAGES = {
    "概念期": {
        "emoji": "🔴",
        "特征": "只有故事，无收入",
        "风险收益": "高风险高回报，赌博性质",
        "策略": "不参与或极小仓位试探",
    },
    "订单期": {
        "emoji": "🟡",
        "特征": "大单公告，收入未确认",
        "风险收益": "中高风险，预期驱动",
        "策略": "观察，确认后介入",
    },
    "放量期": {
        "emoji": "🟢",
        "特征": "收入高增长，利润未跟上",
        "风险收益": "中等风险，最肥美阶段",
        "策略": "核心持仓区间，积极参与",
    },
    "利润期": {
        "emoji": "🟡",
        "特征": "收入利润双增",
        "风险收益": "低风险低回报，验证期",
        "策略": "持有为主，不追高",
    },
    "成熟期": {
        "emoji": "🟡",
        "特征": "增速放缓，分红提升",
        "风险收益": "防御配置，收息为主",
        "策略": "收息配置，降低预期",
    },
}

# ── 二、预期差分析 ─────────────────────────────────────────

# 市场预期 vs 个人判断 → 策略映射
EXPECTATION_DIFFERENTIAL = {
    # (市场预期, 个人判断): 策略标签
    ("乐观", "更乐观"):    "重仓买入",
    ("乐观", "中性/悲观"): "回避或做空",
    ("中性", "乐观"):      "买入（最佳机会）",
    ("中性", "悲观"):      "回避",
    ("悲观", "乐观"):      "逆向买入（困境反转）",
    ("悲观", "更悲观"):    "坚决回避",
}

# 信息层级（用于评估信息质量）
INFO_HIERARCHY = {
    1: {"name": "一手信息", "emoji": "🟢", "来源": "产业链调研、专家访谈、公司IR", "可靠性": "最高", "时效性": "最早"},
    2: {"name": "二手信息", "emoji": "🟡", "来源": "券商研报、机构调研纪要", "可靠性": "高", "时效性": "较早"},
    3: {"name": "三手信息", "emoji": "🔴", "来源": "财经媒体、股吧讨论", "可靠性": "中", "时效性": "滞后"},
    4: {"name": "四手信息", "emoji": "⚫", "来源": "股价走势、技术指标", "可靠性": "低", "时效性": "最滞后"},
}

# 预期验证清单
EXPECTATION_CHECKLIST = [
    "□ 产业数据：行业产量、销量、价格趋势？",
    "□ 公司数据：订单、产能利用率、客户结构？",
    "□ 竞争数据：市占率变化、新品推出节奏？",
    "□ 政策数据：扶持还是限制？力度如何？",
    "□ 宏观数据：利率、汇率、出口环境？",
    "□ 情绪数据：机构持仓、散户参与度？",
]

# ── 三、入场与离场时机 ─────────────────────────────────────

# 四种最佳入场时机
ENTRY_TIMING = {
    "产业爆发前": {
        "emoji": "🟢",
        "特征": "渗透率拐点，技术突破",
        "案例": "2022年底ChatGPT发布",
        "策略": "重仓布局，忽略短期波动",
    },
    "业绩加速前": {
        "emoji": "🟢",
        "特征": "订单放量，产能释放",
        "案例": "季报前1-2个月",
        "策略": "提前埋伏，季报兑现后决策",
    },
    "困境反转前": {
        "emoji": "🟢",
        "特征": "最坏情况已定价，改善迹象出现",
        "案例": "行业低谷，龙头率先企稳",
        "策略": "逆向布局，止损明确",
    },
    "预期修复前": {
        "emoji": "🟢",
        "特征": "过度悲观，预期差最大",
        "案例": "政策转向，情绪冰点",
        "策略": "分批建仓，越跌越买",
    },
}

# 四种必须回避的时机
AVOID_TIMING = {
    "业绩兑现后": {
        "emoji": "🔴",
        "特征": "利好出尽，预期向下",
        "案例": "中联重科2025年4月",
        "教训": "买在预期向下时",
    },
    "情绪高潮后": {
        "emoji": "🔴",
        "特征": "人人谈论，估值泡沫",
        "案例": "2021年核心资产",
        "教训": "人多的地方预期差最小",
    },
    "技术破位后": {
        "emoji": "🔴",
        "特征": "趋势逆转，资金出逃",
        "案例": "跌破MA50，机构出货",
        "教训": "不要接飞刀",
    },
    "预期恶化后": {
        "emoji": "🔴",
        "特征": "基本面变差，尚未完全反映",
        "案例": "业绩预警，下调指引",
        "教训": "不要与趋势为敌",
    },
}

# ── 四、趋势判断框架 ───────────────────────────────────────

TREND_STRATEGY = {
    "强趋势（上涨）": {
        "特征": "均线多头排列，量价齐升",
        "策略": "持有，回调加仓，让利润奔跑",
        "仓位": "80-100%",
    },
    "弱趋势（震荡）": {
        "特征": "均线粘合，量能萎缩",
        "策略": "观望，高抛低吸，控制仓位",
        "仓位": "40-60%",
    },
    "逆转趋势（下跌）": {
        "特征": "均线空头排列，放量下跌",
        "策略": "离场，或极小仓位试探",
        "仓位": "0-20%",
    },
    "无趋势（混沌）": {
        "特征": "方向不明，随机波动",
        "策略": "空仓，等待明朗",
        "仓位": "0%",
    },
}

# ── 五、投资铁律 ───────────────────────────────────────────

INVESTMENT_DISCIPLINE = {
    "不补仓摊薄":     "亏损股票不加仓，避免深套。底部是走出来的，不是补出来的。",
    "不预测底部":     "底部是走出来的，不是猜出来的。不要试图抄在最低点。",
    "不幻想回本":     "每一笔交易独立判断，不受买入成本影响。成本不是锚。",
    "不追逐热点":     "人多的地方预期差最小。热股不买，冷股不卖。",
    "不All in单票":   "单只股票不超过总资金20%。分散是免费的午餐。",
    "不频繁交易":     "交易成本侵蚀收益，耐心等待。频繁操作是复利的天敌。",
    "及时止损":       "亏损时果断止损，不要越陷越深。截断亏损，让利润奔跑。",
    "分批建仓":       "不一把梭，分批入场。首次建仓不超过30%。",
}

# ── 六、仓位分配标准 ───────────────────────────────────────

POSITION_STANDARDS = {
    "单只上限":        {"value": 20, "unit": "%", "标准": "单只股票不超过总资金20%"},
    "单行业上限":      {"value": 35, "unit": "%", "标准": "单一行业不超过35%"},
    "前三大持仓上限":  {"value": 60, "unit": "%", "标准": "前3大持仓不超过60%"},
    "核心仓位":        {"value": (50, 60), "unit": "%", "标准": "高确定性，长期持有"},
    "卫星仓位":        {"value": (30, 40), "unit": "%", "标准": "中确定性，波段操作"},
    "试探仓位":        {"value": (10, 20), "unit": "%", "标准": "低确定性，验证预期"},
    "现金保留":        {"value": (10, 20), "unit": "%", "标准": "应对波动，等待机会"},
}

# 建仓阶段仓位标准
POSITION_PHASES = {
    "建仓期":  {"仓位": (5, 10), "止损": "跌破买入价-8%止损"},
    "验证期":  {"仓位": (10, 15), "止损": "业绩验证后加仓或止损"},
    "持有期":  {"仓位": (15, 20), "止损": "趋势破坏或预期改变离场"},
    "兑现期":  {"仓位": "逐步减仓", "止损": "达到目标价或预期兑现"},
}

# ── 七、行为误区检测 ───────────────────────────────────────

BEHAVIORAL_BIASES = {
    "过度集中": {
        "描述": "单只股票或单一行业占比过高",
        "危害": "系统性风险暴露，睡不着觉",
        "纠正": "单只≤20%，单行业≤35%",
        "检测指标": "max_single > 20% 或 max_sector > 35%",
    },
    "盈利锚定": {
        "描述": "持有盈利股票时急于卖出，持有亏损股票时不愿止损",
        "危害": "截断利润，让亏损奔跑",
        "纠正": "看估值和趋势，不看成本",
        "检测指标": "盈利股票持仓周期 < 亏损股票持仓周期",
    },
    "现金厌恶": {
        "描述": "讨厌持有现金，恨不得全仓操作",
        "危害": "无资金应对下跌，错过机会",
        "纠正": "永远保留10-20%现金",
        "检测指标": "cash_pct < 10%",
    },
    "羊群效应": {
        "描述": "追逐热门板块，买在人声鼎沸时",
        "危害": "买在预期最高点，预期差最小",
        "纠正": "逆向思考，人弃我取",
        "检测指标": "买入时机 = 情绪高点",
    },
    "过度自信": {
        "描述": "重仓单票，All in一个逻辑",
        "危害": "一次错误损失惨重",
        "纠正": "分散持仓，不押注单一标的",
        "检测指标": "任一持仓 > 30%",
    },
    "损失厌恶": {
        "描述": "对亏损的厌恶超过对盈利的喜悦（2倍效应）",
        "危害": "过早止损，过晚止盈",
        "纠正": "设置机械止损止盈规则并执行",
        "检测指标": "止损执行率低，持仓周期过长",
    },
    "后视镜思维": {
        "描述": "用过去的股价走势判断未来",
        "危害": "买跌得不厉害的，卖涨得不厉害的",
        "纠正": "看未来预期，不看过去走势",
        "检测指标": "买卖决策 = 历史价格决定",
    },
    "确认偏误": {
        "描述": "只关注支持自己观点的信息，忽略反面证据",
        "危害": "错失纠错机会，越陷越深",
        "纠正": "主动寻找反对意见，定期审视持仓",
        "检测指标": "看多报告 vs 看空报告严重失衡",
    },
}

# ═══════════════════════════════════════════════════════════
#  龙虾寄语语料库（2026-04-16 扩充版）
# ═══════════════════════════════════════════════════════════

LOBSTER_QUOTES = [
    # ── 经典语录（保留）────────────────────────────────────
    "市场从不缺机会，缺的是等待的耐心。 🦞",
    "低估时不慌，高估时不贪，这才是穿越牛熊的姿态。 🦞",
    "每一次暴跌都是对认知的定价，你的理解力决定你的收益率。 🦞",
    "不追热点是世界上最难的事，也是最重要的事。 🦞",
    "仓位管理比选股更重要，留有子弹的人才有资格打下一场战役。 🦞",
    "风险永远在行情最热的时候悄悄累积。 🦞",
    "研究要深，行动要慢，决定要快。 🦞",
    "好公司也要有好价格，买得便宜是最大的安全边际。 🦞",
    "不要试图预测市场，而是要做好准备应对市场。 🦞",
    "别人贪婪时恐惧，别人恐惧时贪婪——知易行难，且行且珍惜。 🦞",
    # ── 【2026-04-16 经验教训更新】────────────────────────
    # 经验教训1：中联重科——买的是未来，不是过去
    "中联重科业绩+38%却跌了？因为你买的是昨天的利好，不是明天的预期。投资投的是未来，不是过去。 🦞",
    # 经验教训2：预期差是核心
    "市场一致乐观时，你要悲观；市场一致悲观时，你要乐观。预期差才是超额收益的来源。 🦞",
    # 经验教训3：产业趋势是第一维筛选
    "先看行业，再看公司。夕阳行业里的龙头，不如朝阳行业里的普通公司。选错赛道，再努力也是徒劳。 🦞",
    # 经验教训4：放量期是最肥美的阶段
    "收入高增长、利润未跟上——这才是黄金时代。等利润兑现了，预期也就到顶了。 🦞",
    # 经验教训5：不补仓摊薄
    "底部是走出来的，不是补出来的。越跌越买是通往深渊的捷径。 🦞",
    # 经验教训6：不以成本为锚
    "你的成本价只有你自己在乎，市场不在乎。每一笔交易独立判断，不受买入价影响。 🦞",
    # 经验教训7：入场时机四原则
    "四种时候买：爆发前、加速前、困境反转前、预期修复前。四种时候跑：利好出尽、人声鼎沸、技术破位、预期恶化。 🦞",
    # 经验教训8：仓位纪律
    "永远留10-20%现金。满仓的人没有资格在暴跌时加仓。现金是期权，是应对不确定性的最好工具。 🦞",
    # 经验教训9：信息质量
    "股价已经反映了所有公开信息。你需要找到的，是非共识的正确。信息来源决定认知质量。 🦞",
    # 经验教训10：行为纠偏
    "盈利时最危险的不是回撤，是贪婪。你现在的浮盈是市场的馈赠，不是实力的证明。减仓不是认输，是给未来的自己留子弹。 🦞",
    # 经验教训11：止损纪律
    "截断亏损，让利润奔跑——这句话每个人都懂，但执行起来需要纪律。设置止损，不侥幸。 🦞",
    # 经验教训12：一句话总结
    "在产业趋势向上的行业中，找到竞争格局优化的公司，在其业绩加速或预期反转前买入，在预期兑现或趋势破坏后卖出。关键是买卖的是未来，不是过去。 🦞",
]

TRIANGLE_QUOTES = [
    "三角稳定，三资产联动看懂世界资金的流向。 🥇💵₿",
    "美元弱，黄金强；流动性松，BTC狂。这是规律，不是玄学。 🥇",
    "当三资产罕见同涨，危机已在门口；当三资产共振下跌，机会在孕育。 🥇💵₿",
]

# ═══════════════════════════════════════════════════════════
#  以下为各研报模板
# ═══════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────
# 模板1：快速快报
# ───────────────────────────────────────────────────────────
TEMPLATE_BULLETIN = """\
# 🦞 龙虾快报 | {date} {time}

## 一句话定调
{one_sentence_summary}（20字内）

---

## 三资产温度计

| 资产 | 状态 | 关键位 | 信号 |
|:---|:---:|:---|:---:|
| A股 | {aqi_status} | 上证{sh_key_level} | {aqi_signal} |
| 美债/美元 | {bond_status} | 10Y{yield_key}% DXY{dxy_key} | {bond_signal} |
| 黄金/BTC | {commodity_status} | 金{gold_key} BTC{btc_key} | {commodity_signal} |

> 🟢 顺风 | 🟡 震荡 | 🔴 逆风

---

## 多空三信号

| 看多（🟢） | 看空（🔴） |
|:---|:---|
| 1. {bull_1} | 1. {bear_1} |
| 2. {bull_2} | 2. {bear_2} |
| 3. {bull_3} | 3. {bear_3} |

**关键博弈点**：{key_debate}

---

## 热点雷达（TOP3）

| 排名 | 板块 | 驱动 | 持续性 | 龙头 |
|:---:|:---|:---|:---:|:---|
| 1 | {hot_1} | {driver_1} | {sustain_1} | {leader_1} |
| 2 | {hot_2} | {driver_2} | {sustain_2} | {leader_2} |
| 3 | {hot_3} | {driver_3} | {sustain_3} | {leader_3} |

---

## 立即行动

**仓位**：{position}%（{position_range}）

**今日动作**：
- {action_1}
- {action_2}

**止损纪律**：{stop_loss_rule}

---

> {quote} | 数据：{source} | 免责声明：AI生成，仅供参考
"""

# ───────────────────────────────────────────────────────────
# 模板2：大盘日报
# ───────────────────────────────────────────────────────────
TEMPLATE_MARKET_DAILY = """\
# 🦞 龙虾大盘日报 | {date}

> AI生成 | 数据时间：{data_time} | 下次更新：{next_date} 09:30

---

## 一、市场快照

| 指数 | 收盘 | 1日涨跌 | 5日涨跌 | 20日涨跌 | 信号灯 |
|:---|---:|---:|---:|---:|:---:|
| **上证指数** | **{sh_close}** | **{sh_1d}%** | {sh_5d}% | {sh_20d}% | {sh_signal} |
| 深证成指 | {sz_close} | {sz_1d}% | {sz_5d}% | {sz_20d}% | {sz_signal} |
| 创业板指 | {cy_close} | {cy_1d}% | {cy_5d}% | {cy_20d}% | {cy_signal} |
| 科创50 | {kc_close} | {kc_1d}% | {kc_5d}% | {kc_20d}% | {kc_signal} |

> 🟢 强势（涨>1%）| 🟡 震荡（-1%~+1%）| 🔴 偏弱（跌>1%）

**AI速读**：{ai_summary}（150字内，概括市场状态、主要矛盾、关键风险）

---

## 二、宏观环境与政策面

### 2.1 国内经济

| 指标 | 数据 | 信号 |
|:---|:---|:---:|
| GDP | {gdp}% | {gdp_signal} |
| 制造业PMI | {pmi} | {pmi_signal} |
| 工业增加值 | {industrial}% | {industrial_signal} |
| 社零 | {retail}% | {retail_signal} |

### 2.2 货币政策

| 政策工具 | 预期 | 时点 | 影响 |
|:---|:---|:---|:---|
| 降准 | {rrr_expect} | {rrr_time} | {rrr_impact} |
| 降息 | {rate_expect} | {rate_time} | {rate_impact} |

### 2.3 行业政策

{sector_policy_detail}

---

## 三、国际环境

### 3.1 美联储政策

| 指标 | 当前值 | 预期 | 影响 |
|:---|:---|:---|:---|
| 联邦基金利率 | {fed_rate}% | {fed_expect}% | {fed_impact} |
| PCE通胀 | {pce}% | {pce_expect}% | {pce_impact} |

### 3.2 地缘政治

{geopolitics_detail}

---

## 四、核心结论

| 问题 | AI判断 |
|:---|:---|
| **市场状态** | {market_status} |
| **战略仓位** | {position}%（区间{position_range}）|
| **风格偏好** | {style_bias} |
| **主线板块** | {leading_sectors} |
| **今日动作** | {today_action} |

**操作清单**：
- [ ] {check_1}
- [ ] {check_2}
- [ ] {check_3}
- [ ] {check_4}

---

## 五、估值与资金

### 5.1 估值数据

| 指标 | 当前值 | 历史分位 | 信号 | 解读 |
|:---|:---|:---|:---:|:---|
| 万得全A PE | {pe}倍 | {pe_pct}% | {pe_signal} | {pe_comment} |
| 万得全A PB | {pb}倍 | {pb_pct}% | {pb_signal} | {pb_comment} |
| ERP | {erp}% | {erp_pct}% | {erp_signal} | {erp_comment} |

### 5.2 资金数据

| 指标 | 数值 | 环比 | 信号 |
|:---|:---|:---|:---:|
| 两市成交额 | {volume}亿 | {vol_chg}% | {vol_signal} |
| 融资余额 | {margin}亿 | {margin_chg}% | {margin_signal} |
| 北向资金(周) | {north}亿 | {north_trend} | {north_signal} |

---

## 六、趋势与模式

### 6.1 概率仪表盘

| 周期 | 趋势概率 | 判断 |
|:---|:---|:---|
| 短期（1-5日）| {short_prob}% | {short_trend} |
| 中期（5-20日）| {mid_prob}% | {mid_trend} |
| 长期（20-60日）| {long_prob}% | {long_trend} |
| **综合** | **{total_prob}%** | **{total_trend}** |

### 6.2 特殊模式检测

| 模式 | 触发条件 | 当前状态 |
|:---|:---|:---|
| 危机模式 | VIX>30 或 单日暴跌>5% | {crisis_status} |
| 狂热模式 | 贪婪>90 或 融资>90%分位 | {euphoria_status} |
| 磨底模式 | ERP>90% 且 成交<50% | {bottom_status} |

---

## 七、AI解读

### 7.1 好信号 vs 坏信号

| 好信号（支持{bull_case}）| 坏信号（支持{bear_case}）|
|:---|:---|
| {bull_signal_1} | {bear_signal_1} |
| {bull_signal_2} | {bear_signal_2} |
| {bull_signal_3} | {bear_signal_3} |

**AI平衡**：{ai_balance}

### 7.2 行业分级

| 等级 | 板块 | 逻辑 |
|:---:|:---|:---|
| S级 🟢 | {s_sectors} | {s_reason} |
| A级 🟢 | {a_sectors} | {a_reason} |
| B级 🟡 | {b_sectors} | {b_reason} |
| C级 🔴 | {c_sectors} | {c_reason} |

---

## 八、龙虾寄语

> {lobster_quote}

---

**数据**：Yahoo Finance / 东方财富 / 国家统计局 / 央行 / 新浪财经 | **免责声明**：本报告由AI生成，仅供参考，不构成投资建议
"""

# ───────────────────────────────────────────────────────────
# 模板3：个股深度分析
# ───────────────────────────────────────────────────────────
TEMPLATE_STOCK_ANALYSIS = """\
# 🦞 龙虾个股深度分析 | {stock_name}({stock_code})

> AI生成 | 分析日期：{date} | 数据截至：{data_date}

---

## 一、投资快照

| 指标 | 数据 | 信号 | 说明 |
|:---|:---|:---:|:---|
| **最新价** | **{price}元** | - | 较52周高点{high_dist}%，较低点{low_dist}% |
| **趋势状态** | {trend_status} | {trend_emoji} | 短期{short_trend}，中期{mid_trend} |
| **估值水平** | PE {pe}倍 | {pe_signal} | 行业{industry_pe}倍，{pe_vs_industry} |
| **市值** | {market_cap}亿 | - | 流通市值{float_cap}亿 |
| **资金情绪** | {sentiment} | {sentiment_emoji} | 近5日主力{main_5d}亿 |

**AI速读**：{ai_summary}（100字内，核心逻辑+主要风险）

---

## 二、基本面分析

### 2.1 核心财务指标

| 指标 | 最新值 | 同比 | 信号 | 诊断 |
|:---|---:|:---:|:---:|:---|
| 营收增速 | {rev_growth}% | {rev_chg}pct | {rev_signal} | {rev_comment} |
| 净利润增速 | {profit_growth}% | {profit_chg}pct | {profit_signal} | {profit_comment} |
| 毛利率 | {gross_margin}% | {gross_chg}pct | {gross_signal} | {gross_comment} |
| 净利率 | {net_margin}% | {net_chg}pct | {net_signal} | {net_comment} |
| ROE | {roe}% | {roe_chg}pct | {roe_signal} | {roe_comment} |
| 负债率 | {debt_ratio}% | {debt_chg}pct | {debt_signal} | {debt_comment} |

### 2.2 成长性评估

| 维度 | 评估 | 证据 | 置信度 |
|:---|:---|:---|:---:|
| 行业空间 | {industry_space} | {industry_evidence} | {industry_conf} |
| 竞争优势 | {moat} | {moat_evidence} | {moat_conf} |
| 增长驱动 | {growth_driver} | {driver_evidence} | {driver_conf} |

---

## 三、估值分析

### 3.1 同业对比

| 公司 | PE(TTM) | PB | ROE | 营收增速 | 市值 | 估值溢价 |
|:---|---:|---:|---:|---:|---:|:---|
| **{stock_name}** | **{pe}** | **{pb}** | **{roe}%** | **{rev_growth}%** | **{cap}亿** | - |
| {peer_1} | {p1_pe} | {p1_pb} | {p1_roe}% | {p1_rev}% | {p1_cap}亿 | {p1_premium}% |
| {peer_2} | {p2_pe} | {p2_pb} | {p2_roe}% | {p2_rev}% | {p2_cap}亿 | {p2_premium}% |
| 行业平均 | {avg_pe} | {avg_pb} | {avg_roe}% | {avg_rev}% | - | - |

### 3.2 目标价

| 方法 | 假设 | 估值 | 权重 |
|:---|:---|---:|:---:|
| PE估值法 | 给予{pe_target}倍PE | {pe_val}元 | {pe_weight}% |
| PB-ROE模型 | 合理PB={pb_target}倍 | {pb_val}元 | {pb_weight}% |
| **综合目标价** | - | **{target_price}元** | 较现价{upside}% |

**敏感性分析**：

| 情景 | 假设变化 | 目标价 | 涨跌幅 |
|:---|:---|---:|---:|
| 乐观 | {bull_assump} | {bull_target}元 | +{bull_upside}% |
| 基准 | {base_assump} | {target_price}元 | +{upside}% |
| 悲观 | {bear_assump} | {bear_target}元 | +{bear_upside}% |

---

## 四、技术面分析

### 4.1 趋势结构

| 周期 | 趋势 | 关键支撑 | 关键阻力 | 信号 |
|:---|:---:|:---|:---|:---|
| 短期(5日) | {short_dir} | {s1} | {r1} | {short_signal} |
| 中期(20日) | {mid_dir} | {s2} | {r2} | {mid_signal} |
| 长期(60日) | {long_dir} | {s3} | {r3} | {long_signal} |

### 4.2 技术指标

| 指标 | 当前值 | 信号 | 解读 |
|:---|---:|:---:|:---|
| MA5/MA20 | {price}>{ma5}>{ma20} | {ma_signal} | {ma_comment} |
| RSI(14) | {rsi} | {rsi_signal} | {rsi_comment} |
| 成交量 | 5日均量{vol5} | {vol_signal} | {vol_comment} |

---

## 五、资金面分析

| 资金类型 | 最新数据 | 5日变化 | 信号 | 解读 |
|:---|:---|:---:|:---:|:---|
| 主力资金 | {main_flow}亿 | {main_5d}亿 | {main_signal} | {main_comment} |
| 北向资金 | {north_pct}% | {north_5d}亿 | {north_signal} | {north_comment} |
| 融资余额 | {margin}亿 | {margin_5d} | {margin_signal} | {margin_comment} |

---

## 六、催化剂与风险

### 6.1 正向催化剂

| 时间 | 事件 | 影响程度 | 概率 | 股价弹性 |
|:---|:---|:---:|:---:|:---:|
| {cata_date1} | {cata_event1} | {cata_impact1} | {cata_prob1}% | ±{cata_elastic1}% |

### 6.2 风险因素

| 风险类型 | 具体风险 | 量化影响 | 预警信号 |
|:---|:---|:---:|:---|
| 经营风险 | {risk1} | {risk1_quant} | {risk1_alert} |
| 行业风险 | {risk2} | {risk2_quant} | {risk2_alert} |
| 宏观风险 | {risk3} | {risk3_quant} | {risk3_alert} |

---

## 七、投资策略

| 问题 | AI判断 |
|:---|:---|
| **投资评级** | {rating}（目标价{target_price}元，{upside}%） |
| **适合投资者** | {suitable_investor} |
| **仓位建议** | {position_pct}%（单只不超过20%） |

**入场策略**：
- ✅ 理想入场：{entry_zone}元以下分批建仓
- 🎯 止损位：{stop_loss}元（-{sl_pct}%）
- 🎯 止盈位：{take_profit}元（+{tp_pct}%）

---

## 八、龙虾寄语

> {lobster_quote}

---

**数据来源**：Yahoo Finance / 东方财富 / 公司公告 | **免责声明**：本报告由AI生成，仅供参考，不构成投资建议
"""

# ───────────────────────────────────────────────────────────
# 模板4：持仓诊断
# ───────────────────────────────────────────────────────────
TEMPLATE_PORTFOLIO = """\
# 🦞 龙虾持仓分析报告 | {date}

> 用户持仓：{stock_count}只 | 总市值：{total_value}万 | 整体盈亏：{total_pnl}%

---

## 一、持仓概览

| 统计项 | 你的数据 | 健康标准 | 信号灯 |
|:---|---:|:---|:---:|
| 持仓数量 | {stock_count}只 | 5-15只 | {count_emoji} |
| 现金比例 | {cash_pct}% | ≥10% | {cash_emoji} |
| 最大个股占比 | {max_single}% | ≤20% | {single_emoji} |
| 最大行业占比 | {max_sector}% | ≤35% | {sector_emoji} |
| **浮动盈亏** | **{total_pnl}%** | - | {pnl_emoji} |

**AI速读**：{ai_summary}（100字内概括持仓健康度、最大风险、核心机会）

---

## 二、持仓健康评分：{total_score}分 | {overall_rating}

| 维度 | 得分 | 权重 | 关键问题 |
|:---|---:|:---:|:---|
| 集中度健康 | {score1}/20 | 20% | {issue1} |
| 行业分散 | {score2}/20 | 20% | {issue2} |
| 估值合理 | {score3}/20 | 20% | {issue3} |
| 趋势质量 | {score4}/20 | 20% | {issue4} |
| 流动性安全 | {score5}/20 | 20% | {issue5} |

---

## 三、个股逐一诊断

### {s_name}（{s_code}）| 占比{s_pct}% | 盈亏{s_pnl}%

| 指标 | 数据 | 信号灯 |
|:---|:---|:---:|
| 成本价 | {s_cost}元 | - |
| 当前价 | {s_price}元 | - |
| 估值 | PE {s_pe}倍 | {s_pe_emoji} |
| 趋势 | {s_trend} | {s_trend_emoji} |
| 资金 | {s_fund} | {s_fund_emoji} |

**诊断**：{s_diagnosis}（🟢持有/🟡观望/🔴减仓/⚪止损）

**操作建议**：
- 🎯 目标价：{s_target}元（+{s_upside}%）
- 🛑 止损价：{s_stop}元（-{s_downside}%）
- 💰 调仓：{s_action}

---

## 四、组合优化方案

### 4.1 调仓总表

| 代码 | 名称 | 当前→目标 | 操作 | 触发价 | 优先级 |
|:---|:---|:---:|:---|:---|:---:|
| {t_code1} | {t_name1} | {t_now1}%→{t_target1}% | {t_act1} | {t_trigger1} | 🔥高 |
| {t_code2} | {t_name2} | {t_now2}%→{t_target2}% | {t_act2} | {t_trigger2} | ✅中 |

### 4.2 优化效果

| 指标 | 当前 | 优化后 | 变化 |
|:---|---:|---:|:---|
| 预期波动率 | {before_vol}% | {after_vol}% | {vol_chg} |
| 最大回撤 | {before_dd}% | {after_dd}% | {dd_chg} |

---

## 五、短中长期策略

### 短期（1-4周）

**本周操作清单**：
- [ ] {short_check1}
- [ ] {short_check2}

### 中期（1-6月）

- 加仓方向：{mid_add}（理由：{mid_add_reason}）
- 减仓方向：{mid_reduce}（理由：{mid_reduce_reason}）

### 长期（6-12月+）

- 核心持有名单：{long_core}
- 需要替换：{long_exit}

---

## 六、行为纠偏

| 检测到的误区 | 你的表现 | 纠正方案 |
|:---|:---|:---|
| {bias1_type} | {bias1_desc} | {bias1_fix} |

---

## 七、龙虾寄语

> {lobster_quote}

---

**免责声明**：本分析仅供参考，不构成投资建议。市场有风险，调仓需谨慎。
"""

# ───────────────────────────────────────────────────────────
# 模板5：快速选股
# ───────────────────────────────────────────────────────────
TEMPLATE_STOCK_PICK = """\
# 🦞 龙虾快速选股 | {date}

> 选股周期：{cycle} | 数据截至：{data_date}

---

## 一、宏观定仓

**市场温度**：{market_temp} {temp_emoji}

| 指标 | 数据 | 信号 | 解读 |
|:---|:---|:---:|:---|
| 制造业PMI | {pmi} | {pmi_signal} | {pmi_comment} |
| 10Y国债利率 | {bond_yield}% | {bond_signal} | {bond_comment} |
| 北向资金(周) | {north_weekly}亿 | {north_signal} | {north_comment} |
| VIX指数 | {vix} | {vix_signal} | {vix_comment} |

**战略仓位**：建议{position}%（区间{position_range}）

---

## 二、TOP3赛道

| 排名 | 板块 | 核心逻辑 | 政策 | 景气 | 技术 | 资金 | 综合 |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | **{sector1}** | {sector1_logic} | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| 2 | **{sector2}** | {sector2_logic} | 🟢 | 🟡 | 🟢 | 🟢 | 🟢 |
| 3 | **{sector3}** | {sector3_logic} | 🟡 | 🟢 | 🟢 | 🟡 | 🟢 |

---

## 三、精选标的（12只）

### {sector1}板块（仓位{s1_weight}%）

| 代码 | 名称 | 核心逻辑 | 目标价 | 止损价 | 仓位 |
|:---|:---|:---|---:|---:|:---:|
| {s1_c1} | {s1_n1} | {s1_l1} | {s1_t1}元 | {s1_s1}元 | 15% |
| {s1_c2} | {s1_n2} | {s1_l2} | {s1_t2}元 | {s1_s2}元 | 10% |
| {s1_c3} | {s1_n3} | {s1_l3} | {s1_t3}元 | {s1_s3}元 | 10% |
| {s1_c4} | {s1_n4} | {s1_l4} | {s1_t4}元 | {s1_s4}元 | 5% |

---

## 四、组合配置与风控

**仓位分布**：
- 进攻型（15%）：{aggressive_stocks}
- 稳健型（10%）：{stable_stocks}
- 观察型（5%）：{watch_stocks}

**统一风控**：
- 单只最大亏损：-8%强制止损
- 单板块最大亏损：-15%整体减仓
- 组合总回撤：-10%降至半仓，-15%降至3成

---

## 五、龙虾寄语

> {lobster_quote}

---

**数据来源**：Wind / 东方财富 / 同花顺 / 公司公告 | **免责声明**：本选股结果由AI生成，仅供参考，不构成投资建议
"""

# ───────────────────────────────────────────────────────────
# 模板6：跨资产联动
# ───────────────────────────────────────────────────────────
TEMPLATE_CROSS_ASSET = """\
# 🥇💵₿ 三角瞭望 | 黄金·美元·比特币联动 | {date}

> 跨资产分析 | 数据时间：{data_time} UTC

---

## 一、三资产快照

| 资产 | 价格 | 24H涨跌 | 7日涨跌 | 30日涨跌 | 信号 | 关键位 |
|:---|---:|---:|---:|---:|:---:|:---|
| **黄金 XAU/USD** | **{gold_price}** | **{gold_24h}%** | {gold_7d}% | {gold_30d}% | {gold_signal} | 支撑{gold_sup} 阻力{gold_res} |
| **美元指数 DXY** | {dxy_price} | {dxy_24h}% | {dxy_7d}% | {dxy_30d}% | {dxy_signal} | 支撑{dxy_sup} 阻力{dxy_res} |
| **比特币 BTC/USD** | {btc_price} | {btc_24h}% | {btc_7d}% | {btc_30d}% | {btc_signal} | 支撑{btc_sup} 阻力{btc_res} |

**宏观速读**：{macro_summary}（150字内）

---

## 二、相关性矩阵

| 资产对 | 30日相关 | 解读 |
|:---|:---:|:---|
| DXY ↔ 黄金 | {cor_dxy_gold} | {corr_comment_dg} |
| DXY ↔ 比特币 | {cor_dxy_btc} | {corr_comment_db} |
| 黄金 ↔ 比特币 | {cor_gold_btc} | {corr_comment_gb} |

**当前Regime判定**：{current_regime}

---

## 三、三资产策略

### 3.1 相对强弱排名

| 资产 | 综合评分 | 排名 | 近期方向 |
|:---|:---:|:---:|:---|
| 黄金 | {gold_score} | {gold_rank} | {gold_direction} |
| 美元 | {dxy_score} | {dxy_rank} | {dxy_direction} |
| 比特币 | {btc_score} | {btc_rank} | {btc_direction} |

### 3.2 配置建议

| 策略类型 | 黄金 | 美元(做多) | 比特币 | 适用场景 |
|:---|:---:|:---:|:---:|:---|
| 保守型 | 50% | 30% | 20% | 高不确定性，防御 |
| 平衡型 | 35% | 25% | 40% | 趋势明确 |
| 进取型 | 20% | 10% | 70% | 流动性宽松 |
| 对冲型 | 40% | -20% | 40% | 看空美元 |

**当前推荐**：{current_strategy_type}

---

## 四、三角寄语

> {triangle_quote}

---

**数据**：Bloomberg / Yahoo Finance / TradingView / FRED | **免责声明**：杠杆交易风险极高，本报告仅供参考
"""

# ───────────────────────────────────────────────────────────
# 模板7：行业研报
# ───────────────────────────────────────────────────────────
TEMPLATE_INDUSTRY = """\
# 🏭 龙虾行业深度研究 | {industry_name}

> 研究日期：{date} | 数据截至：{data_date} | 评级有效期：6个月

---

## 一、投资快照

| 指标 | 评估 | 信号 | 关键数据 |
|:---|:---|:---:|:---|
| **行业评级** | **{rating}** | {rating_emoji} | 相对收益预期：{relative_return} |
| **生命周期** | {life_cycle} | {lc_emoji} | 渗透率：{penetration}% |
| **景气度** | {prosperity} | {pros_emoji} | 行业PMI：{industry_pmi} |
| **估值水平** | {valuation} | {val_emoji} | PE：{pe}倍（历史{pe_pct}%分位） |
| **政策环境** | {policy} | {pol_emoji} | 政策力度评分：{policy_score}/10 |

**AI速读**：{ai_summary}（150字内，概括行业核心逻辑、关键catalyst、主要风险）

---

## 二、宏观定位与周期判断

### 2.1 经济周期敏感度

| 宏观因子 | 传导机制 | 敏感度 | 当前状态 | 影响方向 |
|:---|:---|:---:|:---|:---:|
| 利率下行 | 降低融资成本，刺激CAPEX | {rate_sens} | {rate_status} | {rate_impact} |
| 信用扩张 | 提升下游需求，改善回款 | {credit_sens} | {credit_status} | {credit_impact} |

**周期定位结论**：{cycle_conclusion}

### 2.2 行业景气度仪表盘

| 指标 | 最新值 | 环比 | 同比 | 历史分位 | 信号 |
|:---|---:|---:|---:|---:|:---:|
| 行业营收增速 | {rev_growth}% | {rev_qoq}pct | {rev_yoy}pct | {rev_pct}% | {rev_signal} |
| 行业利润增速 | {profit_growth}% | {profit_qoq}pct | {profit_yoy}pct | {profit_pct}% | {profit_signal} |

---

## 三、产业链深度解构

### 3.1 价值链分布

| 环节  | 代表企业 | 毛利率 | 净利率 | 壁垒来源 | 议价能力 | 投资价值 |
|:--- |:--- |:---:|---:|:---|:---|:---|
| 上游 | {up_company} | {up_gm}% | {up_nm}% | {up_moat} | {up_power} | {up_value} |
| 中游 | {mid_company} | {mid_gm}% | {mid_nm}% | {mid_moat} | {mid_power} | {mid_value} |
| 下游 | {down_company} | {down_gm}% | {down_nm}% | {down_moat} | {down_power} | {down_value} |

---

## 四、竞争格局

### 4.1 市场集中度

| 指标 | 数值 | 变化趋势 | 国际对比 |
|:---|:---:|:---:|:---|
| CR3 | {cr3}% | {cr3_trend} | 美国{us_cr3}% |
| CR5 | {cr5}% | {cr5_trend} | - |

### 4.2 核心玩家对标

| 公司 | 市占率 | 核心优势 | 战略定位 | 威胁程度 |
|:---|:---:|:---|:---|:---:|
| {player1} | {share1}% | {adv1} | {strategy1} | {threat1} |
| {player2} | {share2}% | {adv2} | {strategy2} | {threat2} |

---

## 五、政策与技术

### 5.1 政策影响力化

| 政策维度 | 具体政策 | 支持力度 | 执行进度 |
|:---|:---|:---:|:---|
| 产业扶持 | {policy1} | {support1}/10 | {progress1} |

**政策综合评分**：{policy_total}/40（{policy_level}）

### 5.2 技术路线演进

| 技术路线 | 当前占比 | 成本水平 | 成熟度 | 颠覆风险 |
|:---|:---:|:---:|:---:|:---:|
| {tech1}（主流） | {share_t1}% | {cost_t1}元/单位 | {mature_t1} | {risk_t1} |
| {tech2}（新兴） | {share_t2}% | {cost_t2}元/单位 | {mature_t2} | {risk_t2} |

---

## 六、投资结论

| 问题 | 判断 |
|:---|:---|
| **行业评级** | {industry_rating} |
| **推荐细分赛道** | {recommended_sector} |
| **核心标的** | {top_stocks} |
| **入场时机** | {entry_timing} |

---

## 七、龙虾寄语

> {lobster_quote}

---

**数据来源**：{data_sources} | **免责声明**：本报告由AI生成，仅供参考
"""

# ───────────────────────────────────────────────────────────
# 模板8：企业研报
# ───────────────────────────────────────────────────────────
TEMPLATE_COMPANY = """\
# 🏢 企业研究调查 | {company_name}（{stock_code}）

> 调查性质：{nature} | 报告日期：{date} | 数据截至：{data_date}

---

## 一、调查快照

| 指标 | 数据/判断 | 信号 | 关键说明 |
|:---|:---|:---:|:---|
| **企业质地** | **{quality_rating}** | {quality_emoji} | {quality_summary} |
| **行业地位** | {industry_position} | {position_emoji} | 市占率{market_share}%，排名{rank} |
| **财务健康** | {financial_health} | {health_emoji} | 核心指标：{key_metric} |
| **估值水平** | {valuation_level} | {valuation_emoji} | {valuation_summary} |
| **核心风险** | {top_risk} | {risk_emoji} | {risk_summary} |
| **调查结论** | **{conclusion}** | {conclusion_emoji} | {conclusion_action} |

**AI速读**：{ai_summary}（150字内，概括商业模式核心、关键优势、最大风险、价值判断）

---

## 二、商业尽调

### 2.1 商业模式解构

| 维度 | 分析 | 证据 | 评价 |
|:---|:---|:---|:---:|
| 价值主张 | {value_proposition} | {value_evidence} | {value_rating} |
| 盈利模式 | {profit_model} | {profit_evidence} | {profit_rating} |
| 核心资源 | {key_resources} | {resource_evidence} | {resource_rating} |

### 2.2 护城河评估

| 护城河类型 | 存在性 | 深度 | 可持续性 | 证据 |
|:---|:---:|:---:|:---:|:---|
| 品牌溢价 | {brand_exist} | {brand_depth} | {brand_sustain} | {brand_evidence} |
| 成本优势 | {cost_exist} | {cost_depth} | {cost_sustain} | {cost_evidence} |
| 网络效应 | {network_exist} | {network_depth} | {network_sustain} | {network_evidence} |
| 转换成本 | {switch_exist} | {switch_depth} | {switch_sustain} | {switch_evidence} |

---

## 三、财务侦探

### 3.1 财务健康仪表盘

| 指标 | 最新值 | 同比 | 行业分位 | 信号 | 诊断 |
|:---|---:|---:|---:|:---:|:---|
| 营收增速 | {rev_growth}% | {rev_chg}pct | {rev_pct}% | {rev_signal} | {rev_comment} |
| 扣非净利润增速 | {profit_growth}% | {profit_chg}pct | {profit_pct}% | {profit_signal} | {profit_comment} |
| 毛利率 | {gross_margin}% | {gross_chg}pct | {gross_pct}% | {gross_signal} | {gross_comment} |
| ROIC | {roic}% | {roic_chg}pct | {roic_pct}% | {roic_signal} | {roic_comment} |
| 有息负债率 | {debt_ratio}% | {debt_chg}pct | {debt_pct}% | {debt_signal} | {debt_comment} |

---

## 四、估值建模

### 4.1 估值矩阵

| 方法 | 关键假设 | 估值 | 权重 |
|:---|:---|---:|:---:|
| DCF | WACC={wacc}%，g={terminal_growth}% | {dcf_value}亿元 | {dcf_weight}% |
| 可比公司 | 选取{peer_count}家，中位数PE={peer_pe}x | {peer_value}亿元 | {peer_weight}% |
| **综合估值** | - | **{weighted_value}亿元** | 每股{per_share}元 |

---

## 五、风险全景

| 风险类别 | 具体风险 | 发生概率 | 影响程度 | 量化影响 |
|:---|:---|:---:|:---:|:---|
| 经营风险 | {risk1_desc} | {risk1_prob}% | {risk1_impact} | {risk1_quant} |
| 财务风险 | {risk2_desc} | {risk2_prob}% | {risk2_impact} | {risk2_quant} |
| 行业风险 | {risk3_desc} | {risk3_prob}% | {risk3_impact} | {risk3_quant} |
| 宏观风险 | {risk4_desc} | {risk4_prob}% | {risk4_impact} | {risk4_quant} |

**综合风险评级**：{overall_risk}（{risk_emoji}）

---

## 六、调查结论与建议

| 问题 | 调查判断 |
|:---|:---|
| **投资评级** | {investment_rating}（{rating_emoji}） |
| **合理价值** | {fair_value}亿元（{fair_per_share}元/股） |
| **安全边际** | {margin_of_safety}% |

---

## 七、免责声明

**免责声明**：本报告基于公开信息和合理假设编制，不构成投资建议。调查方对信息准确性不作保证，使用者应独立判断并承担风险。

---

**报告版本**：V{version} | **编制日期**：{date}
"""

# ───────────────────────────────────────────────────────────
# 模板9：短线助手
# ───────────────────────────────────────────────────────────
TEMPLATE_SHORT_TERM = """\
# ⚡ 龙虾短线助手 | {date} {time}

> 情绪周期：{emotion_phase} | 数据截至：{data_time}

---

## 一、情绪温度计

**当前阶段**：{emotion_phase} {emotion_emoji}

| 指标 | 数据 | 信号 | 解读 |
|:---|:---|:---:|:---|
| 涨停家数 | {limit_up_count}家 | {lu_signal} | {lu_comment} |
| 连板高度 | {max_boards}板 | {mb_signal} | {mb_comment} |
| 昨日涨停今表现 | {last_limit_up_performance}% | {llu_signal} | {llu_comment} |
| 炸板率 | {explode_rate}% | {er_signal} | {er_comment} |

**情绪判断**：{emotion_summary}
**可否出手**：{can_trade}（{trade_condition}）

---

## 二、热点狙击（TOP3）

### 🔥 {theme1}（强度：{t1_strength}）

| 维度 | 内容 |
|:---|:---|
| **驱动因素** | {t1_driver} |
| **涨停家数** | {t1_count}家 |
| **连板梯队** | {t1_ladder} |
| **持续性预判** | {t1_sustain} |

**梯队拆解**：
- **龙头**（{t1_leader_boards}板）：{t1_leader}
- **中军**：{t1_mid}

**参与策略**：{t1_strategy}

---

## 三、今日机会清单

| 代码 | 名称 | 题材 | 买点策略 | 仓位 | 止损 | 预期 |
|:---|:---|:---|:---|:---:|:---|:---|
| {code1} | {name1} | {theme1} | {buy_strategy1} | 20% | {stop1} | {expect1} |

---

## 四、🚨 风险预警

### 核按钮风险

| 标的 | 风险类型 | 原因 | 建议 |
|:---|:---|:---|:---|
| {nuke1_code} | {nuke1_type} | {nuke1_reason} | {nuke1_advice} |

### 今日避坑

- ❌ **{avoid1}**：{avoid1_reason}

---

## 五、操作清单

**今日总仓位建议**：{total_position}%

**空仓信号**（出现任一即空仓）：
- 炸板率>50%
- 昨日涨停今表现<0%
- 连板高度压缩至3板以下

---

## 六、龙虾寄语

> {lobster_quote}

---

**数据**：{data_sources} | **免责声明**：短线高风险，严格执行止损，盈亏自负。
"""

# ───────────────────────────────────────────────────────────
# 模板10：ETF优选
# ───────────────────────────────────────────────────────────
TEMPLATE_ETF = """\
# 🦞 龙虾ETF优选 | {date}

> 优选周期：{cycle} | 数据截至：{data_date} | 下次更新：{next_update}

---

## 一、宏观定仓

**配置模式**：{market_mode} {mode_emoji}
> 🔥 进攻模式 | ⚖️ 震荡模式 | 🛡️ 防守模式

| 指标 | 数据 | 信号 | 解读 |
|:---|:---|:---:|:---|
| 美联储政策 | {fed_policy} | {fed_signal} | {fed_comment} |
| 10Y美债利率 | {bond_yield}% | {bond_signal} | {bond_comment} |
| 美元指数 | {dxy} | {dxy_signal} | {dxy_comment} |
| VIX指数 | {vix} | {vix_signal} | {vix_comment} |

**战略仓位**：权益{equity}% + 债券{bond}% + 商品{commodity}%

---

## 二、TOP5品类

| 排名 | 品类 | 核心逻辑 | 政策 | 景气 | 技术 | 资金 | 综合 |
|:---:|:---|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | **{category1}** | {c1_logic} | {c1_policy} | {c1_prosperity} | {c1_tech} | {c1_fund} | 🟢 |
| 2 | **{category2}** | {c2_logic} | {c2_policy} | {c2_prosperity} | {c2_tech} | {c2_fund} | 🟢 |
| 3 | **{category3}** | {c3_logic} | {c3_policy} | {c3_prosperity} | {c3_tech} | {c3_fund} | 🟢 |

---

## 三、精选标的

### 3.1 {category1}品类（仓位{alloc1}%）

| 代码 | 名称 | 核心逻辑 | 目标价 | 止损价 | 仓位 |
|:---|:---|:---|---:|---:|:---:|
| {c1_code1} | {c1_name1} | {c1_logic1} | {c1_t1}元 | {c1_s1}元 | {c1_p1}% |

**{c1_name1}详解**：
- **投资逻辑**：{c1_detail_logic}
- **业绩表现**：近1月{c1_1m}%/3月{c1_3m}%/1年{c1_1y}%
- **估值分析**：PE{c1_pe}倍（{c1_pepct}%分位）
- **风险提示**：{c1_risk}

---

## 四、组合配置与风控体系

**仓位分布**：
- 核心仓位（60%）：{core_etfs}
- 卫星仓位（30%）：{satellite_etfs}
- 对冲仓位（10%）：{hedge_etfs}

**动态止盈止损矩阵**：

| 策略 | 触发条件 | 执行动作 |
|:---|:---|:---|
| 硬性止损 | 浮亏≥-8%或破20日线 | 减仓50%，剩余设-12%止损 |
| 移动止盈 | 收益≥15%后回撤5% | 减仓至成本线 |
| 溢价风控 | 跨境ETF溢价>3% | 暂停买入 |

---

## 五、龙虾寄语

> {lobster_quote}

---

**数据来源**：{data_sources} | **免责声明**：本优选结果由AI生成，仅供参考，不构成投资建议。
"""

# ───────────────────────────────────────────────────────────
# 模板11：技术研报
# ───────────────────────────────────────────────────────────
TEMPLATE_TECH = """\
# 🔬 前沿技术深度研究 | {tech_name}

> 研究日期：{date} | 数据截至：{data_date} | 评级有效期：6个月

---

## 一、技术快照

| 指标 | 评估 | 信号 | 关键数据 |
|:---|:---|:---:|:---|
| **技术评级** | **{rating}** | {rating_emoji} | 预期商业化时间：{time_to_market} |
| **TRL等级** | TRL {trl} | {trl_emoji} | 距离量产：{gap_to_prod}年 |
| **资本热度** | {capital_heat} | {heat_emoji} | 近12月融资：{funding_12m}亿美元 |
| **成本平价** | {cost_parity} | {cost_emoji} | 当前成本：{current_cost} vs 目标{target_cost} |

**AI速读**：{ai_summary}（150字内）

---

## 二、技术原理与突破点

### 2.1 核心原理

**{tech_name}** 是一种{tech_category}技术，核心原理为：
> {core_principle}

### 2.2 当前技术瓶颈

| 瓶颈类型 | 具体问题 | 当前水平 | 目标水平 | 突破难度 |
|:---|:---|---:|---:|:---:|
| 材料 | {material_issue} | {mat_current} | {mat_target} | {mat_diff} |
| 工艺 | {process_issue} | {proc_current} | {proc_target} | {proc_diff} |

---

## 三、商业化路径与应用场景

### 3.1 应用场景优先级

| 应用场景 | 技术适配度 | 市场紧迫度 | 商业化时间 | 市场规模 |
|:---|:---:|:---:|:---:|:---:|
| {app1} | {fit1} | {urgency1} | {time1} | {size1}亿 |
| {app2} | {fit2} | {urgency2} | {time2} | {size2}亿 |

### 3.2 成本平价分析

| 成本维度 | 当前水平 | 年降速 | 平价临界点 | 预计达成 |
|:---|:---:|:---:|:---:|:---:|
| 单位成本 | {unit_cost} | {decline_rate}% | {parity_point} | {parity_time} |

---

## 四、全球竞争格局

### 4.1 技术路线对比

| 路线 | 代表机构 | TRL | 性能 | 成本 | 产业化进度 |
|:---|:---|:---:|:---:|:---:|:---:|
| {route_a}（主流） | {leader_a} | {trl_a} | {perf_a} | {cost_a} | {progress_a} |
| {route_b}（挑战） | {leader_b} | {trl_b} | {perf_b} | {cost_b} | {progress_b} |

---

## 五、投资策略

| 问题 | AI判断 |
|:---|:---|
| **技术评级** | {rating} |
| **最佳投资时点** | {timing} |
| **推荐细分机会** | {oppty1} > {oppty2} |

---

## 六、龙虾寄语

> {lobster_quote}

---

**数据来源**：{data_sources} | **免责声明**：本报告由AI生成，仅供参考。
"""

# ───────────────────────────────────────────────────────────
# 模板12：科技风向标
# ───────────────────────────────────────────────────────────
TEMPLATE_TECH_TREND = """\
# 🚀 科技风向标 | {date}

> 追踪前沿科技动态 | 数据截至：{data_time}

---

## 一、本期焦点

| 科技热点 | 热度 | 关键进展 | 投资启示 |
|:---|:---:|:---|:---|
| {hot1} | 🔥🔥🔥 | {hot1_progress} | {hot1_implication} |
| {hot2} | 🔥🔥 | {hot2_progress} | {hot2_implication} |
| {hot3} | 🔥 | {hot3_progress} | {hot3_implication} |

---

## 二、技术动态追踪

### 2.1 突破性进展

| 时间 | 机构 | 突破内容 | 可信度 | 影响评估 |
|:---|:---|:---|:---:|:---:|
| {t1} | {org1} | {break1} | {cred1} | {impact1} |

### 2.2 产业应用落地

| 应用 | 技术 | 落地进展 | 商业化时间 |
|:---|:---|:---|:---:|
| {app1} | {tech1} | {progress1} | {time1} |

---

## 三、投资机会扫描

| 赛道 | 核心标的 | 投资逻辑 | 风险 |
|:---|:---|:---|:---|
| {track1} | {stock1} | {thesis1} | {risk1} |
| {track2} | {stock2} | {thesis2} | {risk2} |

---

## 四、风险提示

| 风险类型 | 具体风险 | 发生概率 |
|:---|:---|:---:|
| 科学失败 | {risk1_desc} | {risk1_prob}% |
| 政策阻断 | {risk2_desc} | {risk2_prob}% |

---

## 五、龙虾寄语

> {lobster_quote}

---

**免责声明**：本报告由AI生成，仅供参考，不构成投资建议。
"""

# ───────────────────────────────────────────────────────────
# 模板13：期货妙手
# ───────────────────────────────────────────────────────────
TEMPLATE_FUTURES = """\
# 🎯 期货妙手 | {variety_name}策略日报 | {date}

> 数据截至：{data_time} | 主力合约：{main_contract} | 下次更新：{next_update}

---

## 一、品种快照

| 指标 | 数据 | 信号 | 解读 |
|:---|:---|:---:|:---|
| **主力合约** | {main_price} | {price_signal} | 较昨日{price_chg}% |
| **期限结构** | {term_structure} | {ts_emoji} | {ts_comment} |
| **基差** | {basis}元 | {basis_signal} | {basis_comment} |
| **库存** | {inventory}万吨 | {inv_signal} | {inv_comment} |
| **趋势评级** | **{trend_rating}** | {trend_emoji} | {trend_comment} |

**AI速读**：{ai_summary}（150字内）

---

## 二、期限结构深度分析

### 2.1 全期限结构

| 合约月份 | 收盘价 | 较主力价差 | 持仓量 | 结构信号 |
|:---|---:|---:|---:|:---:|
| {m1} | {p1} | {s1} | {oi1} | {sig1} |
| {m2} | {p2} | {s2} | {oi2} | {sig2} |

**结构形态**：{structure_shape}（Super Back/Back/Flat/Contango/Super Contango）

### 2.2 期限结构策略

| 策略 | 操作 | 适用条件 | 预期收益 | 当前适配度 |
|:---|:---|:---|:---|:---:|
| 正套 | 买近卖远 | Back结构+库存下降 | 价差收敛 | {arbitrage1_fit} |
| 反套 | 卖近买远 | Contango+库存上升 | 价差扩大 | {arbitrage2_fit} |

---

## 三、基差与库存分析

### 3.1 基差全景

| 指标 | 当前值 | 历史分位 | 信号 |
|:---|---:|---:|:---:|
| 主力基差 | {main_basis} | {main_basis_pct}% | {main_basis_sig} |

### 3.2 库存周期定位

| 库存类型 | 当前值 | 环比 | 历史分位 | 信号 |
|:---|---:|---:|:---:|:---:|
| 交易所库存 | {ex_inv} | {ex_chg}% | {ex_pct}% | {ex_sig} |

---

## 四、供需平衡表

| 季度 | 供给 | 需求 | 缺口/过剩 | 价格预判 |
|:---|---:|---:|---:|:---:|
| {q1} | {s1} | {d1} | {g1} | {p1} |
| {q2} | {s2} | {d2} | {g2} | {p2} |

---

## 五、资金与持仓分析

| 席位类型 | 多单持仓 | 空单持仓 | 净持仓 | 信号 |
|:---|---:|---:|---:|:---:|
| 前20多头 | {top20_long} | - | - | {long_sig} |
| 前20空头 | - | {top20_short} | - | {short_sig} |
| **前20净持仓** | - | - | {top20_net} | {net_sig} |

---

## 六、策略矩阵

### 6.1 单边策略

| 策略 | 方向 | 合约 | 入场价位 | 止损价位 | 目标价位 | 仓位 | 盈亏比 |
|:---|:---:|:---|:---:|---:|---:|---:|:---:|
| 趋势跟踪 | {dir1} | {con1} | {entry1} | {stop1} | {target1} | {pos1}% | {rr1}:1 |

### 6.2 套利策略

| 策略 | 组合 | 当前价差 | 历史分位 | 仓位 | 胜率 |
|:---|:---|---:|:---:|:---:|:---:|
| 跨期正套 | {spread1} | {s1_val} | {s1_pct}% | {s1_pos}% | {s1_win}% |

---

## 七、风险监测与预警

### 7.1 交割月风险

| 风险类型 | 当前状态 | 预警级别 | 预案 |
|:---|:---|:---:|:---|
| 逼仓风险 | {squeeze_status} | {squeeze_level} | {squeeze_plan} |
| 流动性风险 | {liquidity_status} | {liquidity_level} | {liquidity_plan} |

### 7.2 宏观黑天鹅

| 风险场景 | 概率 | 影响幅度 | 对冲策略 |
|:---|:---:|:---:|:---|
| 美元暴涨 | {risk1_prob}% | {risk1_mag}% | {risk1_hedge} |

---

## 八、龙虾寄语

> {lobster_quote}

---

**数据**：{data_sources} | **免责声明**：期货交易风险极高，杠杆可能导致本金全部损失甚至穿仓。本报告仅供参考，不构成投资建议。
"""

# ───────────────────────────────────────────────────────────
# 模板14：社会发展报告
# ───────────────────────────────────────────────────────────
TEMPLATE_SOCIAL_DEV = """\
# 📊 社会发展报告 | {date}

> 追踪社会变迁趋势 | 数据截至：{data_time}

---

## 一、本期核心主题

**主题**：{main_theme}
**影响评估**：{impact_level}

---

## 二、人口结构变迁

| 指标 | 当前值 | 变化趋势 | 影响分析 |
|:---|:---|:---:|:---|
| 人口增长率 | {pop_growth}% | {pop_trend} | {pop_impact} |
| 老龄化率 | {aging_rate}% | {aging_trend} | {aging_impact} |
| 城镇化率 | {urban_rate}% | {urban_trend} | {urban_impact} |

---

## 三、消费趋势演变

| 消费群体 | 核心特征 | 趋势 | 投资机会 |
|:---|:---|:---:|:---|
| {group1} | {char1} | {trend1} | {oppty1} |
| {group2} | {char2} | {trend2} | {oppty2} |

---

## 四、技术对社会的影响

| 技术 | 影响领域 | 渗透速度 | 社会效应 |
|:---|:---|:---:|:---|
| {tech1} | {area1} | {speed1} | {effect1} |

---

## 五、龙虾寄语

> {lobster_quote}

---

**免责声明**：本报告由AI生成，仅供参考。
"""

# ───────────────────────────────────────────────────────────
# 模板15：社会金融报告
# ───────────────────────────────────────────────────────────
TEMPLATE_SOCIAL_FINANCE = """\
# 💳 社会金融报告 | {date}

> 追踪金融与社会融合趋势 | 数据截至：{data_time}

---

## 一、本期核心主题

**主题**：{main_theme}

---

## 二、支付趋势

| 指标 | 当前值 | 同比变化 | 信号 |
|:---|:---|:---:|:---:|
| 移动支付渗透率 | {mobile_pay_rate}% | {mobile_pay_chg}% | {mobile_signal} |
| 现金使用率 | {cash_usage}% | {cash_chg}% | {cash_signal} |

---

## 三、信贷趋势

| 信贷类型 | 规模 | 变化 | 风险提示 |
|:---|:---|:---:|:---|
| 消费贷 | {consumer_loan}亿 | {cl_chg}% | {cl_risk} |
| 小微贷 | {smb_loan}亿 | {sl_chg}% | {sl_risk} |

---

## 四、财富管理趋势

| 趋势 | 规模 | 增速 | 投资启示 |
|:---|:---|:---:|:---|
| {trend1} | {scale1}亿 | {growth1}% | {implication1} |

---

## 五、龙虾寄语

> {lobster_quote}

---

**免责声明**：本报告由AI生成，仅供参考。
"""
