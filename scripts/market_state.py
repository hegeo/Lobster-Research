import asyncio
import random
import os
import io
import re
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# 使用UTF8重新包装 stdout 为 UTF-8，解决Windows编码问题
sys.stdout = io.TextIOWrapper(
    sys.stdout.buffer,
    encoding='utf-8',
    errors='replace'
)

# ===================== 【核心配置区】所有参数在这里修改 =====================
# 1. 抓取配置
URLS = [
    "https://gu.sina.cn/#/index/index",
]
MIN_DELAY = 2          # 抓取间隔最小时间（秒）
MAX_DELAY = 5          # 抓取间隔最大时间（秒）
SAVE_FILE_ENCODING = "utf-8"  # 文件保存编码
PAGE_CHARSET = "UTF-8"        # 网页charset设置

# 2. 清理开关（抓取阶段）
REMOVE_EXTERNAL_JS = True    # 移除外部JS
REMOVE_EXTERNAL_CSS = True   # 移除外部CSS

# 3. 输出配置
OUTPUT_FOLDER = "stock_data"  # 输出目录
EXPORT_PLAIN_TXT = False       # 是否输出纯文本TXT
EXPORT_CLEANED_HTML = False    # 是否输出清理后的HTML
FILENAME_PREFIX = "market_state"  # 文件名前缀

# 4. 控制台输出配置（新增！）
CONSOLE_OUTPUT = True         # 是否在CMD/终端直接输出内容
CONSOLE_OUTPUT_TYPE = "html"   # 控制台输出类型：txt = 纯文本 | html = 清理后的HTML源码

# 5. HTML清洗配置
# 要直接删除的标签
REMOVE_TAGS = [
    "script", "style", "iframe", "noscript",
    "meta", "link", "svg", "path", "canvas",
    "nav", "footer", "aside", "header","foot","top","hq-nav"
]

# 要直接删除的Class
REMOVE_CLASSES = [
    "loading", "ad", "advertisement", "sidebar","menu", "footer-wrap", "header-nav", "more","foot","top","position",
    "hq-nav","position: relative;","da-iut","hq-stock-longbtn","s-55a5528c72fe53b2","__callup_bottom_new","snp-container","snp-bottom-bar","s-55b65e3c9db1ba12","hq-header-routes","hq-nav-list","hq-nav-item",
    "SFA-continue-pop","hq-stock-indextitle","hq-stock-flex"
]

# 要直接删除的ID
REMOVE_IDS = ["footer","foot","top", "header", "sidebar", "ad",
"_hqHeader_","-fin-header","_menulist"]

# 关键词同组删除配置
GROUP_DELETE_WORDS = ["新闻动态","网站导航"]  # 子标签包含这些词则删除父级
GROUP_DELETE_LEVEL = 1  # 向上删除级数：1=直接父级，2=爷爷级

# 链接清洗配置
CLEAN_ALL_HREF_LINKS = False  # 所有链接转为纯文本
KEEP_SHTML_LINKS = True       # 保留shtml链接
DELETE_LINKS_WITH_KEYWORDS = True  # 删除含关键词的链接
DELETE_HIDDEN_TAGS = True     # 删除隐藏标签

# 文本过滤关键词
DELETE_TEXT_KEYWORDS = ["加载中...", "关闭", "广告", "推广", "跳转", "下载", "点击查看","返回"]
DELETE_LINK_TEXT_KEYWORDS = ["广告", "推广", "跳转", "下载", "关闭","返回"]

# 属性过滤配置
FILTER_STYLE_ATTR = True   # 过滤style属性
FILTER_CLASS_ATTR = True   # 过滤class属性
FILTER_ID_ATTR = True      # 过滤id属性
FILTER_OTHER_ATTRS = True  # 过滤其他属性（target/onclick等）
# ============================================================================

class HtmlCleaner:
    def __init__(self):
        self.remove_tags = REMOVE_TAGS
        self.remove_classes = REMOVE_CLASSES
        self.remove_ids = REMOVE_IDS
        self.group_delete_words = GROUP_DELETE_WORDS
        self.group_delete_level = GROUP_DELETE_LEVEL
        self.delete_text_keywords = DELETE_TEXT_KEYWORDS
        self.delete_link_keywords = DELETE_LINK_TEXT_KEYWORDS

    def clean_html(self, soup: BeautifulSoup) -> BeautifulSoup:
        # 1. 基础无用标签删除
        for tag in self.remove_tags:
            for t in soup.find_all(tag):
                t.decompose()

        for cls in self.remove_classes:
            for t in soup.find_all(class_=cls):
                t.decompose()

        for id_val in self.remove_ids:
            for t in soup.find_all(id=id_val):
                t.decompose()

        # 2. 关键词同组删除：子含关键词 → 删整个父级块
        for kw in self.group_delete_words:
            for text_node in soup.find_all(string=lambda s: s and kw in s.strip()):
                try:
                    target = text_node
                    for _ in range(self.group_delete_level):
                        if target.parent:
                            target = target.parent
                    target.decompose()
                except:
                    continue

        # 3. 删除隐藏标签
        if DELETE_HIDDEN_TAGS:
            for t in soup.find_all(style=lambda s: s and 'display:none' in s):
                try:
                    t.decompose()
                except:
                    pass

        # 4. 文本关键词删除
        for kw in self.delete_text_keywords:
            for text_tag in soup.find_all(string=lambda s: s and kw in s.strip()):
                try:
                    parent = text_tag.find_parent('tr') or text_tag.parent
                    if parent:
                        parent.decompose()
                except:
                    continue

        # 5. 链接关键词删除
        for a in soup.find_all('a'):
            href = str(a.get('href', '')).lower()
            text = a.get_text(strip=True).lower()

            # 保留 shtml 链接
            if KEEP_SHTML_LINKS and '.shtml' in href:
                continue

            # 删除含关键词链接
            if DELETE_LINKS_WITH_KEYWORDS:
                for kw in self.delete_link_keywords:
                    if kw in text:
                        try:
                            a.decompose()
                        except:
                            pass
                        break

        # 6. 所有残留链接 → 变成纯文本
        if CLEAN_ALL_HREF_LINKS:
            for a in soup.find_all('a'):
                try:
                    a.unwrap()
                except:
                    pass

        # 7. 清理属性
        for tag in soup.find_all():
            attrs = list(tag.attrs.keys())
            for attr in attrs:
                if (FILTER_STYLE_ATTR and attr == 'style') or \
                   (FILTER_CLASS_ATTR and attr == 'class') or \
                   (FILTER_ID_ATTR and attr == 'id') or \
                   (FILTER_OTHER_ATTRS and attr in ['target', 'onclick', 'onload', 'rel', 'title']):
                    try:
                        del tag[attr]
                    except:
                        pass

        # 8. 删除空标签
        for tag in soup.find_all():
            if not tag.get_text(strip=True) and tag.name not in ['br', 'p', 'div']:
                try:
                    tag.decompose()
                except:
                    pass

        return soup

    def process(self, html_content: str):
        soup = BeautifulSoup(html_content, 'html.parser')
        cleaned = self.clean_html(soup)
        return cleaned, cleaned.prettify(), cleaned.get_text(separator="\n", strip=True)

async def save_and_clean_page(page, url, index):
    try:
        # 创建输出目录
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        
        print(f"\n[{index}] 加载: {url}")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        
        # 获取页面HTML
        html = await page.content()

        # 强制统一页面 charset
        html = re.sub(r'charset=[a-zA-Z0-9_-]+', f'charset={PAGE_CHARSET}', html, flags=re.IGNORECASE)

        # 清理外部 JS
        if REMOVE_EXTERNAL_JS:
            html = re.sub(r'<script\s+src=["\'].*?["\'].*?</script>', '', html, flags=re.DOTALL|re.I)
            html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL|re.I)

        # 清理外部 CSS
        if REMOVE_EXTERNAL_CSS:
            html = re.sub(r'<link\s+rel=["\']stylesheet["\'].*?>', '', html, flags=re.I)
            html = re.sub(r'@import\s+url\(.*?\);', '', html, flags=re.I)

        # 初始化清洗器并处理HTML
        cleaner = HtmlCleaner()
        soup, cleaned_html, cleaned_txt = cleaner.process(html)

        # 生成文件名（包含日期时间）
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{FILENAME_PREFIX}_{ts}"
        
        # 输出清理后的HTML
        if EXPORT_CLEANED_HTML:
            html_filename = f"{OUTPUT_FOLDER}/{base_filename}.html"
            with open(html_filename, "w", encoding=SAVE_FILE_ENCODING, errors="ignore") as f:
                f.write(cleaned_html)
            print(f"✅ HTML已保存: {html_filename}")

        # 输出纯文本TXT
        if EXPORT_PLAIN_TXT:
            txt_filename = f"{OUTPUT_FOLDER}/{base_filename}.txt"
            with open(txt_filename, "w", encoding=SAVE_FILE_ENCODING, errors="ignore") as f:
                f.write(cleaned_txt)
            print(f"✅ TXT已保存: {txt_filename}")

        # ===================== 【新增】控制台直接输出 =====================
        if CONSOLE_OUTPUT:
            print(f"\n{'='*50} 控制台输出内容 {'='*50}")
            if CONSOLE_OUTPUT_TYPE.lower() == "html":
                print(cleaned_html)  # 输出清理后的HTML源码
            else:
                print(cleaned_txt)   # 默认输出纯文本
            print(f"{'='*120}\n")
        # =================================================================

    except Exception as e:
        print(f"❌ 失败：{str(e)}")

async def main():
    random.shuffle(URLS)
    print(f"🚀 开始抓取 {len(URLS)} 个页面（随机顺序）")
    print(f"📁 输出目录：{OUTPUT_FOLDER}")
    print(f"📋 输出格式：{'HTML' if EXPORT_CLEANED_HTML else ''}{', TXT' if EXPORT_PLAIN_TXT else ''}")
    print(f"🖥️  控制台输出：{'开启' if CONSOLE_OUTPUT else '关闭'} | 类型：{CONSOLE_OUTPUT_TYPE.upper()}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = await context.new_page()

        for i, url in enumerate(URLS, 1):
            await save_and_clean_page(page, url, i)
            wait = random.uniform(MIN_DELAY, MAX_DELAY)
            print(f"⏳ 等待 {wait:.1f}s")
            await asyncio.sleep(wait)

        await browser.close()
    print(f"\n🎉 全部完成！输出目录：{OUTPUT_FOLDER}")

if __name__ == "__main__":
    asyncio.run(main())