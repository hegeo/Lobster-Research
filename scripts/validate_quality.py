# -*- coding: utf-8 -*-
"""
龙虾调研 — 质量校验模块
==========================
共享函数，供 generate_report.py 和 generate_alonemode.py 共用。

职责：
  1. _normalize_table()   — 兼容两种 table 输入格式，自动转换
  2. check_report_input() — 校验 5_agent_report_input.json 的结构完整性
  3. check_report_html()  — 生成后校验 HTML 报告的内容充实度
"""

from __future__ import annotations
from typing import Optional


# ═══════════════════════════════════════════════════════════
#  类型感知的阈值
# ═══════════════════════════════════════════════════════════

def _get_quality_thresholds(report_type: str, prompt_template: Optional[dict] = None) -> dict:
    """
    根据报告类型返回校验阈值。

    判断逻辑：
      1. 优先从 prompt_template 的 type 字段判断（"快报" / "研报"）
      2. 次优从 report_type 名称判断
      3. 默认走研报标准
    """
    # 从模板 type 判断
    tpl_type = (prompt_template or {}).get("type", "")
    if tpl_type == "快报":
        return {"min_sections": 3, "min_tables": 0, "min_chars": 1800, "mode": "quick"}
    if tpl_type == "研报":
        return {"min_sections": 8, "min_tables": 3, "min_chars": 5000, "mode": "deep"}

    # fallback: 从 report_type 名称判断
    quick_types = ["kuaibao", "dongtai", "shunshi", "kuaisu"]
    if any(q in report_type for q in quick_types):
        return {"min_sections": 3, "min_tables": 0, "min_chars": 1800, "mode": "quick"}
    return {"min_sections": 8, "min_tables": 3, "min_chars": 5000, "mode": "deep"}


# ═══════════════════════════════════════════════════════════
#  table 格式归一化
# ═══════════════════════════════════════════════════════════

def normalize_table(table, section_label="", sub_label=""):
    """
    统一 table 字段为 {headers: [...], rows: [...]} 格式。

    兼容三种 Agent 输入：
      ✅ 正确: {"headers": ["h1"], "rows": [["v1"]]}
      ✅ 自动转: [["h1"], ["v1"]] → {"headers": ["h1"], "rows": [["v1"]]}
      ✅ 自动转: "| h1 |\\n|:---|\\n| v1 |" → {"headers": ["h1"], "rows": [["v1"]]}

    返回:
      dict | None   — None 表示无效或空表
    """
    if not table:
        return None

    if isinstance(table, list):
        # Agent 写了数组套数组格式 → 自动转换
        if not table:
            return None
        headers = table[0] if isinstance(table[0], list) else table
        rows = table[1:] if len(table) > 1 and isinstance(table[1], list) else []
        print(f"  ⚠️ table 格式自动转换（{section_label}/{sub_label}）：array → obj")
        return {"headers": headers, "rows": rows}

    if isinstance(table, dict):
        return table

    if isinstance(table, str):
        # Agent 写了 markdown 表格字符串 → 自动解析
        lines = [l.strip() for l in table.strip().split('\n') if l.strip()]
        if len(lines) < 2:
            print(f"  ⚠️ table 格式无法识别（{section_label}/{sub_label}）：str 行数不足")
            return None

        def split_row(row):
            r = row.strip()
            if r.startswith('|'): r = r[1:]
            if r.endswith('|'): r = r[:-1]
            return [c.strip() for c in r.split('|')]

        # 第一行: headers
        headers = split_row(lines[0])
        # 第二行: 分隔线（跳过）
        rows = []
        for row in lines[2:]:
            cells = split_row(row)
            if len(cells) >= 2:  # 至少2列才认为是有效行
                rows.append(cells)

        if not headers or not rows:
            print(f"  ⚠️ table 格式无法识别（{section_label}/{sub_label}）：str 解析结果为空")
            return None

        print(f"  ⚠️ table 格式自动转换（{section_label}/{sub_label}）：str → obj")
        return {"headers": headers, "rows": rows}

    print(f"  ⚠️ table 格式无法识别（{section_label}/{sub_label}）：{type(table).__name__}")
    return None


# ═══════════════════════════════════════════════════════════
#  5_agent_report_input.json 校验
# ═══════════════════════════════════════════════════════════

def check_report_input(data: dict, prompt_template: Optional[dict] = None) -> dict:
    """
    校验 5_agent_report_input.json 的结构完整性。

    返回:
      {
        "ok": True/False,
        "mode": "quick" | "deep",
        "section_count": N,
        "table_count": N,
        "total_chars": N,
        "warnings": [...],
        "errors": [...],
        "thresholds": {...}
      }
    """
    report_type = data.get("_report_type", "") or ""
    thresholds = _get_quality_thresholds(report_type, prompt_template)
    mode = thresholds["mode"]
    warnings = []
    errors = []

    # — 检查 sections —
    sections = data.get("sections", [])
    section_count = len(sections)

    if section_count < thresholds["min_sections"]:
        warnings.append(
            f"sections 不足: 当前 {section_count} 个, 期望 ≥{thresholds['min_sections']} ({mode}模式)"
        )

    # — 遍历 sections 统计 table 数和字数 —
    table_count = 0
    total_chars = 0
    empty_content_sections = []

    for si, s in enumerate(sections):
        title = s.get("title", f"sections[{si}]")
        subs = s.get("subsections", [])
        for sub in subs:
            content = sub.get("content", "")
            total_chars += len(content)

            # 检查 content 是否为占位符或过短
            clean = content.strip().lstrip("_")
            if len(clean) < 20:
                empty_content_sections.append(f"{title}/{sub.get('title', 'untitled')}")

            # 检查 table 格式
            table = sub.get("table")
            if table:
                if isinstance(table, list):
                    warnings.append(
                        f"table 格式需转换: {title}/{sub.get('title', '')} 当前为 array，需 {headers,rows} 格式"
                    )
                elif isinstance(table, dict):
                    t_headers = table.get("headers", [])
                    if not t_headers:
                        warnings.append(f"table headers 为空: {title}/{sub.get('title', '')}")
                    table_count += 1

    # — 检查顶层字段 —
    if mode == "deep":
        if not data.get("overview_table"):
            warnings.append("overview_table 缺失（研报推荐包含）")
        if not data.get("metrics"):
            warnings.append("metrics 指标卡缺失（研报推荐包含）")

    # — 空内容告警 —
    if empty_content_sections:
        for sec in empty_content_sections[:5]:  # 最多显示 5 条
            warnings.append(f"内容过短或未填入: {sec}")
        if len(empty_content_sections) > 5:
            warnings.append(f"... 还有 {len(empty_content_sections) - 5} 个章节内容过短")

    # — 总字数 —
    if total_chars < thresholds["min_chars"]:
        warnings.append(
            f"总字数不足: 当前约 {total_chars} 字, 期望 ≥{thresholds['min_chars']} ({mode}模式)"
        )

    ok = len(errors) == 0

    return {
        "ok": ok,
        "mode": mode,
        "section_count": section_count,
        "table_count": table_count,
        "total_chars": total_chars,
        "warnings": warnings,
        "errors": errors,
        "thresholds": thresholds,
    }


# ═══════════════════════════════════════════════════════════
#  HTML 报告质量快报（generate 后调用）
# ═══════════════════════════════════════════════════════════

def format_quality_report(quality: dict) -> str:
    """格式化质量快报为一行终端输出"""
    icon = "✅" if quality["ok"] and not quality["warnings"] else "⚠️" if quality["ok"] else "❌"
    mode = quality["mode"].upper()
    warnings = quality["warnings"]
    w_text = f" | ⚠️ {len(warnings)} 条警告" if warnings else ""
    return (
        f"{icon} [{mode}] 质量快报: "
        f"{quality['section_count']} sections | "
        f"{quality['table_count']} tables | "
        f"约{quality['total_chars']}字"
        f"{w_text}"
    )
