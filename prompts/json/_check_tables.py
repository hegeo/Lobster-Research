# -*- coding: utf-8 -*-
"""检查所有模板的表格数量是否与 promptBody 描述一致"""
import json, os, glob, re

BASE = r"C:\Users\Livecha\.workbuddy\skills\lobster-research-v2.2\prompts\json"
files = sorted(glob.glob(os.path.join(BASE, "*.json")))

TOTAL_TEMPLATES = len(files)
print(f"共扫描 {TOTAL_TEMPLATES} 个模板\n")

for fp in files:
    name = os.path.basename(fp)
    with open(fp, encoding="utf-8") as f:
        d = json.load(f)

    t = d.get("type", "")
    secs = d.get("sections", [])
    pb = d.get("promptBody", "")
    is_yanbao = t in ("研报", "专家研报", "白皮书")
    is_kuaibao = t == "快报"

    # ── 统计 sections 中的表格 ──
    sec_tables = 0
    sec_subs_total = 0
    for si, s in enumerate(secs):
        for sub in s.get("subsections", []):
            sec_subs_total += 1
            tbl = sub.get("table")
            if tbl and isinstance(tbl, str) and tbl.strip() and not tbl.strip().startswith("_"):
                sec_tables += 1
            elif tbl and isinstance(tbl, dict) and tbl.get("headers"):
                sec_tables += 1
            elif tbl and isinstance(tbl, list) and len(tbl) > 0:
                sec_tables += 1

    # ── 统计 promptBody 中描述的表格 ──
    # 找 "表1" / "表X" 关键词（表示该段落有表）
    pb_has_table_blocks = 0
    pb_no_table_blocks = 0
    if pb:
        paragraphs = re.split(r'\n---\n', pb)
        for para in paragraphs:
            if "表1" in para or "表 " in para or re.search(r'表\d+', para):
                pb_has_table_blocks += 1
            elif "无表格" in para:
                pb_no_table_blocks += 1

    # ── 检查快照 section 是否无表 ──
    snapshot_table_issues = []
    for s in secs:
        if "快照" in s.get("title", "") or "速读" in s.get("title", ""):
            for sub in s.get("subsections", []):
                tbl = sub.get("table")
                if tbl and isinstance(tbl, str) and "_" not in tbl:
                    snapshot_table_issues.append(f"{s['title']} 有表（应无表）")
                elif tbl and isinstance(tbl, dict) and tbl.get("headers"):
                    snapshot_table_issues.append(f"{s['title']} 有表（应无表）")

    # ── 特别检查 _Agent 占位表格（非真正有效的表）─
    placeholder_tables = 0
    real_tables = 0
    for s in secs:
        for sub in s.get("subsections", []):
            tbl = sub.get("table")
            if tbl is None:
                continue
            if isinstance(tbl, str) and "_Agent" in tbl:
                placeholder_tables += 1
            elif isinstance(tbl, str) and tbl.strip().startswith("_"):
                placeholder_tables += 1
            elif isinstance(tbl, (dict, list)):
                real_tables += 1

    # 输出
    issues = []
    if is_yanbao:
        # 研报：检查 table 比例是否合理
        if sec_subs_total > 0 and placeholder_tables == 0 and real_tables == 0 and sec_subs_total > 3:
            issues.append(f"全无表格（{sec_subs_total} subs）")
    elif is_kuaibao:
        if sec_subs_total > 0 and placeholder_tables == 0 and real_tables == 0:
            issues.append(f"全无表格（{sec_subs_total} subs）")

    if snapshot_table_issues:
        for x in snapshot_table_issues:
            issues.append(x)

    # ── 高级检查：promptBody 嵌套的段落级别 table 统计 ──
    pb_table_count = 0
    pb_none_count = 0
    if pb:
        # 拆段落（按 段落① 或 - 段落 或 "。\n\n" 等）
        # 更简单的方法：统计 "表1" 和 "无表格" 的出现次数
        pb_table_count = len(re.findall(r'表\d+\s*\d+行', pb))
        pb_none_count = len(re.findall(r'无表格', pb))

    # 综合判断
    if is_yanbao or is_kuaibao:
        status = "✅" if not issues else "⚠️"
        print(f"{status} {name} | {t}")
        print(f"   subs={sec_subs_total} | 占位表={placeholder_tables} | 真实表={real_tables}")
        if pb:
            print(f"   promptBody: 表段落≈{pb_table_count}处 | 无表格≈{pb_none_count}处")
        if issues:
            for x in issues:
                print(f"   ⚠️ {x}")
        print()
    else:
        # 非标准 type（如 白皮书 等）
        print(f"➡️ {name} | type={t} | subs={sec_subs_total} | 表={placeholder_tables+real_tables}")
        if issues:
            for x in issues:
                print(f"   ⚠️ {x}")
        print()
