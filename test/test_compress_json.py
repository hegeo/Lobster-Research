# -*- coding: utf-8 -*-
"""TextCompressor JSON 压缩测试 — 输出文件供对比"""
import json, os
from compresstext import TextCompressor

SRC = "test/2_stock_info_detail.json"
OUT_DIR = "test/compress_output"

with open(SRC, "r", encoding="utf-8") as f:
    data = json.load(f)

raw = data["raw_text"]

# 创建输出目录
os.makedirs(OUT_DIR, exist_ok=True)

print("=" * 55)
print("  原始数据概况")
print("=" * 55)
print(f"  来源文件: {SRC}")
print(f"  raw_text 长度: {len(raw)} 字符")
print(f"  预估句子数: 约 {raw.count('。') + raw.count('！') + raw.count('？')}")

# 压缩
c = TextCompressor()
compressed_data = c.compress_json(data, target_keys=["raw_text"])
compressed_text = compressed_data["raw_text"]

print()
print("=" * 55)
print("  压缩统计")
print("=" * 55)
print(f"  原始长度: {len(raw)}")
print(f"  压缩后:   {len(compressed_text)}")
print(f"  压缩比:   {len(compressed_text)/len(raw):.1%}")
c.print_stats()

# ── 输出文件 ──

# 1. 压缩后的完整 JSON
out_json = os.path.join(OUT_DIR, "2_stock_info_detail_compressed.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(compressed_data, f, ensure_ascii=False, indent=2)
print(f"\n  [输出] 压缩后 JSON: {out_json}")

# 2. 原始 raw_text 纯文本
out_raw = os.path.join(OUT_DIR, "raw_original.txt")
with open(out_raw, "w", encoding="utf-8") as f:
    f.write(raw)
print(f"  [输出] 原始纯文本:   {out_raw}")

# 3. 压缩后 raw_text 纯文本
out_comp = os.path.join(OUT_DIR, "raw_compressed.txt")
with open(out_comp, "w", encoding="utf-8") as f:
    f.write(compressed_text)
print(f"  [输出] 压缩后纯文本: {out_comp}")

# 4. 完整的新 JSON（保留原始 JSON 结构，仅 raw_text 被压缩）
out_full = os.path.join(OUT_DIR, "2_stock_info_detail_full.json")
full_output = data.copy()
full_output["raw_text"] = compressed_text
with open(out_full, "w", encoding="utf-8") as f:
    json.dump(full_output, f, ensure_ascii=False, indent=2)
print(f"  [输出] 完整压缩 JSON: {out_full}")

# 5. 文件大小对比
print()
print("=" * 55)
print("  文件大小对比")
print("=" * 55)
for name in ["raw_original.txt", "raw_compressed.txt",
             "2_stock_info_detail_compressed.json",
             "2_stock_info_detail_full.json"]:
    path = os.path.join(OUT_DIR, name)
    size = os.path.getsize(path)
    ratio = f"({size/os.path.getsize(os.path.join(OUT_DIR, 'raw_original.txt')):.1%})" if name != "raw_original.txt" else ""
    print(f"  {name:<40s} {size:>8,} 字节 {ratio}")

print()
print("用以下命令对比原始和压缩内容：")
print(f"  code --diff {OUT_DIR}\\raw_original.txt {OUT_DIR}\\raw_compressed.txt")
print(f"  或记事本分别打开两个文件对照")
