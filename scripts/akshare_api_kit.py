# -*- coding: utf-8 -*-
import akshare as ak
import pandas as pd
import json
import sys
from typing import Optional, Dict, List, Union

# ==============================================
# AKShare 股票数据统一封装（命令行版）
# ==============================================
class AKShareStockAPI:
    def __init__(self):
        # 修复：全 pandas 版本兼容的显示设置
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.max_rows', 20)

    # ==================== 1. 实时行情 ====================
    def get_realtime_a_stock(self):
        df = ak.stock_zh_a_spot()
        print("📊 A 股实时行情（前20条）")
        print(df.head(20))

    def get_realtime_individual(self, symbol: str):
        df = ak.stock_individual_spot_xq(symbol=symbol)
        print(f"📈 个股实时行情：{symbol}")
        print(df)

    # ==================== 2. 历史K线 ====================
    def get_hist_tx(self, symbol: str, start_date: str, end_date: str):
        df = ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start_date, end_date=end_date, adjust="")
        print(f"📅 {symbol} 历史K线 {start_date} ~ {end_date}")
        print(df.head(30))

    # ==================== 3. 板块 ====================
    def get_sector_sina(self):
        df = ak.stock_sector_spot(indicator="新浪行业")
        print("🏢 新浪行业板块")
        print(df.head(20))

    def get_concept_names(self):
        df = ak.stock_board_concept_name_ths()
        print("🔖 同花顺概念列表")
        print(df.head(30))

    # ==================== 4. 资金流向 ====================
    def get_hsgt_flow(self):
        df = ak.stock_hsgt_fund_flow_summary_em()
        print("🌏 北向资金概览")
        print(df)

    def get_fund_flow_rank(self):
        df = ak.stock_individual_fund_flow_rank(indicator="今日")
        print("💸 今日资金流排名")
        print(df.head(20))

    # ==================== 5. 新闻 ====================
    def get_stock_news(self, symbol: str):
        df = ak.stock_news_em(symbol=symbol)
        print(f"\n📰 {symbol} 最新新闻")
        print(df.head(15))

    def get_news_json(self, keyword: str) -> list:
        """获取新闻并以 JSON 格式返回列表，keyword 支持股票代码或关键词（如 A股、焦点）"""
        try:
            df = ak.stock_news_em(symbol=keyword)
            if df is None or df.empty:
                return []
            cols = [c for c in ["发布时间", "新闻标题", "新闻内容", "文章来源"] if c in df.columns]
            records = df[cols].head(20).to_dict(orient="records")
            # 将 Timestamp 等不可 JSON 序列化类型转为字符串
            return json.loads(json.dumps(records, ensure_ascii=False, default=str))
        except Exception as e:
            return [{"error": str(e), "keyword": keyword}]

    # ==================== 6. 热门股票 ====================
    def get_hot_stock(self):
        df = ak.stock_hot_follow_xq(symbol="最热门")
        print("🔥 雪球热门股票")
        print(df.head(20))


# ==================== 命令行调用入口 ====================
if __name__ == "__main__":
    api = AKShareStockAPI()

    # 解析 --json 标志
    json_mode = "--json" in sys.argv
    if json_mode:
        sys.argv.remove("--json")

    if len(sys.argv) < 2:
        print("="*70)
        print("使用方法（命令行输入）：")
        print("python stock.py 行情                # A股实时行情")
        print("python stock.py 个股 000001         # 平安银行实时行情")
        print("python stock.py k线 000001 20250101 20250420")
        print("python stock.py 板块                # 行业板块")
        print("python stock.py 概念                # 同花顺概念")
        print("python stock.py 北向                # 北向资金")
        print("python stock.py 资金排名            # 资金流排行")
        print("python stock.py 新闻 000001         # 个股新闻")
        print("python stock.py --json 新闻 A股     # A股市场新闻(JSON)")
        print("python stock.py --json 新闻 焦点    # 焦点新闻(JSON)")
        print("python stock.py 热门                # 热门股票")
        print("="*70)
        sys.exit()

    cmd = sys.argv[1]

    try:
        if cmd == "行情":
            api.get_realtime_a_stock()

        elif cmd == "个股":
            code = sys.argv[2]
            api.get_realtime_individual(code)

        elif cmd == "k线":
            code = sys.argv[2]
            sdate = sys.argv[3]
            edate = sys.argv[4]
            api.get_hist_tx(code, sdate, edate)

        elif cmd == "板块":
            api.get_sector_sina()

        elif cmd == "概念":
            api.get_concept_names()

        elif cmd == "北向":
            api.get_hsgt_flow()

        elif cmd == "资金排名":
            api.get_fund_flow_rank()

        elif cmd == "新闻":
            keyword = sys.argv[2]
            if json_mode:
                data = api.get_news_json(keyword)
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                api.get_stock_news(keyword)

        elif cmd == "热门":
            api.get_hot_stock()

        else:
            print("不支持的命令！")

    except Exception as e:
        print(f"出错：{e}")
        print("请检查参数格式是否正确")