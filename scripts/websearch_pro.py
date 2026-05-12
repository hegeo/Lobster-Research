# -*- coding: utf-8 -*-
"""
龙虾调研助手 - 多引擎联网搜索 v3.1（API 优先 + 兜底降级）
============================================================
架构：
  API 引擎（结构化 JSON，无 HTML 解析）:
    ① SerpBase  — Google 搜索代理（主推）
    ② Bing API  — Microsoft 官方 API
    ③ Tavily    — AI 搜索 API
    ④ ProSearch — 自定义网关（Auth Gateway，需手动启用）

  兜底引擎（HTML 抓取，反爬保护）:
    ⑤ Baidu        — baidusearch 库
    ⑥ Bing Intl    — 国际版 bing.com 直接请求（替代 Google）

  已废弃：360搜索（IP 封锁）、Google 直接请求（国内 429）、Bing HTML 抓取（旧版失效）

  优先级：按注册顺序依次尝试，任一引擎成功即返回
  质量评估：基于 title + snippet 内容关键词（不依赖 URL 域名）

用法（命令行）:
  python websearch_pro.py "关键词"
  python websearch_pro.py "关键词" fresh
  python websearch_pro.py "关键词" --limit 10

用法（API 调用）:
  from scripts.websearch_pro import run_batch_search
  results = run_batch_search(keyword_groups=[...])
"""

import sys, os, time, json, re, math, random
from difflib import SequenceMatcher
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8")

try:
    import requests
    from requests.adapters import HTTPAdapter
except ImportError:
    raise ImportError("请先安装依赖：pip install requests python-baidusearch")


# ==============================================================================
# 配置加载（仅 apis + engines + defaults）
# ==============================================================================
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SETTINGS_PATH = os.path.join(_PROJECT_ROOT, "config", "settings.json")


def _load_settings() -> dict:
    if os.path.exists(_SETTINGS_PATH):
        with open(_SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


_settings = _load_settings()
_ws = _settings.get("websearch_pro", {})

# ── API Keys ──
_apis = _ws.get("apis", {})
SERPBASE_API_KEY  = os.environ.get("SERPBASE_API_KEY", "")  or _apis.get("serpbase_api_key", "")
SERPBASE_BASE_URL = _apis.get("serpbase_base_url", "https://api.serpbase.dev")
BING_API_KEY      = os.environ.get("BING_API_KEY", "")      or _apis.get("bing_api_key", "")
BING_API_BASE     = _apis.get("bing_api_base", "https://api.bing.microsoft.com/v7.0/search")
TAVILY_API_KEY    = os.environ.get("TAVILY_API_KEY", "")    or _apis.get("tavily_api_key", "")
TAVILY_API_BASE   = _apis.get("tavily_api_base", "https://api.tavily.com/search")
PROSEARCH_BASE    = _apis.get("auth_gateway_base", "http://localhost:19000/proxy/prosearch/search")

# ── ProSearch 端口探测（避免无网关时超时等待 15s）──
_PROSEARCH_ENABLED = _ws.get("prosearch_enabled", False)

def _probe_prosearch() -> bool:
    """快速探测 ProSearch 网关是否在线（仅在显式启用时探测）"""
    if not _PROSEARCH_ENABLED:
        return False
    import socket
    try:
        port = int(PROSEARCH_BASE.split(":")[-1].split("/")[0])
        sock = socket.create_connection(("127.0.0.1", port), timeout=1.5)
        sock.close()
        return True
    except (socket.timeout, OSError, ValueError):
        return False

_PROSEARCH_ALIVE = _probe_prosearch()

# ── 引擎配置 ──
_engines_cfg = _ws.get("engines", {})
PRIMARY_ENGINE   = (os.environ.get("PRIMARY_ENGINE", "")   or _engines_cfg.get("primary", "")).strip().lower()
SECONDARY_ENGINE = (os.environ.get("SECONDARY_ENGINE", "") or _engines_cfg.get("secondary", "")).strip().lower()

# ── 引擎抓取/保留数 ──
_fetch_cfg = _engines_cfg.get("fetch_count", {})
_keep_cfg  = _engines_cfg.get("keep_count", {})

FETCH_COUNT = {
    "serpbase":    _fetch_cfg.get("serpbase", 10),
    "bing_api":    _fetch_cfg.get("bing_api", 10),
    "tavily":      _fetch_cfg.get("tavily", 5),
    "prosearch":   _fetch_cfg.get("prosearch", 10),
    "baidu":       _fetch_cfg.get("baidu", 12),
    "bing_intl":   _fetch_cfg.get("bing_intl", 10),
}
KEEP_COUNT = {
    "serpbase":    _keep_cfg.get("serpbase", 5),
    "bing_api":    _keep_cfg.get("bing_api", 5),
    "tavily":      _keep_cfg.get("tavily", 5),
    "prosearch":   _keep_cfg.get("prosearch", 5),
    "baidu":       _keep_cfg.get("baidu", 5),
    "bing_intl":   _keep_cfg.get("bing_intl", 5),
}

# ── 默认参数 ──
_defaults = _ws.get("defaults", {})
DEFAULT_LIMIT    = _defaults.get("global_max_results", 16)
DEFAULT_TIMEOUT  = _defaults.get("request_timeout", 12)
SIMILARITY_THRESHOLD = _defaults.get("similarity_threshold", 0.6)

# CLI mode
LIMIT = DEFAULT_LIMIT
FRESH = False


# ==============================================================================
# 内容质量评估（基于 title + snippet，不依赖 URL）
# ==============================================================================
_L5_MARKERS = [
    "国务院", "央行", "人民银行", "证监会", "发改委", "工信部", "财政部",
    "统计局", "海关总署", "新华社", "人民日报", "央视", "中央",
    "Nature", "Science", "柳叶刀", "中科院", "清华大学", "北大",
    "美联储", "FOMC", "IMF", "世界银行", "OECD",
]
_L4_MARKERS = [
    "研报", "研究报告", "机构评级", "目标价", "券商", "分析师",
    "财报", "年报", "季报", "营收", "净利润", "同比增长", "毛利率",
    "市盈率", "PE", "估值", "DCF", "EPS", "ROE", "ROIC",
    "招股书", "招股说明书", "IPO", "增发", "回购",
    "财新", "第一财经", "证券时报", "上海证券报", "21世纪经济",
    "36氪", "虎嗅", "界面", "澎湃新闻", "华尔街见闻",
]
_L3_MARKERS = [
    "据报道", "记者获悉", "数据显示", "统计", "发布", "公告",
    "消息", "报道", "透露", "表示", "指出", "认为",
    "行业", "市场", "板块", "赛道", "产业链", "供应链",
    "政策", "规划", "意见", "通知", "办法",
]
_L2_MARKERS = [
    "网友", "评论", "热议", "热搜", "刷屏", "爆了",
    "短视频", "直播", "网红", "带货", "种草",
]
_JUNK_MARKERS = [
    "广告", "推广", "加盟", "代理", "兼职", "赚钱", "免费领取",
    "优惠券", "折扣", "秒杀", "限时", "促销",
    "点击下载", "立即注册", "扫码", "关注公众号",
    "百家号", "好看视频", "搜狐号",
]


def _text_contains(text: str, markers: list) -> bool:
    t = text.lower()
    return any(m.lower() in t for m in markers)


def get_quality_score(title: str, snippet: str = "", url: str = "") -> int:
    """基于标题+snippet内容打分（1-5）"""
    combined = f"{title} {snippet}"
    for markers, level in [
        (_L5_MARKERS, 5), (_L4_MARKERS, 4), (_L3_MARKERS, 3), (_L2_MARKERS, 2),
    ]:
        if _text_contains(combined, markers):
            return level
    return 1


def is_junk(title: str, snippet: str = "") -> bool:
    """基于内容判断是否为垃圾/广告"""
    return _text_contains(f"{title} {snippet}", _JUNK_MARKERS)


# ==============================================================================
# 反反爬基础设施
# ==============================================================================
_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


def _build_headers(target_host: str = "") -> dict:
    ua = random.choice(_UA_POOL)
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    if target_host:
        headers["Host"] = target_host
        ref_map = {
            "www.google.com": "https://www.google.com/",
            "www.baidu.com": "https://www.baidu.com/",
        }
        headers["Referer"] = ref_map.get(target_host, f"https://{target_host}/")
    return headers


_session = requests.Session()
_adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

# ── 节流：API 引擎无需节流，HTML 抓取引擎才需要 ──
_last_request_ts = 0.0
_MIN_INTERVAL = 0.3   # 同域连续请求最小间隔（秒）
_JITTER_MAX    = 0.8  # 随机抖动上限（秒）


def _throttle():
    """仅用于 HTML 抓取引擎（baidu/google），API 引擎不调用"""
    global _last_request_ts
    elapsed = time.time() - _last_request_ts
    wait = _MIN_INTERVAL + random.uniform(0, _JITTER_MAX)
    if elapsed < wait:
        time.sleep(wait - elapsed)
    _last_request_ts = time.time()


def _api_throttle():
    """API 引擎的轻量节流（仅防突发，不防反爬）"""
    time.sleep(random.uniform(0, 0.15))


def _extract_host(url: str) -> str:
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except Exception:
        return ""


def fetch(url: str, timeout=DEFAULT_TIMEOUT, host_hint: str = "", max_retries: int = 2):
    """带完整伪装 + 重试的 HTTP GET。429 立即放弃（不浪费重试）"""
    host = host_hint or _extract_host(url)
    headers = _build_headers(host)
    for attempt in range(max_retries):
        _throttle()
        try:
            r = _session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            if r.status_code == 429:
                # 429 = 频率限制，重试无意义，立即放弃
                return None
            if r.status_code in (403, 503) and attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"  ⚠️ fetch {r.status_code}，{wait:.1f}s 后重试...", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
        except requests.exceptions.HTTPError:
            return None
        except Exception:
            if attempt == max_retries - 1:
                return None
            time.sleep(1 + random.uniform(0, 1))
    return None


def _decode_entities(text: str) -> str:
    """深度解码 HTML 实体，解决 SerpBase 等 API 返回的乱码/实体残留"""
    import html as _html_mod
    # 先用标准库解码 &amp; &#xxx; &#xHH; 等
    text = _html_mod.unescape(text)
    # 处理常见残留实体
    text = text.replace("\xa0", " ")  # non-breaking space
    text = text.replace("\u200b", "")  # zero-width space
    text = text.replace("\u200e", "")  # LTR mark
    text = text.replace("\u200f", "")  # RTL mark
    text = text.replace("\u202a", "").replace("\u202c", "")  # embedding marks
    return text


def clean(html: str) -> str:
    if not html:
        return ""
    html = _decode_entities(html)
    html = re.sub(r"(?is)<script.*?</script>", "", html)
    html = re.sub(r"(?is)<style.*?</style>", "", html)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;|&amp;|&lt;|&gt;|&quot;", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def parse_date(text: str) -> str:
    m = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|20\d{2}年\d{1,2}月\d{1,2}日)", text)
    if not m:
        return ""
    return m.group(1).replace("年", "-").replace("月", "-").replace("日", "")[:10]


# ==============================================================================
# API 引擎 ①：SerpBase（Google 搜索代理）
# ==============================================================================
def serpbase_search(keyword: str, days_n=None, fetch_limit=None) -> list:
    if not SERPBASE_API_KEY:
        return []
    if fetch_limit is None:
        fetch_limit = FETCH_COUNT["serpbase"]
    results = []
    _api_throttle()
    try:
        payload = {"q": keyword, "hl": "zh-CN", "gl": "cn"}
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": SERPBASE_API_KEY,
        }
        resp = requests.post(
            f"{SERPBASE_BASE_URL}/google/search",
            json=payload, headers=headers, timeout=20,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"
        data = resp.json()
        if data.get("status") != 0:
            err = data.get("error", f"status={data.get('status')}")
            print(f"  SerpBase 错误: {err}", file=sys.stderr)
            return []
        for item in data.get("organic", [])[:fetch_limit]:
            title   = clean(item.get("title", ""))
            url_val = item.get("link", "")
            snippet = clean(item.get("snippet", ""))[:300]
            if not title or len(title) < 4:
                continue
            results.append({
                "title": title, "url": url_val,
                "snippet": snippet, "date": parse_date(snippet),
                "source": "SerpBase",
            })
    except Exception as e:
        print(f"  SerpBase 失败: {str(e)[:60]}", file=sys.stderr)
    return results


# ==============================================================================
# API 引擎 ②：Bing API（Microsoft 官方）
# ==============================================================================
def bing_api_search(keyword: str, days_n=None, fetch_limit=None) -> list:
    if not BING_API_KEY:
        return []
    if fetch_limit is None:
        fetch_limit = FETCH_COUNT["bing_api"]
    results = []
    _api_throttle()
    try:
        params = {
            "q": keyword, "mkt": "zh-CN",
            "setLang": "zh-CN", "count": fetch_limit,
        }
        headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
        resp = requests.get(BING_API_BASE, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("webPages", {}).get("value", [])[:fetch_limit]:
            title   = clean(item.get("name", ""))
            url_val = item.get("url", "")
            snippet = clean(item.get("snippet", ""))[:300]
            date_str = item.get("dateLastCrawler", "")[:10] if item.get("dateLastCrawler") else ""
            if not title or len(title) < 4:
                continue
            results.append({
                "title": title, "url": url_val,
                "snippet": snippet, "date": date_str,
                "source": "BingAPI",
            })
    except Exception as e:
        print(f"  Bing API 失败: {str(e)[:60]}", file=sys.stderr)
    return results


# ==============================================================================
# API 引擎 ③：Tavily
# ==============================================================================
def tavily_search(keyword: str, days_n=None, fetch_limit=None) -> list:
    if not TAVILY_API_KEY:
        return []
    if fetch_limit is None:
        fetch_limit = FETCH_COUNT["tavily"]
    results = []
    _api_throttle()
    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": keyword,
            "search_depth": "basic",
            "max_results": fetch_limit,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }
        if days_n:
            payload["time_range"] = "week"
        resp = requests.post(TAVILY_API_BASE, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("results", [])[:fetch_limit]:
            results.append({
                "title": clean(item.get("title", "")),
                "url": item.get("url", ""),
                "snippet": clean(item.get("content", ""))[:300],
                "date": parse_date(item.get("content", "")),
                "source": "Tavily",
            })
    except Exception as e:
        print(f"  Tavily 失败: {str(e)[:60]}", file=sys.stderr)
    return results


# ==============================================================================
# 自定义引擎 ④：ProSearch（Auth Gateway）
# ==============================================================================
def prosearch(keyword: str, days_n=None, fetch_limit=None) -> list:
    if fetch_limit is None:
        fetch_limit = FETCH_COUNT["prosearch"]
    _api_throttle()
    try:
        payload = {"keyword": keyword, "cnt": fetch_limit}
        if days_n:
            payload["from_time"] = int(time.time()) - days_n * 86400
        import urllib.request
        req = urllib.request.Request(
            PROSEARCH_BASE,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as f:
            res = json.load(f)
        return [{
            "title": d["title"], "url": d["url"],
            "snippet": d.get("passage", d.get("snippet", ""))[:300],
            "date": d.get("date", "")[:10] if d.get("date") else "",
            "source": "ProSearch",
        } for d in res.get("data", {}).get("docs", [])[:fetch_limit]]
    except:
        return []


# ==============================================================================
# 兜底引擎 ⑤：百度搜索（baidusearch 库）
# ==============================================================================
def baidu_search(keyword: str, days_n=None, fetch_limit=None) -> list:
    if fetch_limit is None:
        fetch_limit = FETCH_COUNT["baidu"]
    try:
        from baidusearch.baidusearch import search
    except:
        return []
    # baidusearch 库内置 HTTP 处理，不做外部节流
    results = []
    for item in search(keyword=keyword, num_results=fetch_limit)[:fetch_limit]:
        results.append({
            "title": clean(item["title"]),
            "url": item["url"],
            "snippet": clean(item.get("abstract", ""))[:200],
            "date": parse_date(str(item)),
            "source": "Baidu",
        })
    return results


# ==============================================================================
# 兜底引擎 ⑥：国际版 Bing 直接请求（替代 Google）
# ==============================================================================
# 已知不可用的引擎（429/验证码 后静默跳过，不打印错误）
_known_dead: set = set()


def bing_intl_search(keyword: str, days_n=None, fetch_limit=None) -> list:
    """国际版 Bing 直接请求（兜底引擎）。通过 bing.com 获取英文/国际结果。"""
    if "bing_intl" in _known_dead:
        return []
    if fetch_limit is None:
        fetch_limit = FETCH_COUNT.get("bing_intl", 10)
    results = []
    _throttle()
    try:
        params = {"q": keyword, "setlang": "en-US", "cc": "US", "count": fetch_limit}
        if days_n:
            # Bing freshness filter: Day, Week, Month
            params["filters"] = f"ex1:\"ez5_{days_n}d\""
        url = f"https://www.bing.com/search?{requests.compat.urlencode(params)}"
        html = fetch(url, host_hint="www.bing.com", max_retries=2)
        if not html or ("captcha" in html.lower() or "unusual traffic" in html.lower()):
            _known_dead.add("bing_intl")
            return []

        # 解析 Bing 搜索结果
        # Bing 结果块：<li class="b_algo">...</li>
        blocks = re.findall(r'<li class="b_algo">(.*?)</li>', html, re.DOTALL)
        if not blocks:
            # 备选模式：某些 Bing 版本用 ol > li 结构
            blocks = re.findall(r'class="[^"]*b_algo[^"]*"(.*?)</li>', html, re.DOTALL)

        for block in blocks[:fetch_limit * 2]:
            # 标题
            title = ""
            for pat in [r'<h2[^>]*>(.*?)</h2>', r'<a[^>]*>(.*?)</a>']:
                m = re.search(pat, block, re.DOTALL)
                if m:
                    title = clean(m.group(1)).strip()
                    # 去除内部的 <a> 标签残留
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    if title and len(title) >= 4:
                        break
            if not title:
                continue

            # URL
            url_val = ""
            url_match = re.search(r'<a[^>]+href="(https?://[^"]+)"', block)
            if url_match:
                raw = url_match.group(1)
                skip = ["bing.com", "microsoft.com", "go.microsoft.com", "javascript:"]
                if not any(d in raw.lower() for d in skip):
                    url_val = raw.split("#")[0]

            # Snippet
            snippet = ""
            for pat in [
                r'<p[^>]*>(.*?)</p>',
                r'<div[^>]*class="[^"]*b_caption[^"]*"[^>]*>(.*?)</div>',
                r'<span[^>]*class="[^"]*c_.*?>(.*?)</span>',
            ]:
                m = re.search(pat, block, re.DOTALL)
                if m:
                    snippet = clean(m.group(1))[:300]
                    if snippet and len(snippet) >= 20:
                        break

            if not snippet or len(snippet) < 20:
                continue

            results.append({
                "title": title, "url": url_val,
                "snippet": snippet, "date": parse_date(block),
                "source": "BingIntl",
            })
            if len(results) >= fetch_limit:
                break
    except Exception as e:
        print(f"  Bing Intl 失败: {str(e)[:60]}", file=sys.stderr)
    return results


# ==============================================================================
# 引擎注册表 — 优先级从高到低
# ==============================================================================
# (name, fetch_fn, requires_key, is_api)
_ALL_ENGINES = [
    ("serpbase",    serpbase_search,   lambda: bool(SERPBASE_API_KEY), True),
    ("bing_api",    bing_api_search,   lambda: bool(BING_API_KEY),     True),
    ("tavily",      tavily_search,     lambda: bool(TAVILY_API_KEY),   True),
    ("prosearch",   prosearch,         lambda: _PROSEARCH_ALIVE,       True),
    ("baidu",       baidu_search,      lambda: True,                   False),
    ("bing_intl",   bing_intl_search,  lambda: True,                   False),
]


def _get_engine_registry() -> list:
    """
    根据 settings.json 的 primary/secondary 构建引擎注册表。

    规则：
      primary/secondary 均为空 → 返回空列表，运行时报错
      primary = "all" → 按注册表顺序，有 key 的全部启用
      否则 → primary 优先，secondary 次之，无 key 的跳过
    """
    all_names = {n for n, _, _, _ in _ALL_ENGINES}

    # 验证配置
    if not PRIMARY_ENGINE and not SECONDARY_ENGINE:
        print("❌ 未指定搜索引擎，请检查 config/settings.json 的 engines.primary / engines.secondary", file=sys.stderr)
        return []

    if PRIMARY_ENGINE == "all":
        # all 模式：按注册表顺序，无 key 的跳过
        return [(n, f, k, a) for n, f, k, a in _ALL_ENGINES if k()]

    # 指定模式：primary → secondary → 其余（跳过无 key 的）
    primary = [(n, f, k, a) for n, f, k, a in _ALL_ENGINES if n == PRIMARY_ENGINE]
    secondary = [(n, f, k, a) for n, f, k, a in _ALL_ENGINES if n == SECONDARY_ENGINE]
    rest = [(n, f, k, a) for n, f, k, a in _ALL_ENGINES if n not in (PRIMARY_ENGINE, SECONDARY_ENGINE)]

    return primary + secondary + rest


ENGINE_REGISTRY = _get_engine_registry()
# 兼容旧接口：暴露 (name, fn, has_key) 三元组
ENGINE_REGISTRY_COMPAT = [(n, f, k) for n, f, k, _ in ENGINE_REGISTRY]


def run_engine(engine_name: str, keyword: str, days, fetch_limit=None) -> list:
    """执行单个引擎"""
    for name, fn, _, _ in ENGINE_REGISTRY:
        if name == engine_name:
            return fn(keyword, days, fetch_limit)
    return []


# ── 引擎熔断：连接错误才熔断，空结果不熔断 ──
_dead_engines: set = set()


def run_with_fallback(keyword: str, days, fetch_limit=None, primary_only: bool = False) -> list:
    """
    按优先级依次尝试引擎（primary → secondary → 其余），第一个成功即停。
    只有引擎函数抛异常（连接错误）才熔断，返回空列表不算失败。
    
    当 primary_only=True 时，只尝试 primary 引擎，不 fallback。
    用于 site: 数据源限定搜索（百度/Bing 不支持 site: 精确匹配）。
    """
    for name, fn, has_key, _ in ENGINE_REGISTRY:
        if not has_key() or name in _dead_engines:
            continue
        try:
            results = fn(keyword, days, fetch_limit)
            if results:
                return results
        except Exception:
            _dead_engines.add(name)
        if primary_only:
            # 仅尝试 primary 引擎，不再 fallback
            break
    return []


def run_all_available(keyword: str, days, fetch_limit_per_engine=None) -> list:
    """
    尝试所有可用引擎，合并结果。
    只有引擎函数抛异常才熔断，返回空列表不算失败。
    """
    all_results = []
    for name, fn, has_key, _ in ENGINE_REGISTRY:
        if not has_key() or name in _dead_engines:
            continue
        try:
            results = fn(keyword, days, fetch_limit_per_engine)
            if results:
                all_results.extend(results)
        except Exception:
            _dead_engines.add(name)
    return all_results


def reset_circuit_breaker():
    """重置熔断器"""
    _dead_engines.clear()
    _known_dead.clear()


# ==============================================================================
# 去重 + 排序 + 裁剪
# ==============================================================================
def is_similar(a: str, b: str, threshold=None) -> bool:
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold


def filter_sort_and_trim(all_results, max_total=None, skip_quality_sort=False):
    """对搜索结果去重、排序、裁剪（基于内容质量评分）"""
    grouped = {}
    for r in all_results:
        src = r["source"]
        grouped.setdefault(src, []).append(r)

    final = []
    for source, items in grouped.items():
        if not skip_quality_sort:
            for it in items:
                it["level"] = get_quality_score(it.get("title", ""), it.get("snippet", ""), it.get("url", ""))

        sorted_items = sorted(items, key=lambda x: (-x.get("level", 1), -len(x.get("date", ""))))

        seen = set()
        unique = []
        for it in sorted_items:
            t = it["title"].strip()
            if len(t) < 4:
                continue
            if is_junk(t, it.get("snippet", "")):
                continue
            if not it.get("snippet") or len(it["snippet"].strip()) < 20:
                continue
            if any(is_similar(t, x) for x in seen):
                continue
            seen.add(t)
            unique.append(it)

        keep_num = KEEP_COUNT.get(source, 3)
        if max_total and keep_num > max_total:
            keep_num = max_total
        final.extend(unique[:keep_num])

    if not skip_quality_sort:
        final = sorted(final, key=lambda x: (-x.get("level", 1), -len(x.get("date", ""))))

    if max_total:
        final = final[:max_total]

    return final


# ==============================================================================
# 批量搜索模式
# ==============================================================================
def run_batch_search(
    keyword_groups: List[Dict[str, Any]],
    global_max_total: Optional[int] = None,
    fresh: bool = False,
    max_workers: int = 8,
) -> Dict[str, Any]:
    """
    批量搜索：关键词组 × 数据源组，并发搜索后汇总。
    使用 ThreadPoolExecutor 并发执行搜索任务，显著减少等待时间。
    每个搜索任务按主备引擎优先级（run_with_fallback），第一个成功即停。
    """
    days = 7 if fresh else None
    group_results = []
    all_group_tasks = []  # (group_index, query_label, future)

    # Phase 1: 构建所有搜索任务
    for gi, group in enumerate(keyword_groups):
        keywords = group.get("keywords", [])
        sources  = group.get("sources", [])
        max_per_src = group.get("max_per_source")
        max_per_kw  = group.get("max_per_keyword")
        group_label = group.get("group_label", f"group_{gi}")
        if not keywords:
            group_results.append({
                "label": group_label, "keywords": keywords,
                "sources": sources if sources else None,
                "results": [], "result_count": 0,
            })
            continue

        per_engine = max_per_src or max_per_kw
        tasks = []
        for kw in keywords:
            if sources:
                for src_domain in sources:
                    site_query = f"{kw} site:{src_domain}"
                    tasks.append((site_query, per_engine, True))  # primary_only=True
            else:
                tasks.append((kw, per_engine, False))

        # 初始化 group 结果槽位
        group_results.append({
            "label": group_label, "keywords": keywords,
            "sources": sources if sources else None,
            "_tasks": tasks, "_raw": [],  # 临时字段
        })

    # Phase 2: 并发执行所有搜索任务
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for gi, gr in enumerate(group_results):
            for query, per_engine, primary_only in gr.pop("_tasks", []):
                f = pool.submit(run_with_fallback, query, days, per_engine, primary_only)
                futures[f] = gi

        for f in as_completed(futures):
            gi = futures[f]
            try:
                results = f.result()
                if results:
                    group_results[gi]["_raw"].extend(results)
            except Exception:
                pass

    # Phase 3: 每个组去重 + 裁剪
    all_results = []
    for gi, gr in enumerate(group_results):
        has_sources = bool(gr.get("sources"))
        gr["results"] = filter_sort_and_trim(
            gr.pop("_raw", []),
            max_total=gr.get("max_per_keyword") if has_sources else global_max_total,
            skip_quality_sort=has_sources,
        ) if has_sources else filter_sort_and_trim(
            gr.pop("_raw", []),
            max_total=global_max_total,
            skip_quality_sort=False,
        )
        gr["result_count"] = len(gr["results"])
        all_results.extend(gr["results"])

    # Phase 4: 全局去重
    seen_titles = set()
    deduped = []
    for r in all_results:
        t = r.get("title", "").strip()
        if not t or t in seen_titles:
            continue
        if any(is_similar(t, x) for x in seen_titles):
            continue
        seen_titles.add(t)
        deduped.append(r)

    if global_max_total:
        deduped = deduped[:global_max_total]

    return {
        "summary": {
            "total_results": len(deduped),
            "groups_searched": len(group_results),
            "keywords_searched": sum(len(g["keywords"]) for g in keyword_groups if g.get("keywords")),
        },
        "groups": group_results,
        "all_results": deduped,
    }


# ==============================================================================
# 输出渲染
# ==============================================================================
_ENGINE_LABELS = {
    "SerpBase": "SerpBase(G)", "BingAPI": "BingAPI",
    "Tavily": "Tavily", "ProSearch": "ProSearch",
    "Baidu": "百度", "BingIntl": "Bing(Intl)",
    "Google": "Google",
    "BaiduSearch": "百度", "Bing": "Bing", "360so": "360", "HTMLDoc": "fallback",
}


def render_all(results, keyword):
    by_src = {}
    for r in results:
        by_src.setdefault(r["source"], []).append(r)

    lines = [f"  [{keyword}]"]
    for src, lst in by_src.items():
        label = _ENGINE_LABELS.get(src, src)
        lines.append(f"    [{label}] {len(lst)} results")
        for i, r in enumerate(lst, 1):
            date = f" ({r['date']})" if r.get("date") else ""
            lv = f" L{r.get('level', 1)}"
            lines.append(f"      {i}. {r['title']}{date}{lv}")
            if r.get("snippet"):
                lines.append(f"         {r['snippet'][:120]}...")
            if r.get("url"):
                lines.append(f"         -> {r['url']}")
        lines.append("")
    return "\n".join(lines)


def render_batch(batch_result: dict) -> str:
    lines = ["=== BATCH SEARCH RESULT ==="]
    s = batch_result["summary"]
    lines.append(f"Total: {s['total_results']} results "
                 f"from {s['keywords_searched']} keywords "
                 f"in {s['groups_searched']} groups")
    lines.append("")
    for g in batch_result.get("groups", []):
        label = g.get("label", "")
        sources = g.get("sources")
        src_info = f" (sources: {', '.join(sources)})" if sources else ""
        lines.append(f"--- {label}{src_info} [{g['result_count']} results] ---")
        lines.append(f"    keywords: {', '.join(g['keywords'])}")
        lines.append("")
        for i, r in enumerate(g["results"], 1):
            date = f" ({r['date']})" if r.get("date") else ""
            lv = f" L{r.get('level', 1)}"
            src = _ENGINE_LABELS.get(r["source"], r["source"])
            lines.append(f"    {i}. [{src}] {r['title']}{date}{lv}")
            if r.get("snippet"):
                lines.append(f"       {r['snippet'][:100]}...")
        lines.append("")
    return "\n".join(lines)


# ==============================================================================
# 主入口（命令行）
# ==============================================================================
def main():
    global LIMIT, FRESH
    args = sys.argv[1:]
    for i, arg in enumerate(args[:]):
        if arg == "fresh":
            FRESH = True
            args.pop(i)
        elif arg == "--limit" and i + 1 < len(args):
            try:
                LIMIT = int(args.pop(i + 1))
                args.pop(i)
            except:
                pass

    keyword = " ".join(args) if args else "A股 热点"
    days = 7 if FRESH else None

    # 展示引擎状态
    available = [name for name, _, has_key, _ in ENGINE_REGISTRY if has_key()]
    print(f"  主引擎: {PRIMARY_ENGINE} | 备引擎: {SECONDARY_ENGINE}")
    print(f"  可用引擎: {', '.join(available)}")

    all_results = run_with_fallback(keyword, days)
    final = filter_sort_and_trim(all_results)
    print(render_all(final, keyword))


if __name__ == "__main__":
    main()
