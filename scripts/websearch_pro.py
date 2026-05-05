# -*- coding: utf-8 -*-
"""
龙虾调研助手 - 多引擎联网搜索(质量分级版) 
├─ 配置驱动：从 config/settings.json 读取 API keys 和引擎参数
├─ 新增：批量搜索模式（关键词组 × 数据源组，循环搜索后汇总）
├─ 新增：每关键词/每数据源独立配置最大查找数量
├─ 新增：指定数据源时跳过质量分级约束
├─ 兼容：单关键词命令行模式不变
├─ Tavily Search API（优先）
├─ 主引擎：ProSearch（通过本地 Auth Gateway）
├─ 中文引擎：百度搜索（baidusearch 库）
├─ 国际引擎：Bing Search
├─ 备用引擎：360搜索（so.com）
├─ 兜底方案：直接访问目标URL提取内容
├─ 权重等级：5 > 4 > 3 > 2 > 1（仅排序，不过滤）
├─ 各引擎独立：抓取数 → 排序 → 保留数，标题智能去重
默认 UTF-8 打印，彻底解决 Windows GBK 问题

用法（命令行-兼容旧模式）:
  python websearch_pro.py "关键词"                    # 使用配置的主/次引擎
  python websearch_pro.py "关键词" fresh               # 最近7天
  python websearch_pro.py "关键词" tavily              # 仅Tavily
  python websearch_pro.py "关键词" --limit 10         # 调整结果数量

用法（API调用-批量模式）:
  from scripts.websearch_pro import run_batch_search
  # 关键词组搜索
  results = run_batch_search(
      keyword_groups=[{"keywords": ["A股 行情", "北向资金"], "max_per_keyword": 8}]
  )
  # 关键词组 × 数据源组 搜索
  results = run_batch_search(
      keyword_groups=[
          {"keywords": ["东方财富 行情"], "sources": ["eastmoney"], "max_per_keyword": 10},
          {"keywords": ["同花顺 行情"], "sources": ["10jqka"], "max_per_keyword": 8},
      ]
  )
"""

import sys, os, time, json, re, math
from difflib import SequenceMatcher
from typing import List, Dict, Optional, Any

sys.stdout.reconfigure(encoding="utf-8")

try:
    import requests
except ImportError:
    raise ImportError("请先安装依赖：pip install requests python-baidusearch")

# ==============================================================================
# 配置加载（从 config/settings.json）
# ==============================================================================
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SETTINGS_PATH = os.path.join(_PROJECT_ROOT, "config", "settings.json")


def _load_settings() -> dict:
    """加载 settings.json，不存在则返回空 dict"""
    if os.path.exists(_SETTINGS_PATH):
        with open(_SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


_settings = _load_settings()
_ws = _settings.get("websearch_pro", {})

# APIs
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "") or _ws.get("apis", {}).get("tavily_api_key", "")
TAVILY_API_BASE = _ws.get("apis", {}).get("tavily_api_base", "https://api.tavily.com/search")
PORT = os.environ.get("AUTH_GATEWAY_PORT", "") or _ws.get("apis", {}).get("auth_gateway_port", "19000")
PROSEARCH_BASE = _ws.get("apis", {}).get("auth_gateway_base", f"http://localhost:{PORT}/proxy/prosearch/search")

# Engines
PRIMARY_ENGINE = os.environ.get("PRIMARY_ENGINE", "") or _ws.get("engines", {}).get("primary", "360")
SECONDARY_ENGINE = os.environ.get("SECONDARY_ENGINE", "") or _ws.get("engines", {}).get("secondary", "baidu")
ENABLE_ALL_ENGINES = os.environ.get("ENABLE_ALL_ENGINES", "").lower() == "true" or _ws.get("engines", {}).get("enable_all", False)

# Fetch/Keep counts
_fetch_cfg = _ws.get("engines", {}).get("fetch_count", {})
_keep_cfg = _ws.get("engines", {}).get("keep_count", {})
ENGINE_FETCH_COUNT = {
    "Tavily": _fetch_cfg.get("tavily", 5),
    "ProSearch": _fetch_cfg.get("prosearch", 10),
    "Bing": _fetch_cfg.get("bing", 15),
    "360so": _fetch_cfg.get("360", 12),
    "BaiduSearch": _fetch_cfg.get("baidu", 12),
    "HTMLDoc": _fetch_cfg.get("htmldoc", 2),
}
ENGINE_KEEP_COUNT = {
    "Tavily": _keep_cfg.get("tavily", 5),
    "ProSearch": _keep_cfg.get("prosearch", 5),
    "Bing": _keep_cfg.get("bing", 5),
    "360so": _keep_cfg.get("360", 5),
    "BaiduSearch": _keep_cfg.get("baidu", 5),
    "HTMLDoc": _keep_cfg.get("htmldoc", 2),
}

# Quality levels
_lvl = _ws.get("quality_levels", {})
LEVEL_5 = _lvl.get("level_5", [
    "gov.cn", "xinhuanet", "people", "cri.cn", "wikipedia", "baike",
    "cninfo.com.cn", "qichacha", "aiqicha", "eastmoney",
])
LEVEL_4 = _lvl.get("level_4", [
    "caixin", "stcn", "36kr", "cyzone", "oschina", "geekpark",
    "tmtpost", "ithome", "huxiu", "huanqiu", "linkshop", "sina",
])
LEVEL_3 = _lvl.get("level_3", ["qq", "163.com", "sohu", "ifeng", "zhihu"])
LEVEL_2 = _lvl.get("level_2", ["toutiao", "baijiahao", "tiktok", "douyin", "dykt", "bilibili.com"])

# Defaults
_defaults = _ws.get("defaults", {})
DEFAULT_LIMIT = _defaults.get("global_max_results", 16)
DEFAULT_TIMEOUT = _defaults.get("request_timeout", 12)
SIMILARITY_THRESHOLD = _defaults.get("similarity_threshold", 0.6)

TAVILY_ENABLED = bool(TAVILY_API_KEY)
VALID_ENGINES = ["tavily", "bing", "baidu", "360", "prosearch"]

# CLI mode vars
LIMIT = DEFAULT_LIMIT
FRESH = False
ENGINE = "all" if ENABLE_ALL_ENGINES else "custom"


# ==============================================================================
# 4. 质量打分（仅排序用）
# ==============================================================================
def get_quality_score(url: str) -> int:
    if not url:
        return 1
    url = url.lower()
    for kw in LEVEL_5:
        if kw in url:
            return 5
    for kw in LEVEL_4:
        if kw in url:
            return 4
    for kw in LEVEL_3:
        if kw in url:
            return 3
    for kw in LEVEL_2:
        if kw in url:
            return 2
    return 1


# ==============================================================================
# 工具函数
# ==============================================================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/120.0.0",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch(url: str, timeout=DEFAULT_TIMEOUT):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.encoding = r.apparent_encoding or "utf-8"
        return r.text
    except Exception as e:
        return None


def resolve_360_redirect(url: str) -> str:
    if "so.com/link?m=" not in url:
        return url
    try:
        r = requests.head(url, headers=HEADERS, timeout=8, allow_redirects=True)
        return r.url
    except:
        return url


def clean(html: str) -> str:
    if not html:
        return ""
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
# 搜索实现（支持自定义 fetch_limit）
# ==============================================================================
def tavily_search(keyword: str, days_n=None, fetch_limit=None):
    if not TAVILY_ENABLED:
        return []
    if fetch_limit is None:
        fetch_limit = ENGINE_FETCH_COUNT["Tavily"]
    results = []
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
    try:
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


def prosearch(keyword: str, days_n=None, fetch_limit=None):
    if fetch_limit is None:
        fetch_limit = ENGINE_FETCH_COUNT["ProSearch"]
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
        results = [{
            "title": d["title"], "url": d["url"],
            "snippet": d.get("passage", d.get("snippet", ""))[:300],
            "date": d.get("date", "")[:10] if d.get("date") else "",
            "source": "ProSearch",
        } for d in res.get("data", {}).get("docs", [])[:fetch_limit]]
    except:
        results = []
    return results


def baidu_search_plus(keyword: str, fetch_limit=None):
    if fetch_limit is None:
        fetch_limit = ENGINE_FETCH_COUNT["BaiduSearch"]
    try:
        from baidusearch.baidusearch import search
    except:
        return []
    res = []
    for item in search(keyword=keyword, num_results=fetch_limit)[:fetch_limit]:
        res.append({
            "title": clean(item["title"]),
            "url": item["url"],
            "snippet": clean(item.get("abstract", ""))[:200],
            "date": parse_date(str(item)),
            "source": "BaiduSearch",
        })
    return res


def bing_search(keyword: str, limit=None):
    if limit is None:
        limit = ENGINE_FETCH_COUNT["Bing"]
    results = []
    params = {"q": keyword, "mkt": "zh-CN", "setlang": "zh-CN", "ensearch": "0"}
    url = f"https://www.bing.com/search?{requests.compat.urlencode(params)}"
    html = fetch(url)
    if not html:
        return []

    results_blocks = re.findall(r'<li class="b_algo".*?</li>', html, re.DOTALL)
    seen_urls = set()

    for block in results_blocks[:limit]:
        title_match = re.search(r'data-heading="([^"]+)"', block)
        if not title_match:
            title_match = re.search(r'<h2.*?<a.*?>(.*?)</a>', block, re.DOTALL)
        title = clean(title_match.group(1)).strip() if title_match else ""

        url_match = re.search(r'href="(https?://.*?)"', block)
        url_val = ""
        if url_match:
            raw_url = url_match.group(1)
            if "bing.com" not in raw_url and "javascript:" not in raw_url:
                url_val = raw_url.split("#")[0].split("&")[0]

        snippet_match = re.search(r'class="b_paractext.*?">(.*?)</p>', block, re.DOTALL)
        snippet = clean(snippet_match.group(1))[:200] if snippet_match else ""
        date_str = parse_date(block)

        if not title or len(title) < 3:
            continue

        url_key = url_val[:80] if url_val else title[:30]
        if url_key in seen_urls:
            continue
        seen_urls.add(url_key)

        results.append({
            "title": title, "url": url_val,
            "snippet": snippet, "date": date_str, "source": "Bing",
        })
    return results


def so360_search(keyword: str, fetch_limit=None):
    if fetch_limit is None:
        fetch_limit = ENGINE_FETCH_COUNT["360so"]
    res = []
    u = f"https://www.so.com/s?q={requests.utils.quote(keyword)}&rn={fetch_limit}"
    html = fetch(u)
    if not html:
        return []

    for m in re.finditer(r'res-list', html):
        b = html[m.start():m.start() + 2000]
        am = re.search(r'<h3.*?<a href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
        dm = re.search(r'res-desc.*?>(.*?)</p>', b, re.S)
        if not am:
            continue
        href, title = am.groups()
        real_url = resolve_360_redirect(href)
        title = clean(title)
        snippet = clean(dm.group(1) if dm else "")[:200]

        res.append({
            "title": title, "url": real_url,
            "snippet": snippet, "date": parse_date(b), "source": "360so",
        })
        if len(res) >= fetch_limit:
            break
    return res


def fallback_html_search(keyword: str, limit=2):
    res = []
    for prefix in ["https://www.baidu.com/s?wd=", "https://www.bing.com/search?q="]:
        txt = clean(fetch(prefix + requests.utils.quote(keyword), timeout=8))
        res.append({
            "title": f"fallback_{keyword[:10]}",
            "url": prefix,
            "snippet": txt[:400],
            "date": "",
            "source": "HTMLDoc",
        })
        if len(res) >= limit:
            break
    return res


# ==============================================================================
# 引擎执行
# ==============================================================================
engine_exec_map = {
    "tavily": lambda kw, days, fl: tavily_search(kw, days, fl),
    "prosearch": lambda kw, days, fl: prosearch(kw, days, fl),
    "baidu": lambda kw, days, fl: baidu_search_plus(kw, fl),
    "bing": lambda kw, days, fl: bing_search(kw, fl),
    "360": lambda kw, days, fl: so360_search(kw, fl),
}


def run_engine(engine_name, keyword, days, fetch_limit=None):
    """执行单个引擎搜索"""
    if engine_name not in engine_exec_map:
        return []
    return engine_exec_map[engine_name](keyword, days, fetch_limit)


def run_all_engines(keyword, days, fetch_limit_per_engine=None):
    """
    使用配置中的引擎组合搜索一个关键词。
    fetch_limit_per_engine: 如果指定，每个引擎最多抓取这么多条。
    """
    all_results = []
    if ENGINE in VALID_ENGINES:
        all_results = run_engine(ENGINE, keyword, days, fetch_limit_per_engine)
    elif ENGINE == "all":
        if TAVILY_ENABLED:
            all_results += run_engine("tavily", keyword, days, fetch_limit_per_engine)
        all_results += run_engine("prosearch", keyword, days, fetch_limit_per_engine)
        all_results += run_engine("bing", keyword, days, fetch_limit_per_engine)
        all_results += run_engine("360", keyword, days, fetch_limit_per_engine)
        all_results += run_engine("baidu", keyword, days, fetch_limit_per_engine)
    else:
        all_results += run_engine(PRIMARY_ENGINE, keyword, days, fetch_limit_per_engine)
        if SECONDARY_ENGINE in VALID_ENGINES and SECONDARY_ENGINE != PRIMARY_ENGINE:
            all_results += run_engine(SECONDARY_ENGINE, keyword, days, fetch_limit_per_engine)

    if not all_results:
        all_results = fallback_html_search(keyword)

    return all_results


# ==============================================================================
# 去重 + 排序 + 裁剪
# ==============================================================================
def is_similar(a: str, b: str, threshold=None) -> bool:
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold


def filter_sort_and_trim(all_results, max_total=None, skip_quality_sort=False):
    """
    对搜索结果去重、排序、裁剪。
    skip_quality_sort: True 时跳过质量分级（用于指定数据源的场景）
    max_total: 最终最多保留多少条结果
    """
    grouped = {}
    for r in all_results:
        src = r["source"]
        grouped.setdefault(src, []).append(r)

    final = []
    for source, items in grouped.items():
        if not skip_quality_sort:
            for it in items:
                it["level"] = get_quality_score(it["url"])

        sorted_items = sorted(items, key=lambda x: (-x.get("level", 1), -len(x.get("date", ""))))

        seen = set()
        unique = []
        for it in sorted_items:
            t = it["title"].strip()
            if len(t) < 4:
                continue
            if any(is_similar(t, x) for x in seen):
                continue
            seen.add(t)
            unique.append(it)

        keep_num = ENGINE_KEEP_COUNT.get(source, 3)
        if max_total and keep_num > max_total:
            keep_num = max_total
        final.extend(unique[:keep_num])

    if not skip_quality_sort:
        final = sorted(final, key=lambda x: (-x.get("level", 1), -len(x.get("date", ""))))

    if max_total:
        final = final[:max_total]

    return final


# ==============================================================================
# 批量搜索模式（核心新功能）
# ==============================================================================
def run_batch_search(
    keyword_groups: List[Dict[str, Any]],
    global_max_total: Optional[int] = None,
    fresh: bool = False,
) -> Dict[str, Any]:
    """
    批量搜索：关键词组 × 数据源组，循环搜索后汇总。

    参数:
        keyword_groups: 关键词组列表，每组是一个 dict:
            - keywords: List[str] — 关键词列表（必填）
            - sources: List[str] — 指定数据源域名（可选，如 ["eastmoney", "cninfo.com.cn"]）
            - max_per_keyword: int — 每个关键词最大结果数（可选，各引擎平分）
            - max_per_source: int — 每个数据源最大结果数（可选，有 sources 时生效）
            - group_label: str — 组标签（可选，用于结果分类）
        global_max_total: 全局最大结果总数（可选）
        fresh: 是否只搜最近7天

    返回:
        {
            "summary": {"total_results": N, "groups_searched": N, "keywords_searched": N},
            "groups": [
                {
                    "label": "组标签",
                    "keywords": ["关键词1", "关键词2"],
                    "sources": ["数据源1"],
                    "results": [{...}, ...]
                },
                ...
            ],
            "all_results": [{...}, ...],  # 全部去重汇总
        }
    """
    days = 7 if fresh else None
    all_results = []
    group_results = []

    for gi, group in enumerate(keyword_groups):
        keywords = group.get("keywords", [])
        sources = group.get("sources", [])
        max_per_kw = group.get("max_per_keyword")
        max_per_src = group.get("max_per_source")
        group_label = group.get("group_label", f"group_{gi}")

        if not keywords:
            continue

        group_all = []

        for kw in keywords:
            if sources:
                # ── 有指定数据源：每个关键词 × 每个数据源分别搜索 ──
                for src_domain in sources:
                    # 构造 site: 搜索语法
                    site_query = f"{kw} site:{src_domain}"

                    # 计算每个引擎的 fetch_limit
                    if max_per_src:
                        # max_per_src 是总限制，平分给各引擎
                        # 指定数据源时只启用 bing + 360 + baidu（三个通用引擎）
                        active_engines = ["bing", "360", "baidu"]
                        if TAVILY_ENABLED:
                            active_engines.insert(0, "tavily")
                        per_engine = math.ceil(max_per_src / len(active_engines))
                    elif max_per_kw:
                        active_engines = ["bing", "360", "baidu"]
                        if TAVILY_ENABLED:
                            active_engines.insert(0, "tavily")
                        per_engine = math.ceil(max_per_kw / len(active_engines))
                    else:
                        per_engine = None  # 用默认值

                    for eng_name in active_engines:
                        raw = run_engine(eng_name, site_query, days, per_engine)
                        group_all.extend(raw)
            else:
                # ── 无指定数据源：用标准引擎组合搜索 ──
                if max_per_kw:
                    active_engines = []
                    if TAVILY_ENABLED:
                        active_engines.append("tavily")
                    active_engines.extend(["prosearch", "bing", "360", "baidu"])
                    per_engine = math.ceil(max_per_kw / len(active_engines))
                    for eng_name in active_engines:
                        raw = run_engine(eng_name, kw, days, per_engine)
                        group_all.extend(raw)
                else:
                    raw = run_all_engines(kw, days)
                    group_all.extend(raw)

        # 组内去重排序
        skip_quality = bool(sources)  # 指定了数据源就不做质量分级
        group_final = filter_sort_and_trim(group_all, max_total=max_per_kw or global_max_total,
                                           skip_quality_sort=skip_quality)

        group_results.append({
            "label": group_label,
            "keywords": keywords,
            "sources": sources if sources else None,
            "results": group_final,
            "result_count": len(group_final),
        })
        all_results.extend(group_final)

    # 全局去重汇总
    seen_titles = set()
    deduped = []
    for r in all_results:
        t = r.get("title", "").strip()
        if not t or t in seen_titles:
            continue
        # 也检查相似
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
def render_all(results, keyword):
    by_src = {}
    for r in results:
        by_src.setdefault(r["source"], []).append(r)

    lines = [f"  [{keyword}]"]
    order = ["Tavily", "ProSearch", "Bing", "360so", "BaiduSearch", "HTMLDoc"]
    engine_name_map = {
        "Tavily": "Tavily", "ProSearch": "ProSearch",
        "Bing": "BING", "360so": "360", "BaiduSearch": "百度", "HTMLDoc": "fallback",
    }

    for src in order:
        if src not in by_src:
            continue
        lst = by_src[src]
        engine_show = engine_name_map.get(src, src)
        lines.append(f"    [{engine_show}] {len(lst)} results")

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
    """渲染批量搜索结果为文本"""
    lines = ["=== BATCH SEARCH RESULT ==="]
    lines.append(f"Total: {batch_result['summary']['total_results']} results "
                 f"from {batch_result['summary']['keywords_searched']} keywords "
                 f"in {batch_result['summary']['groups_searched']} groups")
    lines.append("")

    for g in batch_result.get("groups", []):
        label = g.get("label", "")
        sources = g.get("sources")
        src_info = f" (sources: {', '.join(sources)})" if sources else ""
        lines.append(f"--- {label}{src_info} [{g['result_count']} results] ---")
        lines.append(f"    keywords: {', '.join(g['keywords'])}")
        lines.append("")

        by_src = {}
        for r in g["results"]:
            by_src.setdefault(r["source"], []).append(r)

        order = ["Tavily", "ProSearch", "Bing", "360so", "BaiduSearch", "HTMLDoc"]
        engine_name_map = {
            "Tavily": "Tavily", "ProSearch": "ProSearch",
            "Bing": "BING", "360so": "360", "BaiduSearch": "百度", "HTMLDoc": "fallback",
        }

        for src in order:
            if src not in by_src:
                continue
            lst = by_src[src]
            engine_show = engine_name_map.get(src, src)
            lines.append(f"    [{engine_show}] {len(lst)} results")

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


# ==============================================================================
# 主入口（命令行模式 - 兼容旧用法）
# ==============================================================================
def main():
    global LIMIT, FRESH, ENGINE

    args = sys.argv[1:]
    for i, arg in enumerate(args[:]):
        if arg == "fresh":
            FRESH = True
            args.pop(i)
        elif arg in VALID_ENGINES:
            ENGINE = arg
            args.pop(i)
        elif arg == "all":
            ENGINE = "all"
            args.pop(i)
        elif arg == "--limit" and i + 1 < len(args):
            try:
                LIMIT = int(args.pop(i + 1))
                args.pop(i)
            except:
                pass

    keyword = " ".join(args) if args else "A股 热点"
    days = 7 if FRESH else None

    all_results = run_all_engines(keyword, days)
    final = filter_sort_and_trim(all_results)
    print(render_all(final, keyword))


if __name__ == "__main__":
    main()
