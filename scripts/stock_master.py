# -*- coding: utf-8 -*-
# ==============================================================================
# 证券之星股票页面下载+清洗一体化工具
# 功能说明：
# 1. 支持一次性下载单个/多个股票代码（英文逗号分隔）
# 2. 自动清洗HTML（删除JS/CSS/广告/无用标签/关键词等）
# 3. 可配置最终输出TXT纯文本或清洗后的HTML
# 4. 模拟人工访问，避免反爬
# ==============================================================================

import sys
import io
# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ======================= 【全局配置区】所有参数在这里修改 =======================
# 1. 下载配置
DOWNLOAD_PAGE_TYPE = "all"  # all/info/corp/dividend/share/finance/main
REQUEST_WAIT_BEFORE = (4, 8)  # 请求前等待秒数范围
REQUEST_INTERVAL = (3, 8)     # 页面间隔等待秒数范围
STOCK_SWITCH_WAIT = (5, 10)   # 股票切换等待秒数范围

# 2. 输出配置
OUTPUT_BASE_DIR = "stock_data"
EXPORT_PLAIN_TXT = True       # 是否输出纯文本TXT
EXPORT_CLEANED_HTML = False    # 是否输出清洗后的HTML

# 3. HTML清洗配置
# 要直接删除的标签
REMOVE_TAGS = [
    "script", "style", "iframe", "noscript",
    "meta", "link", "svg", "path", "canvas",
    "nav", "footer", "aside", "header","foot","top",
]
# 要直接删除的Class
REMOVE_CLASSES = [
    "loading", "ad", "advertisement", "sidebar",
    "menu", "footer-wrap", "header-nav", "more","foot","top","position",
]
# 要直接删除的ID
REMOVE_IDS = ["footer","foot","top", "header", "sidebar", "ad"]
# 关键词同组删除（子元素含关键词则删除整个父级）
GROUP_DELETE_WORDS = ["新闻动态","网站导航"]
GROUP_DELETE_LEVEL = 1  # 向上删除层级：1=父级，2=爷爷级
# 文本关键词过滤
DELETE_TEXT_KEYWORDS = ["加载中...", "证券之星", "关闭", "广告", "推广", "跳转", "下载", "点击查看","返回"]
# 链接文字关键词
DELETE_LINK_TEXT_KEYWORDS = ["广告", "推广", "跳转", "下载", "关闭","返回"]
# 链接清洗
CLEAN_ALL_HREF_LINKS = False
KEEP_SHTML_LINKS = True
DELETE_LINKS_WITH_KEYWORDS = True
DELETE_HIDDEN_TAGS = True
# 属性过滤
FILTER_STYLE_ATTR = True
FILTER_CLASS_ATTR = True
FILTER_ID_ATTR = True
FILTER_OTHER_ATTRS = True
# ==============================================================================

import requests
import urllib3
import chardet
import os
import random
import time
from pathlib import Path
from bs4 import BeautifulSoup
import argparse

# 关闭HTTPS警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()

# 请求头配置
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://stock.quote.stockstar.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ===================== 编码检测 =====================
def detect_encoding(resp):
    try:
        if 'charset' in resp.headers.get('Content-Type', ''):
            return resp.headers['Content-Type'].split('charset=')[-1].strip()
        return chardet.detect(resp.content)['encoding'] or 'utf-8'
    except:
        return 'utf-8'

# ===================== 内容验证 =====================
def validate_page_content(content):
    """宽松验证：只要有内容就保留"""
    if not content or len(content.strip()) < 50:
        return False
    return True

# ===================== 拟人等待 =====================
def human_wait_before_request():
    """请求前拟人等待"""
    load_wait = random.uniform(*REQUEST_WAIT_BEFORE)
    print(f"⏳ 模拟页面加载等待 {load_wait:.1f} 秒")
    time.sleep(load_wait)
    # 额外微小停顿
    mini_wait = random.uniform(0.3, 1.2)
    time.sleep(mini_wait)

# ===================== HTML清洗类 =====================
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
        # 1. 删除指定标签/Class/ID
        for tag in self.remove_tags:
            for t in soup.find_all(tag):
                t.decompose()

        for cls in self.remove_classes:
            for t in soup.find_all(class_=cls):
                t.decompose()

        for id_val in self.remove_ids:
            for t in soup.find_all(id=id_val):
                t.decompose()

        # 2. 关键词同组删除
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

        # 5. 链接清洗
        for a in soup.find_all('a'):
            href = str(a.get('href', '')).lower()
            text = a.get_text(strip=True).lower()

            if KEEP_SHTML_LINKS and '.shtml' in href:
                continue

            if DELETE_LINKS_WITH_KEYWORDS:
                for kw in self.delete_link_keywords:
                    if kw in text:
                        try:
                            a.decompose()
                        except:
                            pass
                        break

        # 6. 链接转纯文本
        if CLEAN_ALL_HREF_LINKS:
            for a in soup.find_all('a'):
                try:
                    a.unwrap()
                except:
                    pass

        # 7. 清理标签属性
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
        cleaned_soup = self.clean_html(soup)
        cleaned_html = cleaned_soup.prettify()
        plain_text = cleaned_soup.get_text(separator="\n", strip=True)
        return cleaned_html, plain_text

# ===================== 下载并保存页面 =====================
def download_and_clean_page(url, stock_code, page_name, cleaner):
    """下载页面并执行清洗"""
    try:
        # 拟人等待
        human_wait_before_request()

        # 发送请求
        session = requests.Session()
        session.headers.update(HEADERS)
        resp = session.get(url, timeout=20, allow_redirects=True, verify=False)
        resp.raise_for_status()

        # 编码处理
        encoding = detect_encoding(resp)
        if encoding.lower() in ['gb2312', 'gbk', 'gb18030']:
            html = resp.content.decode('gbk', errors='ignore')
        else:
            html = resp.content.decode(encoding, errors='ignore')

        # 内容验证
        if not validate_page_content(html):
            print(f"⚠️ {stock_code}_{page_name} 内容为空，跳过")
            return False

        # 清洗HTML
        cleaned_html, plain_text = cleaner.process(html)

        # 创建输出目录
        download_dir = Path(OUTPUT_BASE_DIR) / stock_code
        download_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        base_filename = f"{stock_code}_{page_name}"
        
        if EXPORT_CLEANED_HTML:
            html_path = download_dir / f"{base_filename}_clean.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(cleaned_html)
            print(f"📄 已保存清洗后的HTML：{html_path}")

        if EXPORT_PLAIN_TXT:
            txt_path = download_dir / f"{base_filename}_plain.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(plain_text)
            print(f"📝 已保存纯文本TXT：{txt_path}")

        return True

    except Exception as e:
        print(f"❌ 下载失败 {stock_code}_{page_name}：{str(e)[:50]}")
        return False

# ===================== 处理单个股票 =====================
def process_single_stock(stock_code, cleaner):
    """处理单个股票的所有指定页面"""
    base_url = "https://stock.quote.stockstar.com/"
    page_map = {
        "info":     f"{base_url}info_{stock_code}.shtml",
        "corp":     f"{base_url}corp_{stock_code}.shtml",
        "dividend": f"{base_url}dividend_{stock_code}.shtml",
        "share":    f"{base_url}share_{stock_code}.shtml",
        "finance":  f"{base_url}finance_{stock_code}.shtml",
        "main":     f"{base_url}{stock_code}.shtml",
    }

    # 确定要下载的页面
    if DOWNLOAD_PAGE_TYPE == "all":
        pages = list(page_map.items())
        random.shuffle(pages)  # 随机访问顺序
    elif DOWNLOAD_PAGE_TYPE in page_map:
        pages = [(DOWNLOAD_PAGE_TYPE, page_map[DOWNLOAD_PAGE_TYPE])]
    else:
        print(f"❌ 不支持的页面类型：{DOWNLOAD_PAGE_TYPE}")
        return

    print(f"\n===== 开始处理股票：{stock_code} =====")
    success_count = 0

    # 下载每个页面
    for i, (page_name, url) in enumerate(pages, 1):
        print(f"\n[{i}/{len(pages)}] 处理 {page_name} 页面")
        if download_and_clean_page(url, stock_code, page_name, cleaner):
            success_count += 1

        # 页面间间隔等待（最后一页不等待）
        if i < len(pages):
            wait_time = random.uniform(*REQUEST_INTERVAL)
            print(f"⏳ 页面间隔等待 {wait_time:.1f} 秒")
            time.sleep(wait_time)

    print(f"\n✅ {stock_code} 处理完成：成功 {success_count}/{len(pages)}")
    return success_count

# ===================== 主函数 =====================
def main(stock_codes):
    print("=" * 60)
    print("          证券之星股票数据下载+清洗工具")
    print(f"待处理股票：{stock_codes}")
    print(f"输出格式：TXT={EXPORT_PLAIN_TXT} | HTML={EXPORT_CLEANED_HTML}")
    print("=" * 60)

    # 初始化清洗器
    cleaner = HtmlCleaner()

    # 处理每个股票
    total_success = 0
    total_pages = 0

    for idx, code in enumerate(stock_codes):
        code = code.strip()
        if not code:
            continue
        
        success = process_single_stock(code, cleaner)
        total_success += success
        
        # 股票切换等待（最后一个股票不等待）
        if idx < len(stock_codes) - 1:
            switch_wait = random.uniform(*STOCK_SWITCH_WAIT)
            print(f"\n⏳ 切换股票，等待 {switch_wait:.1f} 秒")
            time.sleep(switch_wait)

    print("\n" + "=" * 60)
    print(f"🎉 所有任务完成！总计成功处理 {total_success} 个页面")
    print(f"📁 输出目录：{OUTPUT_BASE_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="证券之星股票下载+清洗工具")
    parser.add_argument("-code", required=True, help="股票代码，多个用英文逗号分隔")
    args = parser.parse_args()

    # 处理股票代码列表
    stock_code_list = [c.strip() for c in args.code.split(",") if c.strip()]
    
    # 执行主程序
    main(stock_code_list)