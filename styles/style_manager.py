# -*- coding: utf-8 -*-
"""
style_manager — 龙虾研报统一样式管理器
========================================
现在使用纯 CSS 文件（palettes.css + base.css）

Style样式参数：
  style       (blue/purple/green/...)  →  颜色主题（从 palettes.css 加载）
  color_type  (solid/gradient/liquid)  →  渲染类型（纯色/渐变/液态）
  layout      (rounded/square/minimal) →  布局风格（圆角/方正/极简）

用法：
  from styles.style_manager import get_css, list_styles

  css = get_css(style="blue", color_type="liquid", layout="rounded")
  # 返回的 CSS 包含了 palettes.css + base.css，通过 data-* 属性激活对应效果
  # HTML 需要添加 data-palette="blue" data-color-type="liquid" data-layout="rounded"
"""

import os

_STYLES_DIR = os.path.dirname(os.path.abspath(__file__))


def _read_css(filename: str) -> str:
    """读取 CSS 文件内容"""
    path = os.path.join(_STYLES_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSS file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_css(style: str = "blue", color_type: str = "liquid", layout: str = "rounded") -> str:
    """
    获取完整报告 CSS 字符串。

    返回的 CSS 已包含所有调色板定义 + 基础样式，
    HTML 端只需设置 data-palette、data-color-type、data-layout 属性即可生效。

    Args:
        style:      颜色主题名称，如 "blue", "purple", "green" ...
        color_type: 渲染类型 — "solid" (纯色) | "gradient" (渐变) | "liquid" (液态)
        layout:     布局风格 — "rounded" (圆角) | "square" (方正) | "minimal" (极简)

    Returns:
        完整 CSS 样式字符串（palettes.css + base.css 合并）
    """
    palette_css = _read_css("palettes.css")
    base_css = _read_css("base.css")
    return palette_css + "\n" + base_css


def get_html_attrs(style: str = "blue", color_type: str = "liquid", layout: str = "rounded") -> str:
    """
    获取 HTML 标签属性字符串，用于 body 或其他容器元素。

    返回值示例：
      data-palette="blue" data-color-type="liquid" data-layout="rounded"
    """
    return f'data-palette="{style}" data-color-type="{color_type}" data-layout="{layout}"'


def list_styles() -> list:
    """返回所有可用颜色主题名称的排序列表"""
    return sorted([
        "blue", "purple", "green", "indigo", "orange",
        "pink", "red", "yellow", "cyan", "brown",
    ])


# ── 便捷速查 ──
STYLE_NAMES = list_styles()
COLOR_TYPES = ["solid", "gradient", "liquid"]
LAYOUTS     = ["rounded", "square", "minimal"]
