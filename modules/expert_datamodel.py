# -*- coding: utf-8 -*-
"""
🦞 龙虾智能调研助手 - 专家模式数据模型
Expert Mode Data Model for Professional Research Reports

本模块定义专家模式下各类研报的标准数据结构和采集规范。
适用于企业研报、行业研报、个股深度分析等需要详细数据的报告类型。

标准报告规格：
- 字数：6000-7500字
- 章节：8-10章
- 数据维度：基本面 + 技术面 + 资金面 + 行业面
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TechnicalMetrics:
    """技术指标数据结构"""
    current_price: float = 0.0           # 当前价格
    price_change: float = 0.0            # 涨跌额
    price_change_pct: float = 0.0        # 涨跌幅(%)
    volume: int = 0                      # 成交量(手)
    turnover: float = 0.0                # 成交额(元)
    
    # 均线系统
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    
    # 趋势判断
    short_trend: str = ""                # 短期趋势: 向上/向下/震荡
    mid_trend: str = ""                  # 中期趋势
    long_trend: str = ""                 # 长期趋势
    
    # 支撑压力位
    support_1: float = 0.0               # 第一支撑位
    support_2: float = 0.0               # 第二支撑位
    resistance_1: float = 0.0            # 第一压力位
    resistance_2: float = 0.0            # 第二压力位
    
    # 阶段涨跌幅
    change_5d: float = 0.0               # 近5日涨跌
    change_20d: float = 0.0              # 近20日涨跌
    change_60d: float = 0.0              # 近60日涨跌
    amplitude_20d: float = 0.0           # 近20日振幅
    
    # 综合评分
    tech_score: int = 0                  # 技术面评分(满分90)
    tech_rating: str = ""                # 评级: 强势/中性/弱势
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'current_price': self.current_price,
            'price_change': self.price_change,
            'price_change_pct': self.price_change_pct,
            'volume': self.volume,
            'turnover': self.turnover,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'ma60': self.ma60,
            'short_trend': self.short_trend,
            'mid_trend': self.mid_trend,
            'long_trend': self.long_trend,
            'support_1': self.support_1,
            'support_2': self.support_2,
            'resistance_1': self.resistance_1,
            'resistance_2': self.resistance_2,
            'change_5d': self.change_5d,
            'change_20d': self.change_20d,
            'change_60d': self.change_60d,
            'amplitude_20d': self.amplitude_20d,
            'tech_score': self.tech_score,
            'tech_rating': self.tech_rating,
        }


@dataclass
class FinancialMetrics:
    """财务指标数据结构"""
    # 营收利润
    revenue: float = 0.0                 # 营业总收入(亿元)
    revenue_yoy: float = 0.0             # 营收同比(%)
    net_profit: float = 0.0              # 归母净利润(亿元)
    net_profit_yoy: float = 0.0          # 净利润同比(%)
    net_profit_deducted: float = 0.0     # 扣非净利润(亿元)
    
    # 每股收益和净资产
    eps: float = 0.0                     # 每股收益(元)
    bps: float = 0.0                     # 每股净资产(元)
    
    # 盈利能力
    gross_margin: float = 0.0            # 毛利率(%)
    net_margin: float = 0.0              # 净利率(%)
    roe: float = 0.0                     # 净资产收益率(%)
    
    # 资产负债
    total_assets: float = 0.0            # 总资产(亿元)
    total_liabilities: float = 0.0       # 总负债(亿元)
    net_assets: float = 0.0              # 净资产(亿元)
    debt_ratio: float = 0.0              # 资产负债率(%)
    cash: float = 0.0                    # 现金及等价物(亿元)
    
    # 现金流
    operating_cash_flow: float = 0.0     # 经营现金流(亿元)
    investing_cash_flow: float = 0.0     # 投资现金流(亿元)
    financing_cash_flow: float = 0.0     # 筹资现金流(亿元)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'revenue': self.revenue,
            'revenue_yoy': self.revenue_yoy,
            'net_profit': self.net_profit,
            'net_profit_yoy': self.net_profit_yoy,
            'net_profit_deducted': self.net_profit_deducted,
            'eps': self.eps,
            'bps': self.bps,
            'gross_margin': self.gross_margin,
            'net_margin': self.net_margin,
            'roe': self.roe,
            'total_assets': self.total_assets,
            'total_liabilities': self.total_liabilities,
            'net_assets': self.net_assets,
            'debt_ratio': self.debt_ratio,
            'cash': self.cash,
            'operating_cash_flow': self.operating_cash_flow,
            'investing_cash_flow': self.investing_cash_flow,
            'financing_cash_flow': self.financing_cash_flow,
        }


@dataclass
class InstitutionRating:
    """机构评级数据结构"""
    institution: str = ""                # 机构名称
    rating: str = ""                     # 评级: 买入/增持/中性/减持
    target_price: float = 0.0            # 目标价
    key_points: str = ""                 # 核心观点
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'institution': self.institution,
            'rating': self.rating,
            'target_price': self.target_price,
            'key_points': self.key_points,
        }


@dataclass
class InvestmentAdvice:
    """投资建议数据结构"""
    timeframe: str = ""                  # 投资期限: 短期/中期/长期
    rating: str = ""                     # 评级
    strategy: str = ""                   # 操作策略
    key_levels: str = ""                 # 关键价位
    focus_points: str = ""               # 关注要点
    risk_return: str = ""                # 风险收益比
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timeframe': self.timeframe,
            'rating': self.rating,
            'strategy': self.strategy,
            'key_levels': self.key_levels,
            'focus_points': self.focus_points,
            'risk_return': self.risk_return,
        }


@dataclass
class CompanyReportData:
    """
    企业研报完整数据结构
    基于中兴通讯v4研报经验总结
    """
    # 基础信息
    title: str = ""                      # 报告标题
    subtitle: str = ""                   # 副标题
    date: str = ""                       # 报告日期
    author: str = "龙虾财经研究院"        # 报告作者
    summary: str = ""                    # 核心摘要
    quote: str = ""                      # 引言/金句
    disclaimer: str = ""                 # 免责声明
    
    # 核心指标卡条
    metrics: List[Dict[str, str]] = field(default_factory=list)
    
    # 核心速览表
    overview_table: Dict[str, Any] = field(default_factory=dict)
    
    # 技术分析指标
    technical: TechnicalMetrics = field(default_factory=TechnicalMetrics)
    
    # 财务指标
    financial: FinancialMetrics = field(default_factory=FinancialMetrics)
    
    # 机构评级列表
    institution_ratings: List[InstitutionRating] = field(default_factory=list)
    
    # 分阶段投资建议
    investment_advices: List[InvestmentAdvice] = field(default_factory=list)
    
    # 章节内容
    sections: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_report_dict(self) -> Dict[str, Any]:
        """转换为报告生成器所需的字典格式"""
        return {
            'title': self.title,
            'subtitle': self.subtitle,
            'date': self.date,
            'author': self.author,
            'summary': self.summary,
            'quote': self.quote,
            'disclaimer': self.disclaimer,
            'metrics': self.metrics,
            'overview_table': self.overview_table,
            'sections': self.sections,
        }


class ExpertReportBuilder:
    """
    专家模式报告构建器
    提供标准化的报告数据构建流程
    """
    
    def __init__(self, report_type: str = "company_report"):
        self.report_type = report_type
        self.data = CompanyReportData()
        
    def set_basic_info(self, title: str, subtitle: str, date: str, 
                       summary: str, quote: str = "") -> 'ExpertReportBuilder':
        """设置基础信息"""
        self.data.title = title
        self.data.subtitle = subtitle
        self.data.date = date
        self.data.summary = summary
        self.data.quote = quote
        return self
        
    def set_technical_metrics(self, metrics: TechnicalMetrics) -> 'ExpertReportBuilder':
        """设置技术指标"""
        self.data.technical = metrics
        return self
        
    def set_financial_metrics(self, metrics: FinancialMetrics) -> 'ExpertReportBuilder':
        """设置财务指标"""
        self.data.financial = metrics
        return self
        
    def add_institution_rating(self, rating: InstitutionRating) -> 'ExpertReportBuilder':
        """添加机构评级"""
        self.data.institution_ratings.append(rating)
        return self
        
    def add_investment_advice(self, advice: InvestmentAdvice) -> 'ExpertReportBuilder':
        """添加投资建议"""
        self.data.investment_advices.append(advice)
        return self
        
    def set_sections(self, sections: List[Dict[str, Any]]) -> 'ExpertReportBuilder':
        """设置章节内容"""
        self.data.sections = sections
        return self
        
    def build(self) -> Dict[str, Any]:
        """构建最终报告数据"""
        return self.data.to_report_dict()


# 标准报告模板配置
EXPERT_REPORT_TEMPLATES = {
    'company_report': {
        'name': '企业研报',
        'min_words': 6000,
        'max_words': 7500,
        'required_chapters': [
            '🦞 龙虾提示：行情指标与投资导航',
            '公司概况与股权结构',
            '财务深度分析',
            '业务深度解析',
            '行业竞争格局',
            '核心催化剂',
            '投资亮点与风险',
            '估值与投资建议',
            '股东回报与ESG',
        ],
        'required_data': [
            'technical',      # 技术指标
            'financial',      # 财务数据
            'institution_ratings',  # 机构评级
            'investment_advices',   # 投资建议
        ],
    },
    'industry_report': {
        'name': '行业研报',
        'min_words': 6000,
        'max_words': 7500,
        'required_chapters': [
            '行业概览',
            '产业链分析',
            '竞争格局',
            '政策环境',
            '发展趋势',
            '投资机会',
            '风险提示',
        ],
        'required_data': [
            'market_size',    # 市场规模
            'growth_rate',    # 增长率
            'key_players',    # 主要玩家
            'policy',         # 政策
        ],
    },
    'stock_analysis': {
        'name': '个股深度分析',
        'min_words': 5000,
        'max_words': 6500,
        'required_chapters': [
            '公司概况',
            '财务分析',
            '技术分析',
            '估值分析',
            '投资建议',
        ],
        'required_data': [
            'technical',
            'financial',
        ],
    },
}


def get_template_config(report_type: str) -> Dict[str, Any]:
    """获取报告模板配置"""
    return EXPERT_REPORT_TEMPLATES.get(report_type, EXPERT_REPORT_TEMPLATES['company_report'])


def validate_report_data(data: Dict[str, Any], report_type: str) -> List[str]:
    """
    验证报告数据完整性
    返回缺失的必填字段列表
    """
    config = get_template_config(report_type)
    missing = []
    
    # 检查必填字段
    required_fields = ['title', 'subtitle', 'date', 'summary', 'sections']
    for field in required_fields:
        if not data.get(field):
            missing.append(field)
    
    # 检查章节数量
    sections = data.get('sections', [])
    min_chapters = len(config['required_chapters'])
    if len(sections) < min_chapters:
        missing.append(f"章节数量不足(需要至少{min_chapters}章，当前{len(sections)}章)")
    
    return missing
