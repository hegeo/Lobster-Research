# -*- coding: utf-8 -*-
"""
龙虾调研助手  - HTML报告生成模块
================================
统一报告生成入口，支持 HTML / PDF 两种输出格式。

【PDF 方案】
  HTML → OpenClaw browser.pdf() 转 A4 PDF（无边距打印）
  style需要读取配置文件
"""
from __future__ import annotations

import os, sys, io
from datetime import datetime
from typing import Optional
# UTF-8 stdout：仅当当前 stdout 不是 UTF-8 编码时才重定向，避免二次包装
if getattr(sys.stdout, 'encoding', None) != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SKILL_ROOT)

from modules.extend import REPORT_TYPES, match_report_type, get_template, LOBSTER_QUOTES
from config.config import get
REPORT_STYLE = get("output.report_style", "ios_liquid")
import styles as _styles_lib


def _load_css(style: Optional[str] = None) -> str:
    """从 styles/ 目录加载样式 CSS，优先用传入值，否则读 config"""
    return _styles_lib.load_style(style if style else REPORT_STYLE)


def _build_overview_table(data: dict) -> str:
    """生成概览表格 HTML"""
    t = data.get("overview_table")
    if not t:
        return ""
    headers = t.get("headers", [])
    rows = t.get("rows", [])
    header_html = "".join(f"<th>{h}</th>" for h in headers)
    rows_html = ""
    for row in rows:
        cells = "".join(f"<td>{c}</td>" for c in row)
        rows_html += f"<tr>{cells}</tr>"
    return f"""
<div class="overview-table-wrap">
  <h3>📋 核心速览</h3>
  <table>{header_html}<tbody>{rows_html}</tbody></table>
</div>"""


def _build_metrics_bar(data: dict) -> str:
    """生成指标卡条"""
    metrics = data.get("metrics", [])
    if not metrics:
        return ""
    cards = ""
    for m in metrics:
        label = m.get("label", "")
        value = m.get("value", "-")
        change = m.get("change", "")
        cards += f"""<div class="metric-card">
  <div class="metric-label">{label}</div>
  <div class="metric-value">{value}</div>
  {'<div class="metric-change">' + change + '</div>' if change else ''}
</div>"""
    return f'<div class="metrics-bar">{cards}</div>'


def _build_trends_table(data: dict) -> str:
    """生成趋势预判表格"""
    t = data.get("trends_table")
    if not t:
        return ""
    headers = t.get("headers", [])
    rows = t.get("rows", [])
    header_html = "".join(f"<th>{h}</th>" for h in headers)
    rows_html = ""
    for row in rows:
        cells = "".join(f"<td>{c}</td>" for c in row)
        rows_html += f"<tr>{cells}</tr>"
    return f"""
<div class="data-table-wrap" style="margin-top:16px">
  <table><thead><tr>{header_html}</tr></thead>
  <tbody>{rows_html}</tbody></table>
</div>"""


def _build_section(s: dict) -> str:
    """生成单个章节 HTML"""
    title = s.get("title", "")
    subs_html = ""
    for sub in s.get("subsections", []):
        sub_title = sub.get("title", "")
        content = sub.get("content", "").replace("\n", "<br>")
        highlight = sub.get("highlight", "")
        table = sub.get("table", None)

        sub_html = f'<div class="subsection-title">{sub_title}</div>' if sub_title else ""
        sub_html += f'<div class="subsection-content">{content}</div>'

        if highlight:
            sub_html += f'<div class="highlight-box">{highlight}</div>'

        if table:
            t_headers = "".join(f"<th>{h}</th>" for h in table.get("headers", []))
            t_rows = ""
            for row in table.get("rows", []):
                cells = "".join(f"<td>{c}</td>" for c in row)
                t_rows += f"<tr>{cells}</tr>"
            style = table.get("style", "default")
            sub_html += f"""<div class="data-table-wrap">
<table><thead><tr>{t_headers}</tr></thead><tbody>{t_rows}</tbody></table>
</div>"""

        subs_html += f'<div class="subsection">{sub_html}</div>'

    return f'<div class="section"><div class="section-title">{title}</div>{subs_html}</div>'


def _build_html(data: dict, report_type_label: str = "龙虾研报", css: str = "") -> str:
    """构建完整 HTML 报告"""
    title = data.get("title", report_type_label)
    subtitle = data.get("subtitle", "")
    date = data.get("date", datetime.now().strftime("%Y年%m月%d日"))
    author = data.get("author", "龙虾财经研究院")
    summary = data.get("summary", "")
    quote = data.get("quote", "市场从不缺机会，缺的是等待的耐心。 🦞")
    disclaimer = data.get(
        "disclaimer",
        "免责声明：数据来源于公开网络搜索整理，仅供信息参考，不构成任何投资建议。"
    )

    # 概览 + 指标
    overview_html = _build_overview_table(data)
    metrics_html = _build_metrics_bar(data)

    # 章节
    sections_html = ""
    for s in data.get("sections", []):
        sections_html += _build_section(s)

    # 趋势预判（附加到第一个章节或独立）
    trends_html = _build_trends_table(data)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="page-frame">

<!-- 封面 -->
<div class="cover">
  <div class="cover-inner">
    <div class="cover-label">Lobster Research · {report_type_label}</div>
    <div class="cover-title">{title}</div>
    <div class="cover-subtitle">{subtitle}</div>
    <div class="cover-meta">
      <span>📅 {date}</span>
      <span>👨‍💻 {author}</span>
      <span>🦞 龙虾智能研报中心</span>
    </div>
    <div class="cover-lobster">🦞</div>
  </div>
</div>

<!-- 概览 + 指标 -->
{metrics_html}
{overview_html}

<!-- 章节内容 -->
<div class="page-break"></div>
{sections_html}

<!-- 趋势预判表格（若在各章节内未包含则独立显示）-->
{trends_html}

<!-- 摘要 -->
{'<div class="summary-box"><div class="summary-label">📌 核心摘要</div><div class="summary-text">' + summary + '</div></div>' if summary else ''}

<!-- 龙虾寄语 -->
{'<div class="quote-box">' + quote + '</div>' if quote else ''}

<!-- 免责声明 -->
<div class="disclaimer">{disclaimer}</div>

</div><!-- /.page-frame -->
</body>
</html>"""


# ═══════════════════════════════════════════════════════════
#  统一入口
# ═══════════════════════════════════════════════════════════

def generate_report(
    user_input: str = "",
    explicit_type: Optional[str] = None,
    data: Optional[dict] = None,
    output_format: Optional[str] = None,
    output_path: Optional[str] = None,
    config_output_format: Optional[str] = None,
    style: Optional[str] = None,
) -> dict:
    """
    统一报告生成入口

    Args:
        user_input:       用户原始输入/请求文本
        explicit_type:    显式指定的报告类型（如 "dapan_ribao"）
        data:             预填充的报告数据
        output_format:    输出格式 override（"html" | "pdf"）
        output_path:      输出文件路径
        config_output_format: 从 config 读取的默认格式
        style:            样式名称（覆盖 config.REPORT_STYLE），如 "orange"、"ios_liquid"

    Returns:
        dict { success, format, path, content }
    """
    if data is None:
        data = {}

    # 解析类型
    if explicit_type and explicit_type in REPORT_TYPES:
        rt = REPORT_TYPES[explicit_type]
        report_key = explicit_type
        report_label = rt.get("label", explicit_type)
    else:
        matched = match_report_type(user_input) if user_input else list(REPORT_TYPES.keys())[0]
        rt = REPORT_TYPES.get(matched, REPORT_TYPES["kuaisu_kuaibao"])
        report_key = matched
        report_label = rt.get("label", matched)

    fmt = output_format or config_output_format or "html"

    # 填充时间字段
    now = datetime.now()
    data.setdefault("date", now.strftime("%Y年%m月%d日"))
    data.setdefault("author", "龙虾财经研究院")

    # 从样式文件加载 CSS
    css = _load_css(style)

    # 生成 HTML
    html_content = _build_html(data, report_label, css)

    # 输出路径
    if not output_path:
        output_dir = os.path.join(_SKILL_ROOT, "output")
        os.makedirs(output_dir, exist_ok=True)
        ts = now.strftime("%Y%m%d_%H%M%S")
        ext = "html" if fmt == "html" else "pdf"
        output_path = os.path.join(output_dir, f"{report_key}_{ts}.{ext}")

    try:
        if fmt == "html":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            return {
                "success": True,
                "format": "html",
                "path": output_path,
                "content": html_content[:500],
            }
        else:
            # PDF 格式：保存 HTML → Chrome headless 打印
            html_path = output_path.replace(".pdf", ".html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Chrome headless 无边框打印
            import subprocess
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            ]
            chrome = None
            for p in chrome_paths:
                if os.path.exists(p):
                    chrome = p
                    break

            if chrome:
                cmd = [
                    chrome,
                    "--headless", "--disable-gpu",
                    f'--print-to-pdf="{output_path}"',
                    "--print-to-pdf-no-header",
                    f'file:///{html_path.replace(chr(92), "/")}',
                ]
                try:
                    subprocess.run(cmd, capture_output=True, timeout=30)
                    if os.path.exists(output_path):
                        return {
                            "success": True,
                            "format": "pdf",
                            "path": output_path,
                            "html_path": html_path,
                            "content": f"[PDF] {output_path}",
                        }
                except Exception as chrome_err:
                    pass  # 降级：返回 HTML 路径

            # 降级：返回 HTML 路径（由调用方自行打印）
            return {
                "success": True,
                "format": "html",
                "path": html_path,
                "html_path": html_path,
                "content": f"[HTML] {html_path}（请用浏览器打印为PDF）",
            }
    except Exception as e:
        return {
            "success": False,
            "format": fmt,
            "error": str(e),
            "path": None,
            "content": f"[ERROR] {e}",
        }
