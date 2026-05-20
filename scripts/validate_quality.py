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
import json
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
        return {"min_sections": 3, "min_tables": 0, "min_chars": 1800, "mode": "quick", "min_chars_per_section": 150}
    if tpl_type == "研报":
        return {"min_sections": 8, "min_tables": 3, "min_chars": 5000, "mode": "deep", "min_chars_per_section": 300}

    # fallback: 从 report_type 名称判断
    quick_types = ["kuaibao", "dongtai", "shunshi", "kuaisu"]
    if any(q in report_type for q in quick_types):
        return {"min_sections": 3, "min_tables": 0, "min_chars": 1800, "mode": "quick", "min_chars_per_section": 150}
    return {"min_sections": 8, "min_tables": 3, "min_chars": 5000, "mode": "deep", "min_chars_per_section": 300}


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
#  JSON 自动修复（可独立调用 / 被 task_runner 引用）
# ═══════════════════════════════════════════════════════════

def auto_fix_json(raw: str) -> str:
    """
    通用 JSON 自动修复函数。
    与 task_runner._fix_json_common_issues 逻辑一致，可供外部独立调用。

    修复清单：
      1. 字符串内未转义的控制字符（\n, \r, \t → \\n, \\r, \\t）
      2. 字符串内误用的 ASCII 直引号 ""  → Unicode 引号 ""
    """
    result = []
    i = 0
    in_string = False
    escape_next = False

    while i < len(raw):
        c = raw[i]

        if escape_next:
            result.append(c)
            escape_next = False
            i += 1
            continue

        if c == '\\' and in_string:
            result.append(c)
            escape_next = True
            i += 1
            continue

        # 控制字符转义（仅在字符串内）
        if in_string:
            cp = ord(c)
            if cp == 0x0A:
                result.append('\\n')
                i += 1
                continue
            elif cp == 0x0D:
                result.append('\\r')
                i += 1
                continue
            elif cp == 0x09:
                result.append('\\t')
                i += 1
                continue
            elif cp < 0x20:
                result.append('\\u00' + format(cp, '02x'))
                i += 1
                continue

        # 双引号处理
        if c == '"':
            if not in_string:
                in_string = True
                result.append(c)
            else:
                rest = raw[i + 1:].lstrip()
                if rest and rest[0] in ':,]}\n\r':
                    in_string = False
                    result.append(c)
                elif rest and rest[0] == '"':
                    in_string = False
                    result.append(c)
                else:
                    # 内容中的中文引号，向前找配对
                    j = i + 1
                    close_pos = -1
                    while j < len(raw):
                        if raw[j] == '"':
                            rest2 = raw[j + 1:].lstrip()
                            if rest2 and rest2[0] in ':,]}\n\r':
                                break
                            elif rest2 and rest2[0] == '"':
                                break
                            else:
                                close_pos = j
                                break
                        j += 1

                    if close_pos > 0:
                        inner = raw[i + 1:close_pos]
                        result.append('\u201c')
                        result.append(inner)
                        result.append('\u201d')
                        i = close_pos + 1
                        continue
                    else:
                        in_string = False
                        result.append(c)
            i += 1
            continue

        result.append(c)
        i += 1

    return ''.join(result)


def load_json_with_auto_fix(path: str) -> dict:
    """
    读取 JSON 文件，自动修复后返回 dict。
    修复失败时抛出异常，保留 .bak 备份。
    """
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        fixed = auto_fix_json(raw)
        try:
            data = json.loads(fixed)
            # 修复成功，回写
            with open(path, "w", encoding="utf-8") as f:
                f.write(fixed)
            return data
        except json.JSONDecodeError:
            # 保留备份
            import shutil
            shutil.copy2(path, path + ".bak")
            raise


# ═══════════════════════════════════════════════════════════
#  5_agent_report_input.json 校验
# ═══════════════════════════════════════════════════════════

PLACEHOLDER_PATTERNS = ["待确认", "无数据", "未知", "暂无数据", "待补充"]


def _scan_table_placeholders(table: dict, section_label: str, sub_label: str) -> list:
    """扫描表格单元中的占位符，返回警告列表"""
    found = []
    if not table:
        return found
    rows = table.get("rows", [])
    for ri, row in enumerate(rows):
        for ci, cell in enumerate(row):
            cell_str = str(cell)
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern in cell_str:
                    found.append(f"表格含占位符「{pattern}」: {section_label}/{sub_label} row[{ri}] col[{ci}]")
                    break
    return found


def check_report_input(data: dict, prompt_template: Optional[dict] = None) -> dict:
    """
    校验 5_agent_report_input.json 的结构完整性。增强版：

    - 充实度: 每个章节字数统计与阈值检查
    - 丰富度: subsection 分布统计与空内容检测
    - 可读度: 表格列数匹配、highlight 非空
    - 数据完善: 扫描表格占位符

    返回:
      {
        "ok": True/False,
        "mode": "quick" | "deep",
        "section_count": N,
        "table_count": N,
        "total_chars": N,
        "warnings": [...],
        "errors": [...],
        "thresholds": {...},
        "section_chars": {...},
        "subsection_distribution": {...},
        "empty_subsections": [...],
        "table_issues": [...],
        "highlight_missing": [...],
        "placeholder_warnings": [...]
      }
    """
    report_type = data.get("_report_type", "") or ""
    thresholds = _get_quality_thresholds(report_type, prompt_template)
    mode = thresholds["mode"]
    warnings = []
    errors = []

    # 新增字段
    section_chars = {}
    subsection_distribution = {}
    empty_subsections = []
    table_issues = []
    highlight_missing = []
    placeholder_warnings = []

    # — 检查 sections —
    sections = data.get("sections", [])
    section_count = len(sections)

    if section_count < thresholds["min_sections"]:
        warnings.append(
            f"sections 不足: 当前 {section_count} 个, 期望 ≥{thresholds['min_sections']} ({mode}模式)"
        )

    # — 遍历 sections 统计 —
    table_count = 0
    total_chars = 0
    empty_content_sections = []

    for si, s in enumerate(sections):
        title = s.get("title", f"sections[{si}]")
        subs = s.get("subsections", [])
        subsection_distribution[title] = len(subs)

        # 丰富度: section 级别 subsection 数量
        if mode == "deep" and len(subs) < 2:
            warnings.append(f"章节「{title}」子节数不足: {len(subs)} 个, 研报建议 ≥2 个")

        section_total = 0
        for sub in subs:
            sub_title = sub.get("title", "")
            content = sub.get("content", "")
            section_total += len(content)
            total_chars += len(content)

            # 检查 content 是否为占位符或过短
            clean = content.strip().lstrip("_")
            if len(clean) < 20:
                empty_content_sections.append(f"{title}/{sub_title}")
                empty_subsections.append(f"{title}/{sub_title}")

            # 可读度: highlight 非空检查
            highlight = sub.get("highlight", "")
            if not highlight or (isinstance(highlight, str) and highlight.strip().startswith("_")):
                highlight_missing.append(f"{title}/{sub_title}")

            # 检查 table 格式
            table = sub.get("table")
            if table:
                if isinstance(table, list):
                    warnings.append(
                        f"table 格式需转换: {title}/{sub_title} 当前为 array，需 {{headers,rows}} 格式"
                    )
                elif isinstance(table, dict):
                    t_headers = table.get("headers", [])
                    t_rows = table.get("rows", [])
                    if not t_headers:
                        table_issues.append(f"table headers 为空: {title}/{sub_title}")
                    # 可读度: headers vs rows 列数匹配
                    if t_headers and t_rows:
                        for ri, row in enumerate(t_rows):
                            if len(row) != len(t_headers):
                                table_issues.append(
                                    f"table 列数不匹配: {title}/{sub_title} headers={len(t_headers)} 列, row[{ri}]={len(row)} 列"
                                )
                    # 可读度: 至少 1 行数据
                    if t_headers and len(t_rows) < 1:
                        table_issues.append(f"table 无数据行: {title}/{sub_title}")
                    # 数据完善: 扫描占位符
                    placeholder_warnings.extend(
                        _scan_table_placeholders(table, title, sub_title)
                    )
                    table_count += 1

        section_chars[title] = section_total

        # 充实度: section 级别字数检查
        min_per = thresholds.get("min_chars_per_section", 300 if mode == "deep" else 150)
        if section_total < min_per:
            warnings.append(
                f"章节「{title}」字数不足: {section_total} 字, 期望 ≥{min_per} 字 ({mode}模式)"
            )

    # — 检查顶层字段 —
    if mode == "deep":
        if not data.get("overview_table"):
            warnings.append("overview_table 缺失（研报推荐包含）")
        if not data.get("metrics"):
            warnings.append("metrics 指标卡缺失（研报推荐包含）")

    # — 空内容告警 —
    if empty_content_sections:
        for sec in empty_content_sections[:5]:
            warnings.append(f"内容过短或未填入: {sec}")
        if len(empty_content_sections) > 5:
            warnings.append(f"... 还有 {len(empty_content_sections) - 5} 个章节内容过短")

    # — 总字数 —
    if total_chars < thresholds["min_chars"]:
        warnings.append(
            f"总字数不足: 当前约 {total_chars} 字, 期望 ≥{thresholds['min_chars']} ({mode}模式)"
        )

    # — 汇总 table / highlight / placeholder 警告 —
    for issue in table_issues:
        warnings.append(issue)
    for h in highlight_missing:
        warnings.append(f"highlight 缺失或为占位符: {h}")
    for pw in placeholder_warnings:
        warnings.append(pw)

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
        "section_chars": section_chars,
        "subsection_distribution": subsection_distribution,
        "empty_subsections": empty_subsections,
        "table_issues": table_issues,
        "highlight_missing": highlight_missing,
        "placeholder_warnings": placeholder_warnings,
    }


# ═══════════════════════════════════════════════════════════
#  Agent 输出预检（HTML 生成前调用）
# ═══════════════════════════════════════════════════════════

def preflight_agent_input(
    data: dict,
    prompt_template: Optional[dict] = None,
    user_config: Optional[dict] = None,
) -> dict:
    """
    Agent 输出预检，在 HTML / PDF 生成前调用。
    目的是尽早发现 Agent 常见遗漏，而非阻断生成。

    检查项:
      1. 每个 section content 是否 >= 200 字
      2. 每个 subsection 是否有 highlight 字段（非空字符串）
      3. 是否包含 _fill_instructions / _prompt_body 残留
      4. 如果 user_config 提供 total_assets_range="below_10w":
         检查推荐股票代码是否在 600/000/002 范围内

    返回:
      {
        "ok": True/False,
        "section_count": N,
        "highlight_missing": [section_title, ...],
        "short_content": [section_path, ...],
        "residual_fields": [field_name, ...],
        "code_violations": [code, ...],
        "warnings": [str, ...],
        "errors": [str, ...],
      }
    """
    warnings = []
    errors = []
    sections = data.get("sections", [])
    highlight_missing = []
    short_content = []
    residual_fields = []
    code_violations = []

    # — 检查 1: 每个 section 字数 —
    for si, s in enumerate(sections):
        title = s.get("title", f"sections[{si}]")
        subs = s.get("subsections", [])
        for sub in subs:
            sub_title = sub.get("title", "untitled")
            path = f"{title}/{sub_title}"

            content = sub.get("content", "") or ""
            clean = content.strip().lstrip("_")
            if len(clean) < 200:
                short_content.append(path)
                warnings.append(f"章节内容不足 200 字: {path}（当前 {len(clean)} 字）")

            # — 检查 2: highlight 字段 —
            highlight = sub.get("highlight")
            if not highlight or (isinstance(highlight, str) and highlight.strip().startswith("_")):
                highlight_missing.append(path)
                warnings.append(f"highlight 缺失或为占位符: {path}")

    # — 检查 3: 残留字段 —
    residual_keys = ["_fill_instructions", "_prompt_body"]
    for key in residual_keys:
        if key in data:
            residual_fields.append(key)
            warnings.append(f"残留字段未清理: {key}（建议在 Agent 输出中删除）")

    # — 检查 4: 代码范围约束 —
    if user_config:
        assets_range = user_config.get("total_assets_range", "")
        if assets_range == "below_10w":
            # 从 sections 中扫描推荐代码
            for si, s in enumerate(sections):
                title = s.get("title", f"sections[{si}]")
                subs = s.get("subsections", [])
                for sub in subs:
                    content = sub.get("content", "") or ""
                    # 匹配 6 位股票代码
                    import re
                    codes = re.findall(r'(?<!\d)(6\d{5}|0\d{5}|300\d{3}|688\d{3})(?!\d)', content)
                    for code in codes:
                        if code.startswith("300") or code.startswith("688"):
                            code_violations.append(code)
                            warnings.append(
                                f"超范围标地代码: {code}（below_10w 用户禁止 300/688）"
                            )

    ok = len(errors) == 0

    return {
        "ok": ok,
        "section_count": len(sections),
        "highlight_missing": highlight_missing,
        "short_content": short_content,
        "residual_fields": residual_fields,
        "code_violations": code_violations,
        "warnings": warnings,
        "errors": errors,
    }


def format_preflight_report(result: dict) -> str:
    """格式化预检结果为一行的摘要"""
    icon = "✅" if result["ok"] and not result["warnings"] else "⚠️"
    parts = []
    if result["highlight_missing"]:
        parts.append(f"⬜溢出 {len(result['highlight_missing'])} 处")
    if result["short_content"]:
        parts.append(f"🩰短线 {len(result['short_content'])} 处")
    if result["residual_fields"]:
        parts.append(f"转存 {len(result['residual_fields'])} 个")
    if result["code_violations"]:
        parts.append(f"代码越界 {len(result['code_violations'])} 个")
    w_text = f" | {', '.join(parts)}" if parts else ""
    return f"{icon} 预检快报: {result['section_count']} sections{w_text}"


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
