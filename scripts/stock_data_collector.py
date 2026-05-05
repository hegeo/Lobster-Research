# -*- coding: utf-8 -*-
"""
龙虾调研助手 - 股票数据采集器
Stock Data Collector for Professional Research Reports

本脚本提供标准化的股票数据采集功能，适用于企业研报、个股深度分析等专家模式报告。
整合了ticktime.py、stock_master.py等多种数据源。

功能：
1. 实时行情数据获取
2. 历史K线数据获取与技术指标计算
3. 个股详细资料下载
4. 综合数据输出

使用示例：
    python scripts/stock_data_collector.py --code 000063 --name 中兴通讯
    python scripts/stock_data_collector.py --code 000063 --output json
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ticktime import StockDataAPI


def get_realtime_quote(stock_code: str) -> Dict[str, Any]:
    """
    获取实时行情数据
    
    Args:
        stock_code: 股票代码，如 "000063"
        
    Returns:
        实时行情数据字典
    """
    api = StockDataAPI()
    
    # 先尝试深圳
    result = api.get_realtime_stock(f'sz{stock_code}')
    if not result.get('success'):
        # 再尝试上海
        result = api.get_realtime_stock(f'sh{stock_code}')
    
    if result.get('success'):
        data = result.get('data', {})
        return {
            'code': stock_code,
            'name': data.get('名称', ''),
            'price': data.get('当前价', 0.0),
            'change': data.get('涨跌额', 0.0),
            'change_pct': data.get('涨跌幅(%)', 0.0),
            'open': data.get('今开', 0.0),
            'high': data.get('最高', 0.0),
            'low': data.get('最低', 0.0),
            'pre_close': data.get('昨收', 0.0),
            'volume': data.get('成交量(手)', 0),
            'turnover': data.get('成交额(元)', 0.0),
            'time': data.get('时间', ''),
            'source': data.get('数据源', ''),
        }
    else:
        print(f"获取 {stock_code} 实时行情失败")
        return {}


def get_history_kline(stock_code: str, days: int = 90) -> List[Dict[str, Any]]:
    """
    获取历史K线数据
    
    Args:
        stock_code: 股票代码
        days: 获取天数，默认90天
        
    Returns:
        K线数据列表
    """
    api = StockDataAPI()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    end_date_str = end_date.strftime('%Y%m%d')
    start_date_str = start_date.strftime('%Y%m%d')
    
    kline_data = api.get_history_kline(stock_code, start_date_str, end_date_str, 'day')
    
    return kline_data


def calculate_moving_averages(closes: List[float]) -> Dict[str, float]:
    """
    计算移动平均线
    
    Args:
        closes: 收盘价列表
        
    Returns:
        各周期均线字典
    """
    mas = {}
    periods = [5, 10, 20, 60]
    
    for period in periods:
        if len(closes) >= period:
            mas[f'ma{period}'] = sum(closes[-period:]) / period
        else:
            mas[f'ma{period}'] = sum(closes) / len(closes) if closes else 0.0
    
    return mas


def calculate_technical_indicators(kline_data: List[Dict], realtime_data: Dict) -> Dict[str, Any]:
    """
    计算完整技术指标
    
    Args:
        kline_data: K线数据
        realtime_data: 实时行情数据
        
    Returns:
        技术指标字典
    """
    if not kline_data or len(kline_data) < 20:
        return {}
    
    closes = [item['收盘'] for item in kline_data]
    highs = [item['最高'] for item in kline_data]
    lows = [item['最低'] for item in kline_data]
    volumes = [item['成交量(手)'] for item in kline_data]
    
    latest_close = closes[-1]
    latest_volume = volumes[-1]
    
    # 计算均线
    mas = calculate_moving_averages(closes)
    
    # 涨跌幅计算
    change_5d = ((closes[-1] - closes[-6]) / closes[-6] * 100) if len(closes) >= 6 else 0.0
    change_20d = ((closes[-1] - closes[-21]) / closes[-21] * 100) if len(closes) >= 21 else 0.0
    change_60d = ((closes[-1] - closes[0]) / closes[0] * 100) if len(closes) > 0 else 0.0
    
    # 振幅
    amplitude_5d = ((max(highs[-5:]) - min(lows[-5:])) / min(lows[-5:]) * 100) if len(highs) >= 5 else 0.0
    amplitude_20d = ((max(highs[-20:]) - min(lows[-20:])) / min(lows[-20:]) * 100) if len(highs) >= 20 else 0.0
    
    # 支撑压力位（近20日）
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    
    resistance_1 = max(recent_highs[-5:]) if len(recent_highs) >= 5 else max(recent_highs)
    resistance_2 = max(recent_highs)
    support_1 = min(recent_lows[-5:]) if len(recent_lows) >= 5 else min(recent_lows)
    support_2 = mas.get('ma20', latest_close * 0.95)
    
    # 趋势判断
    short_trend = "向上" if latest_close > mas.get('ma5', 0) else "向下"
    mid_trend = "向上" if latest_close > mas.get('ma20', 0) else "向下"
    long_trend = "向上" if latest_close > mas.get('ma60', latest_close * 1.1) else "向下"
    
    # 量能分析
    avg_volume_5 = sum(volumes[-5:]) / 5 / 10000 if len(volumes) >= 5 else 0.0
    avg_volume_20 = sum(volumes[-20:]) / 20 / 10000 if len(volumes) >= 20 else 0.0
    
    if latest_volume > avg_volume_5 * 1.2:
        volume_status = "放量"
    elif latest_volume < avg_volume_5 * 0.8:
        volume_status = "缩量"
    else:
        volume_status = "平量"
    
    # 综合评分（满分90分）
    tech_score = 0
    if latest_close > mas.get('ma5', 0): tech_score += 10
    if latest_close > mas.get('ma20', 0): tech_score += 10
    if latest_close > mas.get('ma60', 0): tech_score += 10
    if mas.get('ma5', 0) > mas.get('ma10', 0): tech_score += 10
    if mas.get('ma10', 0) > mas.get('ma20', 0): tech_score += 10
    if change_5d > 0: tech_score += 10
    if change_20d > 0: tech_score += 10
    if latest_volume > avg_volume_20: tech_score += 10
    if closes[-1] > closes[-2] if len(closes) >= 2 else False: tech_score += 10
    
    # 评级
    if tech_score >= 70:
        tech_rating = "强势"
    elif tech_score >= 50:
        tech_rating = "中性"
    else:
        tech_rating = "弱势"
    
    return {
        # 价格信息
        'current_price': round(latest_close, 2),
        'price_change': round(realtime_data.get('change', 0), 2),
        'price_change_pct': round(realtime_data.get('change_pct', 0), 2),
        'open': round(realtime_data.get('open', 0), 2),
        'high': round(realtime_data.get('high', 0), 2),
        'low': round(realtime_data.get('low', 0), 2),
        'pre_close': round(realtime_data.get('pre_close', 0), 2),
        
        # 成交信息
        'volume': latest_volume,
        'turnover': realtime_data.get('turnover', 0.0),
        'avg_volume_5': round(avg_volume_5, 2),
        'avg_volume_20': round(avg_volume_20, 2),
        'volume_status': volume_status,
        
        # 均线系统
        'ma5': round(mas.get('ma5', 0), 2),
        'ma10': round(mas.get('ma10', 0), 2),
        'ma20': round(mas.get('ma20', 0), 2),
        'ma60': round(mas.get('ma60', 0), 2),
        
        # 趋势
        'short_trend': short_trend,
        'mid_trend': mid_trend,
        'long_trend': long_trend,
        
        # 涨跌幅
        'change_5d': round(change_5d, 2),
        'change_20d': round(change_20d, 2),
        'change_60d': round(change_60d, 2),
        
        # 振幅
        'amplitude_5d': round(amplitude_5d, 2),
        'amplitude_20d': round(amplitude_20d, 2),
        
        # 支撑压力
        'resistance_1': round(resistance_1, 2),
        'resistance_2': round(resistance_2, 2),
        'support_1': round(support_1, 2),
        'support_2': round(support_2, 2),
        
        # 综合评分
        'tech_score': tech_score,
        'tech_rating': tech_rating,
    }


def collect_all_data(stock_code: str, stock_name: str = '') -> Dict[str, Any]:
    """
    采集股票的所有数据
    
    Args:
        stock_code: 股票代码
        stock_name: 股票名称（可选）
        
    Returns:
        包含所有数据的字典
    """
    print(f"[开始] 采集 {stock_code} {stock_name} 的数据...")
    
    # 1. 实时行情
    print("[步骤1/3] 获取实时行情...")
    realtime = get_realtime_quote(stock_code)
    if not realtime:
        print("[错误] 获取实时行情失败")
        return {}
    
    if not stock_name:
        stock_name = realtime.get('name', stock_code)
    
    # 2. 历史K线
    print("[步骤2/3] 获取历史K线...")
    kline = get_history_kline(stock_code, days=90)
    
    # 3. 技术指标
    print("[步骤3/3] 计算技术指标...")
    technical = calculate_technical_indicators(kline, realtime)
    
    result = {
        'stock_code': stock_code,
        'stock_name': stock_name,
        'collection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'realtime': realtime,
        'kline_count': len(kline),
        'technical': technical,
    }
    
    print(f"[完成] 数据采集完成，共 {len(kline)} 条K线")
    return result


def print_report(data: Dict[str, Any]):
    """
    打印数据报告
    
    Args:
        data: 采集的数据
    """
    if not data:
        print("无数据")
        return
    
    tech = data.get('technical', {})
    
    print("\n" + "=" * 60)
    print(f"=== {data['stock_name']} ({data['stock_code']}) 数据报告 ===")
    print("=" * 60)
    
    print(f"\n【实时行情】")
    print(f"  当前价: {tech.get('current_price', 0):.2f}元")
    print(f"  涨跌幅: {tech.get('price_change_pct', 0):+.2f}%")
    print(f"  成交量: {tech.get('volume', 0):.0f}手")
    print(f"  成交额: {tech.get('turnover', 0)/10000:.2f}万元")
    
    print(f"\n【均线系统】")
    print(f"  MA5:  {tech.get('ma5', 0):.2f}")
    print(f"  MA10: {tech.get('ma10', 0):.2f}")
    print(f"  MA20: {tech.get('ma20', 0):.2f}")
    print(f"  MA60: {tech.get('ma60', 0):.2f}")
    
    print(f"\n【趋势判断】")
    print(f"  短期趋势: {tech.get('short_trend', '')}")
    print(f"  中期趋势: {tech.get('mid_trend', '')}")
    print(f"  长期趋势: {tech.get('long_trend', '')}")
    
    print(f"\n【阶段涨跌】")
    print(f"  近5日:  {tech.get('change_5d', 0):+.2f}%")
    print(f"  近20日: {tech.get('change_20d', 0):+.2f}%")
    print(f"  近60日: {tech.get('change_60d', 0):+.2f}%")
    
    print(f"\n【支撑压力】")
    print(f"  压力位1: {tech.get('resistance_1', 0):.2f}")
    print(f"  压力位2: {tech.get('resistance_2', 0):.2f}")
    print(f"  支撑位1: {tech.get('support_1', 0):.2f}")
    print(f"  支撑位2: {tech.get('support_2', 0):.2f}")
    
    print(f"\n【综合评分】")
    print(f"  评分: {tech.get('tech_score', 0)}/90分")
    print(f"  评级: {tech.get('tech_rating', '')}")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='股票数据采集器 - 用于专家模式研报',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python scripts/stock_data_collector.py --code 000063 --name 中兴通讯
  python scripts/stock_data_collector.py --code 000063 --output json
  python scripts/stock_data_collector.py --code 000858 --name 五粮液 --days 120
        '''
    )
    
    parser.add_argument('--code', '-c', required=True, help='股票代码')
    parser.add_argument('--name', '-n', default='', help='股票名称')
    parser.add_argument('--days', '-d', type=int, default=90, help='获取K线天数，默认90天')
    parser.add_argument('--output', '-o', choices=['print', 'json'], default='print', 
                        help='输出格式：print(打印) 或 json(JSON格式)')
    parser.add_argument('--save', '-s', help='保存到JSON文件路径')
    
    args = parser.parse_args()
    
    # 采集数据
    data = collect_all_data(args.code, args.name)
    
    if not data:
        print("[错误] 数据采集失败")
        return
    
    # 输出
    if args.output == 'json':
        json_output = json.dumps(data, ensure_ascii=False, indent=2)
        print(json_output)
        
        if args.save:
            with open(args.save, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"\n[保存] 数据已保存到: {args.save}")
    else:
        print_report(data)
        
        if args.save:
            with open(args.save, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n[保存] 数据已保存到: {args.save}")


if __name__ == '__main__':
    main()
