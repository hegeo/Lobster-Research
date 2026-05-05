# -*- coding: utf-8 -*-
import requests
import xml.etree.ElementTree as ET
import re
import sys
import io

# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 百度新闻RSS地址
BAIDU_CHANNELS = {
    "国际焦点": "http://news.baidu.com/n?cmd=1&class=internews&tn=rss",
    "军事焦点": "http://news.baidu.com/n?cmd=1&class=mil&tn=rss",
    "财经焦点": "http://news.baidu.com/n?cmd=1&class=finannews&tn=rss",
    "互联网焦点": "http://news.baidu.com/n?cmd=1&class=internet&tn=rss",
    "房产焦点": "http://news.baidu.com/n?cmd=1&class=housenews&tn=rss",
    "汽车焦点": "http://news.baidu.com/n?cmd=1&class=autonews&tn=rss",
    "体育焦点": "http://news.baidu.com/n?cmd=1&class=sportnews&tn=rss",
    "娱乐焦点": "http://news.baidu.com/n?cmd=1&class=enternews&tn=rss",
    "游戏焦点": "http://news.baidu.com/n?cmd=1&class=gamenews&tn=rss",
    "教育焦点": "http://news.baidu.com/n?cmd=1&class=edunews&tn=rss",
    "女人焦点": "http://news.baidu.com/n?cmd=1&class=healthnews&tn=rss",
    "科技焦点": "http://news.baidu.com/n?cmd=1&class=technnews&tn=rss",
    "社会焦点": "http://news.baidu.com/n?cmd=1&class=socianews&tn=rss",
}

def clean_text(s):
    if not s:
        return ""
    s = re.sub(r'<.*?>', '', s)
    s = re.sub(r'&nbsp;|&quot;|&amp;|&lt;|&gt;', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def fetch_news(channel_name, url, limit=10):
    try:
        session = requests.Session()
        resp = session.get(url, timeout=3)
        resp.encoding = 'utf-8'
        root = ET.fromstring(resp.text)

        print(f"\n📌 {channel_name}")
        print("-" * 70)

        count = 0
        for item in root.findall("./channel/item"):
            if count >= limit:
                break
            title = clean_text(item.findtext("title", ""))
            desc = clean_text(item.findtext("description", ""))
            time = item.findtext("pubDate", "")[:19]

            print(f"{count+1}. {title}")
            if desc:
                print(f"   {desc[:120]}..." if len(desc) > 120 else f"   {desc}")
            print(f"   {time}\n")
            count += 1

    except Exception as e:
        print(f"\n📌 {channel_name}")
        print("-" * 70)
        print("获取失败\n")

# ===================== 命令行参数版本 =====================
if __name__ == "__main__":
    print("="*70)
    print("百度新闻命令行工具")
    print("用法：python news.py 科技 | 军事 | 财经 | ALL")
    print("="*70)

    # 默认显示10条
    NEWS_COUNT = 10

    # 读取命令行输入的参数
    if len(sys.argv) < 2:
        print("请输入分类，例如：python news.py 科技")
        sys.exit(1)

    keyword = sys.argv[1]

    # 模糊匹配（输入 科技 = 匹配 科技焦点）
    target_mode = None
    for channel_name in BAIDU_CHANNELS.keys():
        if keyword in channel_name:
            target_mode = channel_name
            break

    # 如果匹配到
    if target_mode:
        fetch_news(target_mode, BAIDU_CHANNELS[target_mode], limit=NEWS_COUNT)
    
    # 如果输入 ALL
    elif keyword.upper() == "ALL":
        for name, url in BAIDU_CHANNELS.items():
            fetch_news(name, url, limit=NEWS_COUNT)
    
    else:
        print(f"找不到匹配的分类：{keyword}")
        print("支持：国际、军事、财经、互联网、房产、汽车、体育、娱乐、游戏、教育、女人、科技、社会")