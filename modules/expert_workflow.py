# -*- coding: utf-8 -*-
"""
🦞 龙虾智能调研助手 - 专家模式工作流
Expert Mode Workflow for Professional Research Reports

本模块定义专家模式下研报生成的标准工作流程。
适用于需要完整、详细数据的报告类型（企业研报、行业研报、个股深度分析）。

标准报告规格：
- 字数：6000-7500字
- 章节：8-10章
- 数据来源：ticktime.py + stock_master.py + websearch_pro.py + akshare_api_kit.py

工作流程：
1. 配置加载 -> 2. 数据采集 -> 3. 数据整合 -> 4. 报告生成 -> 5. PDF导出
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DataSourceConfig:
    """数据源配置"""
    use_ticktime: bool = True          # 使用ticktime获取实时行情和历史K线
    use_stock_master: bool = True      # 使用stock_master获取个股详细资料
    use_websearch: bool = True         # 使用websearch_pro获取新闻和资讯
    use_akshare: bool = False          # 使用akshare_api_kit获取补充数据
    

def step1_load_config() -> Dict[str, Any]:
    """
    步骤1：加载配置
    从config/config.py读取用户配置
    """
    from config.config import (
        INVESTMENT_STYLE, TOTAL_ASSETS, OPREATION_FREQ, RISK_LEVEL,
        USER_SETED
    )
    
    return {
        'investment_style': INVESTMENT_STYLE,
        'total_assets': TOTAL_ASSETS,
        'operation_freq': OPREATION_FREQ,
        'risk_level': RISK_LEVEL,
        'user_configured': USER_SETED == 'YES',
    }


def step2_collect_technical_data(stock_code: str) -> Dict[str, Any]:
    """
    步骤2.1：采集技术数据
    使用ticktime.py获取实时行情和历史K线
    
    Args:
        stock_code: 股票代码，如 "000063"
        
    Returns:
        技术指标数据字典
    """
    from scripts.ticktime import StockDataAPI
    
    api = StockDataAPI()
    
    # 获取实时行情
    raw = api.get_realtime_stock(f'sz{stock_code}')  # 默认深圳，上海用sh
    if not raw.get('success'):
        # 尝试上海
        raw = api.get_realtime_stock(f'sh{stock_code}')
    # 解包 success/data 格式
    realtime_data = raw.get('data', {}) if raw.get('success') else {}
    
    # 获取历史K线（近3个月）
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now().replace(month=datetime.now().month-3)).strftime('%Y%m%d')
    kline_data = api.get_history_kline(stock_code, start_date, end_date, 'day')
    
    # 计算技术指标
    technical_metrics = calculate_technical_metrics(kline_data, realtime_data)
    
    return {
        'realtime': realtime_data,
        'kline': kline_data,
        'metrics': technical_metrics,
    }


def calculate_technical_metrics(kline_data: List[Dict], realtime_data: Dict) -> Dict[str, Any]:
    """
    计算技术指标
    
    Returns:
        包含完整技术指标的字典
    """
    if not kline_data or len(kline_data) < 20:
        return {}
    
    closes = [item['收盘'] for item in kline_data]
    highs = [item['最高'] for item in kline_data]
    lows = [item['最低'] for item in kline_data]
    volumes = [item['成交量(手)'] for item in kline_data]
    
    latest_close = closes[-1]
    
    # 计算均线
    ma5 = sum(closes[-5:]) / 5
    ma10 = sum(closes[-10:]) / 10
    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else sum(closes) / len(closes)
    
    # 计算涨跌幅
    change_5d = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0
    change_20d = (closes[-1] - closes[-21]) / closes[-21] * 100 if len(closes) >= 21 else 0
    change_60d = (closes[-1] - closes[0]) / closes[0] * 100
    
    # 计算振幅
    amplitude_20d = (max(highs[-20:]) - min(lows[-20:])) / min(lows[-20:]) * 100
    
    # 支撑压力位
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    resistance_1 = max(recent_highs[-5:])
    resistance_2 = max(recent_highs)
    support_1 = min(recent_lows[-5:])
    support_2 = ma20
    
    # 趋势判断
    short_trend = "向上" if latest_close > ma5 else "向下"
    mid_trend = "向上" if latest_close > ma20 else "向下"
    long_trend = "向上" if latest_close > ma60 else "向下"
    
    # 量能分析
    avg_volume_5 = sum(volumes[-5:]) / 5 / 10000
    avg_volume_20 = sum(volumes[-20:]) / 20 / 10000
    latest_volume = volumes[-1] / 10000
    
    # 综合评分
    tech_score = 0
    if latest_close > ma5: tech_score += 10
    if latest_close > ma20: tech_score += 10
    if latest_close > ma60: tech_score += 10
    if ma5 > ma10: tech_score += 10
    if ma10 > ma20: tech_score += 10
    if change_5d > 0: tech_score += 10
    if change_20d > 0: tech_score += 10
    if latest_volume > avg_volume_20: tech_score += 10
    if closes[-1] > closes[-2]: tech_score += 10
    
    if tech_score >= 70:
        tech_rating = "强势"
    elif tech_score >= 50:
        tech_rating = "中性"
    else:
        tech_rating = "弱势"
    
    return {
        'current_price': latest_close,
        'price_change': realtime_data.get('涨跌额', 0),
        'price_change_pct': realtime_data.get('涨跌幅(%)', 0),
        'volume': volumes[-1],
        'turnover': realtime_data.get('成交额(元)', 0),
        'ma5': ma5,
        'ma10': ma10,
        'ma20': ma20,
        'ma60': ma60,
        'short_trend': short_trend,
        'mid_trend': mid_trend,
        'long_trend': long_trend,
        'resistance_1': resistance_1,
        'resistance_2': resistance_2,
        'support_1': support_1,
        'support_2': support_2,
        'change_5d': change_5d,
        'change_20d': change_20d,
        'change_60d': change_60d,
        'amplitude_20d': amplitude_20d,
        'tech_score': tech_score,
        'tech_rating': tech_rating,
    }


def step2_collect_financial_data(stock_code: str) -> Dict[str, Any]:
    """
    步骤2.2：采集财务数据
    使用stock_master.py获取个股详细财务资料
    
    Args:
        stock_code: 股票代码
        
    Returns:
        财务数据字典
    """
    import subprocess
    import json
    
    # 调用stock_master下载数据
    try:
        result = subprocess.run(
            ['python', 'scripts/stock_master.py', '-code', stock_code],
            capture_output=True,
            text=True,
            timeout=60
        )
    except Exception as e:
        print(f"采集财务数据失败: {e}")
        return {}
    
    # 读取生成的文本文件
    data_dir = f'stock_data/{stock_code}'
    financial_data = {}
    
    try:
        # 读取公司资料
        corp_file = os.path.join(data_dir, f'{stock_code}_corp_plain.txt')
        if os.path.exists(corp_file):
            with open(corp_file, 'r', encoding='utf-8') as f:
                financial_data['corporate'] = f.read()
        
        # 读取财务数据
        finance_file = os.path.join(data_dir, f'{stock_code}_finance_plain.txt')
        if os.path.exists(finance_file):
            with open(finance_file, 'r', encoding='utf-8') as f:
                financial_data['finance'] = f.read()
        
        # 读取基本信息
        info_file = os.path.join(data_dir, f'{stock_code}_info_plain.txt')
        if os.path.exists(info_file):
            with open(info_file, 'r', encoding='utf-8') as f:
                financial_data['info'] = f.read()
                
    except Exception as e:
        print(f"读取财务数据文件失败: {e}")
    
    return financial_data


def step2_collect_news_and_research(stock_name: str, keywords: List[str]) -> Dict[str, Any]:
    """
    步骤2.3：采集新闻和研报资讯
    使用websearch_pro.py搜索相关资讯
    
    Args:
        stock_name: 股票名称，如 "中兴通讯"
        keywords: 搜索关键词列表
        
    Returns:
        新闻和研报数据字典
    """
    import subprocess
    import json
    
    search_results = {}
    
    # 搜索股票最新动态
    try:
        result = subprocess.run(
            ['python', 'scripts/websearch_pro.py', f'{stock_name} 2026年 业绩 财报', '--limit', '10'],
            capture_output=True,
            text=True,
            timeout=30
        )
        search_results['latest_news'] = result.stdout
    except Exception as e:
        print(f"搜索最新动态失败: {e}")
    
    # 搜索机构评级
    try:
        result = subprocess.run(
            ['python', 'scripts/websearch_pro.py', f'{stock_name} 机构评级 增持 买入 目标价', '--limit', '8'],
            capture_output=True,
            text=True,
            timeout=30
        )
        search_results['institution_ratings'] = result.stdout
    except Exception as e:
        print(f"搜索机构评级失败: {e}")
    
    # 搜索行业和竞争信息
    try:
        result = subprocess.run(
            ['python', 'scripts/websearch_pro.py', f'{stock_name} {keywords[0]} 竞争对手 市场份额', '--limit', '8'],
            capture_output=True,
            text=True,
            timeout=30
        )
        search_results['industry'] = result.stdout
    except Exception as e:
        print(f"搜索行业信息失败: {e}")
    
    return search_results


def step3_build_report_data(
    technical_data: Dict[str, Any],
    financial_data: Dict[str, Any],
    news_data: Dict[str, Any],
    company_name: str,
    stock_code: str,
    report_title: str,
    report_subtitle: str
) -> Dict[str, Any]:
    """
    步骤3：整合数据构建报告
    
    Args:
        technical_data: 技术数据
        financial_data: 财务数据
        news_data: 新闻数据
        company_name: 公司名称
        stock_code: 股票代码
        report_title: 报告标题
        report_subtitle: 报告副标题
        
    Returns:
        完整的报告数据字典
    """
    from modules.expert_datamodel import (
        TechnicalMetrics, FinancialMetrics, 
        InstitutionRating, InvestmentAdvice
    )
    
    current_date = datetime.now().strftime('%Y年%m月%d日')
    
    # 构建技术指标对象
    tech = technical_data.get('metrics', {})
    technical_metrics = TechnicalMetrics(**tech)
    
    # 构建报告数据结构
    report_data = {
        'title': report_title,
        'subtitle': report_subtitle,
        'date': current_date,
        'author': '龙虾财经研究院',
        'summary': f'{company_name}是全球第四大通信设备商，国内5G市场份额稳居第二。',
        'quote': '投资不是赌方向，而是计算概率与赔率后的理性决策。',
        'disclaimer': '免责声明：本报告由AI生成，数据来源于公开网络，仅供参考，不构成投资建议。',
        
        # 指标卡条
        'metrics': [
            {'label': '当前股价', 'value': f"{tech.get('current_price', 0):.2f}元", 
             'change': f"{tech.get('price_change_pct', 0):+.2f}% {'🟢' if tech.get('price_change_pct', 0) > 0 else '🔴'}"},
            {'label': '总市值', 'value': '计算中...', 'change': 'A股'},
            {'label': '技术面评分', 'value': f"{tech.get('tech_score', 0)}/90分", 
             'change': tech.get('tech_rating', '')},
        ],
        
        # 核心速览表
        'overview_table': {
            'headers': ['维度', '评估', '信号', '要点'],
            'rows': [
                ['企业质地', '行业龙头企业', '🟢', '技术实力强'],
                ['财务健康', '营收增长利润承压', '🟡', '转型期'],
                ['技术趋势', f"{tech.get('short_trend', '')}/{tech.get('mid_trend', '')}", 
                 '🟢' if tech.get('tech_score', 0) >= 70 else '🟡', '综合评分良好'],
                ['投资评级', '增持', '🟡', '目标价待计算'],
            ]
        },
        
        # 章节内容将在后续填充
        'sections': []
    }
    
    return report_data


def step4_generate_report(report_data: Dict[str, Any], report_type: str = 'company_report') -> Dict[str, Any]:
    """
    步骤4：生成报告
    
    Args:
        report_data: 报告数据
        report_type: 报告类型
        
    Returns:
        报告生成结果
    """
    from scripts.generate_report import generate_report
    
    result = generate_report(
        user_input=report_data['title'],
        explicit_type=report_type,
        data=report_data,
        output_format='html',
        style='blue'
    )
    
    return result


def step5_export_pdf(html_path: str, pdf_path: str) -> bool:
    """
    步骤5：导出PDF
    使用Chrome headless将HTML转换为PDF
    
    Args:
        html_path: HTML文件路径
        pdf_path: PDF输出路径
        
    Returns:
        是否成功
    """
    import subprocess
    
    try:
        # 转换文件路径为URL格式
        html_url = html_path.replace('\\', '/').replace(' ', '%20')
        if not html_url.startswith('file:///'):
            html_url = 'file:///' + html_url
        
        result = subprocess.run(
            [
                'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                '--headless',
                '--disable-gpu',
                f'--print-to-pdf={pdf_path}',
                '--print-to-pdf-no-header',
                html_url
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return result.returncode == 0
    except Exception as e:
        print(f"PDF导出失败: {e}")
        return False


class ExpertReportGenerator:
    """
    专家模式报告生成器
    提供一键生成完整研报的功能
    """
    
    def __init__(self, stock_code: str, stock_name: str, 
                 report_type: str = 'company_report'):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.report_type = report_type
        self.technical_data = {}
        self.financial_data = {}
        self.news_data = {}
        self.report_data = {}
        
    def collect_all_data(self) -> 'ExpertReportGenerator':
        """采集所有必要数据"""
        print(f"🔄 开始采集 {self.stock_name}({self.stock_code}) 的数据...")
        
        print("📊 采集技术数据...")
        self.technical_data = step2_collect_technical_data(self.stock_code)
        
        print("📈 采集财务数据...")
        self.financial_data = step2_collect_financial_data(self.stock_code)
        
        print("📰 采集新闻资讯...")
        self.news_data = step2_collect_news_and_research(
            self.stock_name, 
            ['竞争对手', '行业趋势']
        )
        
        print("✅ 数据采集完成")
        return self
    
    def build_report(self, title: str = None, subtitle: str = None) -> 'ExpertReportGenerator':
        """构建报告数据"""
        if title is None:
            title = f'{self.stock_name}企业深度研报'
        if subtitle is None:
            subtitle = '全球通信设备龙头，算力第二曲线加速崛起'
            
        self.report_data = step3_build_report_data(
            self.technical_data,
            self.financial_data,
            self.news_data,
            self.stock_name,
            self.stock_code,
            title,
            subtitle
        )
        return self
    
    def generate(self, output_dir: str = 'output') -> Dict[str, str]:
        """
        生成报告并导出PDF
        
        Returns:
            包含html_path和pdf_path的字典
        """
        import os
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成报告
        print("📝 生成HTML报告...")
        result = step4_generate_report(self.report_data, self.report_type)
        
        if not result.get('success'):
            print(f"❌ 报告生成失败: {result.get('error')}")
            return {}
        
        html_path = result.get('html_path', '')
        
        # 生成PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"{self.stock_code}_{self.report_type}_{timestamp}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        print(f"📄 导出PDF: {pdf_path}")
        if step5_export_pdf(html_path, pdf_path):
            print("✅ PDF导出成功")
        else:
            print("❌ PDF导出失败")
            pdf_path = ""
        
        return {
            'html_path': html_path,
            'pdf_path': pdf_path,
        }


def generate_company_report(stock_code: str, stock_name: str) -> Dict[str, str]:
    """
    一键生成企业研报的便捷函数
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        
    Returns:
        报告文件路径
        
    Example:
        >>> result = generate_company_report('000063', '中兴通讯')
        >>> print(result['pdf_path'])
    """
    generator = ExpertReportGenerator(stock_code, stock_name, 'company_report')
    
    return (
        generator
        .collect_all_data()
        .build_report()
        .generate()
    )


# 质量控制检查清单
QUALITY_CHECKLIST = """
专家模式研报质量检查清单：

□ 字数检查：6000-7500字
□ 章节检查：8-10章
□ 数据完整性检查：
  □ 技术指标：均线、支撑压力、趋势判断、综合评分
  □ 财务指标：营收、利润、现金流、资产负债
  □ 机构评级：至少3-5家机构观点
  □ 分阶段建议：短期/中期/长期
□ 数据来源标注：ticktime、stock_master、websearch_pro
□ 风险提示：已包含风险提示章节
□ 免责声明：已包含免责声明
□ 数据时效性：检查数据是否为最新
"""

if __name__ == '__main__':
    # 示例用法
    print("专家模式工作流模块")
    print("=" * 50)
    print(QUALITY_CHECKLIST)
