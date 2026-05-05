import requests
import json
import random
from typing import Dict, List, Optional, Union


class StockDataAPI:
    """
    股票数据统一API（新浪为主，腾讯为备用）
    支持：实时大盘、实时个股、大盘历史K线、个股历史K线、个股盘口
    """
    def __init__(self):
        # 新浪请求头
        self.sina_headers = {
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # 腾讯请求头
        self.tencent_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://stock.finance.qq.com/"
        }
        self.session = requests.Session()

    # ===================== 通用工具方法 =====================
    def _format_code(self, code: str) -> str:
        """统一股票代码格式（补全sh/sz前缀）"""
        if code.startswith(('sh', 'sz')):
            return code
        # 沪市6开头，深市0/3开头
        prefix = "sh" if code.startswith("6") else "sz"
        return f"{prefix}{code}"

    def _sina_request(self, url: str) -> Optional[str]:
        """新浪请求封装"""
        try:
            resp = self.session.get(url, headers=self.sina_headers, timeout=8)
            resp.raise_for_status()
            return resp.text.strip()
        except Exception:
            return None

    def _tencent_request(self, url: str) -> Optional[str]:
        """腾讯请求封装"""
        try:
            resp = self.session.get(url, headers=self.tencent_headers, timeout=8)
            resp.raise_for_status()
            return resp.text.strip()
        except Exception:
            return None

    # ===================== 1. 实时大盘 =====================
    def get_realtime_index(self) -> Dict[str, Dict]:
        """
        获取实时大盘指数（上证指数+深证成指）
        优先新浪，失败则用腾讯
        """
        
    def get_realtime_index(self) -> Dict[str, Dict]:
        # 新浪实现
        def _sina_impl():
            result = {}
            for code in ["sh000001", "sz399001", "sz399006"]:
                url = f"http://hq.sinajs.cn/list={code}"
                text = self._sina_request(url)
                if not text:
                    return None
                try:
                    content = text.split('="')[1].rstrip('";')
                    data = content.split(',')
                    result[code] = {
                        "代码": code,
                        "名称": data[0],
                        "当前价": float(data[3]),
                        "涨跌额": round(float(data[3]) - float(data[2]), 2),
                        "涨跌幅(%)": round((float(data[3]) - float(data[2])) / float(data[2]) * 100, 2),
                        "今开": float(data[1]),
                        "最高": float(data[4]),
                        "最低": float(data[5]),
                        "昨收": float(data[2]),
                        "成交量(手)": int(data[8]) // 100,
                        "成交额(元)": float(data[9]),
                        "数据源": "新浪"
                    }
                except Exception:
                    return None
            return result

        # 腾讯实现（备用）
        def _tencent_impl():
            result = {}
            for code in ["sh000001", "sz399001", "sz399006"]:
                url = f"http://qt.gtimg.cn/q={code}"
                text = self._tencent_request(url)
                if not text:
                    return None
                try:
                    data_part = text.split('="')[1].rstrip('"')
                    fields = data_part.split('~')
                    result[code] = {
                        "代码": fields[2],
                        "名称": fields[1],
                        "当前价": fields[3],
                        "涨跌额": fields[4],
                        "涨跌幅(%)": fields[5],
                        "今开": fields[6],
                        "最高": fields[7],
                        "最低": fields[8],
                        "昨收": fields[9],
                        "成交量(手)": fields[10],
                        "成交额(万)": fields[11],
                        "换手率": fields[12],
                        "市盈率": fields[13],
                        "市净率": fields[14],
                        "数据源": "腾讯"
                    }
                except Exception:
                    return None
            return result

        # 优先新浪，失败用腾讯
        return _sina_impl() or _tencent_impl() or {"error": "新浪/腾讯均获取大盘数据失败"}

    # ===================== 2. 实时个股 =====================
    def get_realtime_stock(self, code: str) -> Dict:
        """
        获取个股实时行情
        :param code: 股票代码（如600000 / sz000001 / sh600000）
        """
        code = self._format_code(code)
        
        # 新浪实现
        def _sina_impl():
            url = f"http://hq.sinajs.cn/list={code}"
            text = self._sina_request(url)
            if not text:
                return None
            try:
                content = text.split('="')[1].rstrip('";')
                data = content.split(',')
                return {
                    "代码": code,
                    "名称": data[0],
                    "当前价": float(data[3]),
                    "涨跌额": round(float(data[3]) - float(data[2]), 2),
                    "涨跌幅(%)": round((float(data[3]) - float(data[2])) / float(data[2]) * 100, 2),
                    "今开": float(data[1]),
                    "最高": float(data[4]),
                    "最低": float(data[5]),
                    "昨收": float(data[2]),
                    "成交量(手)": int(data[8]) // 100,
                    "成交额(元)": float(data[9]),
                    "时间": f"{data[30]} {data[31]}",
                    "数据源": "新浪"
                }
            except Exception:
                return None

        # 腾讯实现（备用）
        def _tencent_impl():
            url = f"http://qt.gtimg.cn/q={code}"
            text = self._tencent_request(url)
            if not text:
                return None
            try:
                data_part = text.split('="')[1].rstrip('"')
                fields = data_part.split('~')
                return {
                    "代码": fields[2],
                    "名称": fields[1],
                    "当前价": fields[3],
                    "涨跌额": fields[4],
                    "涨跌幅(%)": fields[5],
                    "今开": fields[6],
                    "最高": fields[7],
                    "最低": fields[8],
                    "昨收": fields[9],
                    "成交量(手)": fields[10],
                    "成交额(万)": fields[11],
                    "换手率": fields[12],
                    "市盈率": fields[13],
                    "市净率": fields[14],
                    "数据源": "腾讯"
                }
            except Exception:
                return None

        return _sina_impl() or _tencent_impl() or {"error": f"获取{code}实时数据失败"}

    # ===================== 3. 历史K线（大盘/个股） =====================
    def get_history_kline(self, code: str, start: str, end: str, period: str = "day") -> List[Dict]:
        """
        获取历史K线（支持大盘/个股）
        :param code: 股票代码（如sh000001 / 600000）
        :param start: 开始日期（20260101）
        :param end: 结束日期（20260420）
        :param period: day=日线, week=周线, month=月线
        """
        code = self._format_code(code)
        period_map = {"day": 240, "week": 1680, "month": 7200}  # 新浪scale映射
        
        # 新浪实现
        def _sina_impl():
            scale = period_map.get(period, 240)
            url = (
                f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                f"CN_MarketData.getKLineData?symbol={code}&scale={scale}&ma=no&datalen=10000"
            )
            text = self._sina_request(url)
            if not text:
                return None
            try:
                data = json.loads(text)
                if not isinstance(data, list):
                    return None
                # 过滤日期范围
                result = []
                for item in data:
                    if start <= item['day'] <= end:
                        result.append({
                            "日期": item['day'],
                            "开盘": float(item['open']),
                            "收盘": float(item['close']),
                            "最高": float(item['high']),
                            "最低": float(item['low']),
                            "成交量(手)": int(item['volume']) // 100,
                            "成交额(元)": float(item['volume']) * float(item['close']),
                            "数据源": "新浪"
                        })
                return result
            except Exception:
                return None

        # 腾讯实现（备用）
        def _tencent_impl():
            rnd = random.random()
            url = (
                f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
                f"?_var=kline_{period}qfq"
                f"&param={code},{period},{start},{end},640,qfq"
                f"&r=0.{rnd}"
            )
            text = self._tencent_request(url)
            if not text:
                return None
            try:
                data = json.loads(text.split('=', 1)[-1])
                if not data or code not in data.get("data", {}):
                    return None
                kline_data = data["data"][code].get(period, [])
                result = []
                for item in kline_data:
                    result.append({
                        "日期": item[0],
                        "开盘": item[1],
                        "收盘": item[2],
                        "最高": item[3],
                        "最低": item[4],
                        "成交量(手)": item[5],
                        "成交额(万)": item[6],
                        "数据源": "腾讯"
                    })
                return result
            except Exception:
                return None

        return _sina_impl() or _tencent_impl() or []

    # ===================== 4. 个股盘口 =====================
    def get_stock_pankou(self, code: str) -> Dict:
        """
        获取个股盘口（买卖大单/小单分布）
        仅腾讯数据源支持，无备用
        :param code: 股票代码（如600000 / sz000858）
        """
        code = self._format_code(code)
        url = f"http://qt.gtimg.cn/q=s_pk{code}"
        
        try:
            text = self._tencent_request(url)
            if not text:
                return {"error": "盘口数据获取失败"}
            
            # 解析腾讯盘口格式
            content = text.split('"')[1]
            fields = content.split('~')
            return {
                "代码": code,
                "买盘大单": float(fields[0]),
                "买盘小单": float(fields[1]),
                "卖盘大单": float(fields[2]),
                "卖盘小单": float(fields[3]),
                "数据源": "腾讯"
            }
        except Exception as e:
            return {"error": f"盘口数据解析失败: {str(e)}"}


# ===================== 测试用例 =====================
if __name__ == "__main__":
    api = StockDataAPI()

    # 1. 实时大盘
    print("===== 1. 实时大盘指数 =====")
    index_data = api.get_realtime_index()
    print(json.dumps(index_data, ensure_ascii=False, indent=2))

    # 2. 实时个股（浦发银行）
    print("\n===== 2. 浦发银行 实时行情 =====")
    stock_realtime = api.get_realtime_stock("600000")
    print(json.dumps(stock_realtime, ensure_ascii=False, indent=2))

    # 3. 大盘历史K线（上证指数 20260101-20260420 日线）
    print("\n===== 3. 上证指数 历史日线（前5条） =====")
    index_kline = api.get_history_kline("sh000001", "20260101", "20260420", "day")
    print(json.dumps(index_kline[:5], ensure_ascii=False, indent=2))

    # 4. 个股历史K线（浦发银行 20260101-20260420 日线）
    print("\n===== 4. 浦发银行 历史日线（前5条） =====")
    stock_kline = api.get_history_kline("600000", "20260101", "20260420", "day")
    print(json.dumps(stock_kline[:5], ensure_ascii=False, indent=2))

    # 5. 个股盘口（五粮液）
    print("\n===== 5. 五粮液 盘口数据 =====")
    pankou_data = api.get_stock_pankou("sz000858")
    print(json.dumps(pankou_data, ensure_ascii=False, indent=2))