# -*- coding: utf-8 -*-
"""
样式测试脚本 - 快速验证不同样式效果
用法：python test_style.py [样式名]
示例：python test_style.py orange
      python test_style.py ios_liquid
默认：orange

所有 HTML 生成逻辑统一由 scripts/generate_report.py 提供，
本脚本只负责加载样式并调用报告生成入口。
"""
import sys
import os

# Windows 终端 UTF-8 输出
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SKILL_PATH = r"C:\Users\Livecha\.qclaw\skills\lobster_research"
TEST_DIR = os.path.join(SKILL_PATH, "test")
sys.path.insert(0, SKILL_PATH)
sys.path.insert(0, os.path.join(SKILL_PATH, "scripts"))

# 导入测试数据
from test_data import TEST_DATA

# 从 styles 目录获取可用样式列表
from styles import list_styles

# 从 lobster_research 导入样式加载器
from styles import load_style

# 导入统一报告生成入口
from generate_report import generate_report


def main():
    style_name = sys.argv[1] if len(sys.argv) > 1 else "orange"

    available = list_styles()
    if style_name not in available:
        print(f"❌ 样式 '{style_name}' 不存在")
        print(f"可用样式: {', '.join(available)}")
        sys.exit(1)

    print(f"🎨 测试样式: {style_name}")

    # 测试输出到 test/test_output/
    test_output_dir = os.path.join(TEST_DIR, "test_output")
    os.makedirs(test_output_dir, exist_ok=True)

    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join(test_output_dir, f"test_{style_name}_{ts}.html")

    # 调用 generate_report，传入目标路径（不走默认的 output/）
    result = generate_report(
        user_input="样式测试",
        data=TEST_DATA,
        output_format="html",
        output_path=html_path,
        style=style_name,
    )

    if result["success"]:
        html_path = result["path"]
        print(f"✅ 报告已生成: {html_path}")

        # 尝试生成 PDF
        try:
            import subprocess
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            pdf_path = html_path.replace(".html", ".pdf")
            html_url = "file:///" + html_path.replace("\\", "/")
            cmd = [
                chrome_path,
                "--headless", "--disable-gpu",
                f"--print-to-pdf={pdf_path}",
                "--print-to-pdf-no-header",
                html_url
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            if os.path.exists(pdf_path):
                size_kb = os.path.getsize(pdf_path) / 1024
                print(f"✅ PDF:  {pdf_path} ({size_kb:.1f} KB)")
            else:
                print(f"⚠️ PDF 生成失败")
        except Exception as e:
            print(f"⚠️ PDF 生成跳过: {e}")
    else:
        print(f"❌ 生成失败: {result.get('error')}")


if __name__ == "__main__":
    main()
