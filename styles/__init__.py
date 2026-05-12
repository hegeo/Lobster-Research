# -*- coding: utf-8 -*-
"""
Styles package — report CSS theme loader.

纯 CSS 文件架构：
  palettes.css  — 10 色调色板自定义属性
  base.css      — 完整报告样式模板（var() + data-* 属性控制）
  style_manager.py — Python 加载器

3D parameter system:
  style       (blue/purple/green/...)  →  data-palette 属性选择器
  color_type  (solid/gradient/liquid)  →  data-color-type 属性选择器
  layout      (rounded/square/minimal) →  data-layout 属性选择器

Usage:
  from styles import load_style, list_styles
  css = load_style("blue", color_type="liquid", layout="rounded")
"""

from styles.style_manager import get_css, get_html_attrs, list_styles


def load_style(style: str = "blue", color_type: str = "liquid", layout: str = "rounded") -> str:
    """
    加载样式 CSS 字符串（向后兼容旧 API）。

    Args:
        style:      颜色主题名称，如 "blue", "purple"
        color_type: 渲染类型 — "solid" | "gradient" | "liquid"
        layout:     布局风格 — "rounded" | "square" | "minimal"

    Returns:
        CSS 样式字符串
    """
    return get_css(style=style, color_type=color_type, layout=layout)
