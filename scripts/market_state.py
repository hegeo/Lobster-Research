"""
龙虾调研助手 - 大盘整体状况采集
================================
通过 Playwright 抓取新浪行情页，输出清洗后的 rawtext 或 HTML。

用法：
  python scripts/market_state.py                          # 默认输出到 stdout（rawtext）
  python scripts/market_state.py --output path/to.json    # 直接写 JSON 文件
  python scripts/market_state.py --format html            # 输出清洗后 HTML（默认 rawtext）
  python scripts/market_state.py --output x.json --format html  # 组合
"""

import asyncio
import random
import os
import io
import re
import sys
import json
import argparse
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# 清除 NODE_OPTIONS，Playwright 的 Node 不支持 --use-system-ca 等参数
os.environ.pop("NODE_OPTIONS", None)

# 使用UTF8重新包装 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ===================== 【核心配置区】 =====================
URLS = ["https://gu.sina.cn/#/index/index"]
MIN_DELAY = 2
MAX_DELAY = 5
PAGE_CHARSET = "UTF-8"

# HTML 清洗配置
REMOVE_TAGS = [
    "script", "style", "iframe", "noscript", "meta", "link",
    "svg", "path", "canvas", "nav", "footer", "aside", "header",
    "foot", "top", "hq-nav",
]
REMOVE_CLASSES = [
    "loading", "ad", "advertisement", "sidebar", "menu",
    "footer-wrap", "header-nav", "more", "foot", "top", "position",
    "hq-nav", "da-iut", "hq-stock-longbtn", "snp-container",
    "snp-bottom-bar", "hq-header-routes", "hq-nav-list", "hq-nav-item",
    "SFA-continue-pop", "hq-stock-indextitle", "hq-stock-flex",
]
REMOVE_IDS = ["footer", "foot", "top", "header", "sidebar", "ad", "_hqHeader_", "-fin-header", "_menulist"]
GROUP_DELETE_WORDS = ["新闻动态", "网站导航"]
GROUP_DELETE_LEVEL = 1
CLEAN_ALL_HREF_LINKS = False
KEEP_SHTML_LINKS = True
DELETE_LINKS_WITH_KEYWORDS = True
DELETE_HIDDEN_TAGS = True
DELETE_TEXT_KEYWORDS = ["加载中...", "关闭", "广告", "推广", "跳转", "下载", "点击查看", "返回"]
DELETE_LINK_TEXT_KEYWORDS = ["广告", "推广", "跳转", "下载", "关闭", "返回"]
FILTER_STYLE_ATTR = True
FILTER_CLASS_ATTR = True
FILTER_ID_ATTR = True
FILTER_OTHER_ATTRS = True


# ==============================================================================
# HTML 清洗器
# ==============================================================================
class HtmlCleaner:
    def clean_html(self, soup):
        for tag in REMOVE_TAGS:
            for t in soup.find_all(tag):
                t.decompose()
        for cls in REMOVE_CLASSES:
            for t in soup.find_all(class_=cls):
                t.decompose()
        for id_val in REMOVE_IDS:
            for t in soup.find_all(id=id_val):
                t.decompose()
        for kw in GROUP_DELETE_WORDS:
            for text_node in soup.find_all(string=lambda s: s and kw in s.strip()):
                try:
                    target = text_node
                    for _ in range(GROUP_DELETE_LEVEL):
                        if target.parent:
                            target = target.parent
                    target.decompose()
                except:
                    continue
        if DELETE_HIDDEN_TAGS:
            for t in soup.find_all(style=lambda s: s and 'display:none' in s):
                try:
                    t.decompose()
                except:
                    pass
        for kw in DELETE_TEXT_KEYWORDS:
            for text_tag in soup.find_all(string=lambda s: s and kw in s.strip()):
                try:
                    parent = text_tag.find_parent('tr') or text_tag.parent
                    if parent:
                        parent.decompose()
                except:
                    continue
        for a in soup.find_all('a'):
            href = str(a.get('href', '')).lower()
            text = a.get_text(strip=True).lower()
            if KEEP_SHTML_LINKS and '.shtml' in href:
                continue
            if DELETE_LINKS_WITH_KEYWORDS:
                for kw in DELETE_LINK_TEXT_KEYWORDS:
                    if kw in text:
                        try:
                            a.decompose()
                        except:
                            pass
                        break
        if CLEAN_ALL_HREF_LINKS:
            for a in soup.find_all('a'):
                try:
                    a.unwrap()
                except:
                    pass
        for tag in soup.find_all():
            for attr in list(tag.attrs.keys()):
                if attr in ('style', 'class', 'id', 'target', 'onclick', 'onload', 'rel', 'title'):
                    try:
                        del tag[attr]
                    except:
                        pass
        for tag in soup.find_all():
            if not tag.get_text(strip=True) and tag.name not in ('br', 'p', 'div'):
                try:
                    tag.decompose()
                except:
                    pass
        return soup

    def process(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        cleaned = self.clean_html(soup)
        return cleaned, cleaned.prettify(), cleaned.get_text(separator="\n", strip=True)


# ==============================================================================
# 抓取 + 清洗
# ==============================================================================
async def fetch_and_clean(page, url):
    """抓取单个 URL，返回 (cleaned_html, cleaned_text)"""
    await page.goto(url, wait_until="networkidle", timeout=60000)
    await page.wait_for_timeout(2000)
    html = await page.content()

    html = re.sub(r'charset=[a-zA-Z0-9_-]+', f'charset={PAGE_CHARSET}', html, flags=re.IGNORECASE)
    html = re.sub(r'<script\s+src=["\'].*?["\'].*?</script>', '', html, flags=re.DOTALL | re.I)
    html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL | re.I)
    html = re.sub(r'<link\s+rel=["\']stylesheet["\'].*?>', '', html, flags=re.I)
    html = re.sub(r'@import\s+url\(.*?\);', '', html, flags=re.I)

    cleaner = HtmlCleaner()
    soup, cleaned_html, cleaned_text = cleaner.process(html)
    return cleaned_html, cleaned_text


# ==============================================================================
# 主入口
# ==============================================================================
async def main():
    parser = argparse.ArgumentParser(description="大盘整体状况采集")
    parser.add_argument("--output", "-o", default="", help="输出 JSON 文件路径（不指定则打印到 stdout）")
    parser.add_argument("--format", "-f", default="rawtext", choices=["rawtext", "html"],
                        help="输出内容格式：rawtext=纯文本（默认），html=清洗后HTML")
    args = parser.parse_args()

    out_path = args.output
    out_format = args.format

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True,
        )
        page = await context.new_page()

        cleaned_html, cleaned_text = await fetch_and_clean(page, URLS[0])
        await browser.close()

    # 构建 JSON 数据
    data = {
        "_meta": {
            "step": "market_state",
            "fetched_at": datetime.now().isoformat(),
            "run_success": True,
            "source": URLS[0],
        },
        "agent_note": (
            "这是新浪行情页的清理后内容，包含大盘整体状况、板块涨跌、热门股票等信息。"
            "请从中提取：今日大盘情绪、主要板块动态、资金流向信号，整合进报告"
        ),
    }
    if out_format == "html":
        data["raw_html"] = cleaned_html[:20000]
    else:
        data["raw_text"] = cleaned_text[:20000]

    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        # 无 --output 时，直接打印内容到 stdout
        if out_format == "html":
            print(cleaned_html[:20000])
        else:
            print(cleaned_text[:20000])


if __name__ == "__main__":
    asyncio.run(main())
