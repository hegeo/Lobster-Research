# -*- coding: utf-8 -*-
"""
🦞 龙虾测试工具 — 完整测试套件

用法:
    # 全部测试（dry-run 模式，只显示指令不执行）
    python -m test.runner

    # 全部测试（执行模式）
    python -m test.runner --execute

    # 指定测试类别
    python -m test.runner --category cli
    python -m test.runner --category style
    python -m test.runner --category collection  # 数据采集
    python -m test.runner --category generate    # 报告生成

    # 输出测试报告
    python -m test.runner --report

测试类别:
    cli        CLI 命令 -> 验证各子命令参数解析
    collection 数据采集 -> 测试 ticktime/akshare 数据获取
    style      样式测试 -> 10色 x 3布局 交叉验证
    generate   报告生成 -> 快速报告生成测试
    api        模块 API -> core.py/extend.py 函数测试
"""

import os, sys, json, argparse, subprocess, time, traceback
from datetime import datetime
from pathlib import Path

# ── 项目根 ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from modules.logger import get_logger

log = get_logger("test_runner")

# ═══════════════════════════════════════════════════════════════════════
#  测试基类
# ═══════════════════════════════════════════════════════════════════════


class TestCase:
    """单个测试用例"""

    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.passed = False
        self.duration = 0.0
        self.error = ""

    def run(self, execute: bool = False):
        """运行测试（子类重写）"""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════
#  CLI 命令测试
# ═══════════════════════════════════════════════════════════════════════


class CLITest(TestCase):
    """测试 CLI 子命令参数解析"""

    def __init__(self, name: str, cmd_args: list, expect_success: bool = True):
        super().__init__(name, "cli")
        self.cmd_args = cmd_args
        self.expect_success = expect_success

    def run(self, execute: bool = False):
        cmd = [sys.executable, "main.py"] + self.cmd_args
        cmd_str = " ".join(cmd)
        log.cmd(cmd_str)

        if not execute:
            log.info("  (dry-run, 未执行)")
            self.passed = True
            return

        start = time.time()
        try:
            result = subprocess.run(
                cmd, cwd=str(_PROJECT_ROOT), capture_output=True, text=True, timeout=30
            )
            self.duration = time.time() - start
            ok = result.returncode == 0 if self.expect_success else result.returncode != 0
            self.passed = ok
            if ok:
                log.ok(f"返回码={result.returncode}, 耗时={self.duration:.1f}s")
            else:
                self.error = result.stderr[:300]
                log.fail(f"返回码={result.returncode}: {self.error}")
        except subprocess.TimeoutExpired:
            self.duration = time.time() - start
            self.error = "超时 (30s)"
            log.fail("超时")
        except Exception as e:
            self.duration = time.time() - start
            self.error = str(e)
            log.fail(str(e))


# ═══════════════════════════════════════════════════════════════════════
#  数据采集测试
# ═══════════════════════════════════════════════════════════════════════


class CollectionTest(TestCase):
    """测试数据采集模块"""

    def __init__(self, name: str, code: str = "000063", steps: list = None):
        super().__init__(name, "collection")
        self.code = code
        self.steps = steps or ["quote", "kline"]

    def run(self, execute: bool = False):
        log.section(f"数据采集: {self.name} (code={self.code})")

        if execute:
            # 直接调用 ticktime 模块测试
            log.cmd(f"python -c 'from scripts.ticktime import get_realtime_stock; ...'")
            try:
                from scripts.ticktime import get_realtime_stock, get_history_kline
            except ImportError as e:
                log.fail(f"导入 ticktime 失败: {e}")
                self.error = str(e)
                return

        for step in self.steps:
            cmd_str = f"step={step}, code={self.code}"
            log.cmd(cmd_str)
            if not execute:
                log.info("  (dry-run)")
                self.passed = True
                continue

            start = time.time()
            try:
                if step == "quote":
                    data = get_realtime_stock(self.code)
                    ok = data and isinstance(data, dict) and "price" in str(data)
                elif step == "kline":
                    data = get_history_kline(self.code)
                    ok = data and isinstance(data, list) and len(data) > 0
                else:
                    ok = False
                self.duration = time.time() - start
                self.passed = ok
                if ok:
                    log.ok(f"{step}: 数据获取成功 ({self.duration:.1f}s)")
                else:
                    log.fail(f"{step}: 返回空数据")
                    self.error = f"{step}返回空"
            except Exception as e:
                self.duration = time.time() - start
                log.fail(f"{step}: {e}")
                self.error = str(e)


# ═══════════════════════════════════════════════════════════════════════
#  样式测试
# ═══════════════════════════════════════════════════════════════════════


class StyleTest(TestCase):
    """测试所有样式 × 渲染类型 × 布局组合"""

    STYLES = ["blue", "purple", "green", "indigo", "orange",
              "pink", "red", "yellow", "cyan", "brown"]
    COLOR_TYPES = ["solid", "gradient", "liquid"]
    LAYOUTS = ["rounded", "square", "minimal"]

    def __init__(self):
        super().__init__("style_matrix", "style")

    def run(self, execute: bool = False):
        log.section("样式测试: 10色 × 3渲染 × 3布局")
        total = len(self.STYLES) * len(self.COLOR_TYPES) * len(self.LAYOUTS)
        passed = 0

        for style in self.STYLES:
            for ct in self.COLOR_TYPES:
                for layout in self.LAYOUTS:
                    cmd_str = f"load_style('{style}', color_type='{ct}', layout='{layout}')"
                    log.cmd(cmd_str)
                    if not execute:
                        log.info("  (dry-run)")
                        passed += 1
                        continue

                    try:
                        from styles import load_style
                        css = load_style(style, color_type=ct, layout=layout)
                        has_body = "body {" in css
                        has_cover = ".cover {" in css
                        has_palette = f'[data-palette="{style}"]' in css
                        ok = len(css) > 5000 and has_body and has_cover and has_palette
                        if ok:
                            passed += 1
                            log.ok(f"[{style}/{ct}/{layout}] {len(css)} chars, "
                                   f"palette={has_palette}")
                        else:
                            log.fail(f"[{style}/{ct}/{layout}] "
                                     f"short={len(css)<5000}, body={has_body}, "
                                     f"palette={has_palette}")
                    except Exception as e:
                        log.fail(f"[{style}/{ct}/{layout}] {e}")

        self.passed = passed == total
        log.summary(passed, total)


# ═══════════════════════════════════════════════════════════════════════
#  报告生成测试
# ═══════════════════════════════════════════════════════════════════════


class GenerateTest(TestCase):
    """测试快速报告生成"""

    def __init__(self, name: str, code: str = "000063", name_cn: str = "中兴通讯",
                 cmd: str = "stock", style: str = "purple",
                 color_type: str = "liquid", layout: str = "rounded"):
        super().__init__(name, "generate")
        self.code = code
        self.name_cn = name_cn
        self.cmd = cmd
        self.style = style
        self.color_type = color_type
        self.layout = layout

    def run(self, execute: bool = False):
        # Phase 1: CLI 触发数据采集
        cmd_args = [self.cmd, "--code", self.code, "--name", self.name_cn,
                    "--style", self.style, "--color-type", self.color_type,
                    "--layout", self.layout]
        full_cmd = f"python main.py {' '.join(cmd_args)}"
        log.cmd(full_cmd)

        if not execute:
            log.info("  (dry-run)")
            self.passed = True
            return

        start = time.time()
        try:
            result = subprocess.run(
                [sys.executable, "main.py"] + cmd_args,
                cwd=str(_PROJECT_ROOT), capture_output=True, text=True, timeout=120
            )
            self.duration = time.time() - start
            ok = result.returncode == 0
            self.passed = ok
            if ok:
                # Find task_id from output
                import re
                task_match = re.search(r"任务\s+(\d{8}_\d{6})", result.stdout)
                task_id = task_match.group(1) if task_match else "?"
                log.ok(f"Phase 1 完成 (task={task_id}, {self.duration:.1f}s)")
            else:
                self.error = result.stderr[:300]
                log.fail(f"Phase 1 失败: {self.error}")
        except subprocess.TimeoutExpired:
            self.duration = time.time() - start
            self.error = "超时 (120s)"
            log.fail("超时")
        except Exception as e:
            self.duration = time.time() - start
            self.error = str(e)
            log.fail(str(e))


# ═══════════════════════════════════════════════════════════════════════
#  API / 模块测试
# ═══════════════════════════════════════════════════════════════════════


class APITest(TestCase):
    """测试核心模块 API"""

    def __init__(self):
        super().__init__("core_api", "api")

    def run(self, execute: bool = False):
        log.section("API 测试: core.py / extend.py / config")

        tests = [
            ("core.signal_emoji_change", "from modules.core import signal_emoji_change; signal_emoji_change(2.0) == '🟢'"),
            ("core.signal_emoji_change(negative)", "from modules.core import signal_emoji_change; signal_emoji_change(-2.0) == '🔴'"),
            ("extend.REPORT_TYPES", "from modules.extend import REPORT_TYPES; len(REPORT_TYPES) > 10"),
            ("extend.LOBSTER_QUOTES", "from modules.extend import LOBSTER_QUOTES; len(LOBSTER_QUOTES) > 5"),
            ("config.config.get", "from config.config import get; isinstance(get('output.report_style'), str)"),
            ("styles.list_styles", "from styles import list_styles; len(list_styles()) >= 10"),
        ]

        passed = 0
        for name, expr in tests:
            log.cmd(f"  {expr[:70]}...")
            if not execute:
                log.info("  (dry-run)")
                passed += 1
                continue
            try:
                result = eval(expr)
                ok = bool(result)
                if ok:
                    passed += 1
                    log.ok(f"{name}")
                else:
                    log.fail(f"{name}: 返回值={result}")
            except Exception as e:
                log.fail(f"{name}: {e}")

        self.passed = passed == len(tests)
        log.summary(passed, len(tests))


# ═══════════════════════════════════════════════════════════════════════
#  测试运行器
# ═══════════════════════════════════════════════════════════════════════


class TestRunner:
    """完整测试套件运行器"""

    CATEGORIES = {
        "cli":        ("CLI 命令测试", CLITest),
        "collection": ("数据采集测试", CollectionTest),
        "style":      ("样式测试",    StyleTest),
        "generate":   ("报告生成测试", GenerateTest),
        "api":        ("API 模块测试", APITest),
    }

    def __init__(self, execute: bool = False, categories: list = None,
                 report: bool = False):
        self.execute = execute
        self.categories = categories or list(self.CATEGORIES.keys())
        self.report = report
        self.results: list = []

    def _build_tests(self) -> list:
        """按类别构建测试用例列表"""
        tests = []

        if "cli" in self.categories:
            log.section("CLI 命令测试")
            cli_tests = [
                CLITest("stock-help",  ["stock", "--help"]),
                CLITest("market-help", ["market", "--help"]),
                CLITest("smart-help",  ["smart", "--help"]),
                CLITest("generate-help", ["generate", "--help"]),
                CLITest("list-cmd",    ["list"]),
                CLITest("stock-basic", ["stock", "--code", "000063", "--name", "中兴通讯",
                                        "--type", "quick", "--style", "purple", "--color-type", "liquid"]),
                CLITest("company-basic", ["company", "--code", "000157", "--name", "中联重科",
                                          "--type", "quick", "--style", "blue", "--color-type", "gradient"]),
                CLITest("market-basic", ["market", "--style", "green", "--color-type", "liquid"]),
                CLITest("smart-basic", ["smart", "--input", "中兴通讯行情", "--style", "purple",
                                        "--color-type", "liquid", "--layout", "minimal"]),
            ]
            for t in cli_tests:
                t.run(self.execute)
                tests.append(t)

        if "style" in self.categories:
            st = StyleTest()
            st.run(self.execute)
            tests.append(st)

        if "collection" in self.categories:
            log.section("数据采集测试")
            for code, name in [("000063", "中兴通讯"), ("000157", "中联重科")]:
                ct = CollectionTest(f"采集-{name}", code=code)
                ct.run(self.execute)
                tests.append(ct)

        if "generate" in self.categories:
            log.section("报告生成测试")
            gen_tests = [
                GenerateTest("stock-gen-purple", code="000063", name_cn="中兴通讯",
                            cmd="stock", style="purple", color_type="liquid"),
                GenerateTest("company-gen-blue", code="000157", name_cn="中联重科",
                             cmd="company", style="blue", color_type="gradient", layout="square"),
            ]
            for t in gen_tests:
                t.run(self.execute)
                tests.append(t)

        if "api" in self.categories:
            at = APITest()
            at.run(self.execute)
            tests.append(at)

        return tests

    def run(self):
        """执行所有测试"""
        start_time = datetime.now()
        log.section(f"🦞 龙虾测试套件 v1.0")
        log.info(f"  模式: {'执行' if self.execute else 'Dry-Run (仅显示指令)'}")
        log.info(f"  类别: {', '.join(self.categories)}")
        log.info(f"  开始: {start_time.strftime('%H:%M:%S')}")

        self.results = self._build_tests()

        # 汇总
        total = len(self.results)
        passed = sum(1 for t in self.results if t.passed)
        duration = (datetime.now() - start_time).total_seconds()

        log.section("测试汇总")
        log.info(f"  总数: {total} | 通过: {passed} | 失败: {total - passed}")
        log.info(f"  耗时: {duration:.1f}s")
        log.summary(passed, total)

        # 失败详情
        failed = [t for t in self.results if not t.passed]
        if failed:
            log.section("失败详情")
            for t in failed:
                log.fail(f"[{t.category}] {t.name}: {t.error or '未知错误'}")

        # 生成报告
        if self.report:
            self._write_report(start_time, duration)

        return passed == total

    def _write_report(self, start_time: datetime, duration: float):
        """生成 JSON 测试报告"""
        report = {
            "test_time": start_time.isoformat(),
            "duration_s": round(duration, 1),
            "mode": "execute" if self.execute else "dry-run",
            "categories": self.categories,
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for t in self.results if t.passed),
                "failed": sum(1 for t in self.results if not t.passed),
            },
            "results": [
                {
                    "name": t.name,
                    "category": t.category,
                    "passed": t.passed,
                    "duration_s": round(t.duration, 1),
                    "error": t.error or "",
                }
                for t in self.results
            ],
        }
        report_dir = _PROJECT_ROOT / "test" / "test_output"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"test_report_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        log.info(f"\n📄 测试报告: {report_path}")


# ═══════════════════════════════════════════════════════════════════════
#  CLI 入口
# ═══════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        prog="test.runner",
        description="🦞 龙虾测试工具 — 完整测试套件",
    )
    parser.add_argument("--execute", action="store_true",
                        help="实际执行测试（默认 dry-run 仅显示指令）")
    parser.add_argument("--category", "-c", default="all",
                        help="测试类别: cli/collection/style/generate/api/all (默认 all)")
    parser.add_argument("--report", action="store_true",
                        help="输出 JSON 测试报告")
    args = parser.parse_args()

    categories = list(TestRunner.CATEGORIES.keys()) if args.category == "all" else [args.category]
    for c in categories:
        if c not in TestRunner.CATEGORIES:
            print(f"❌ 未知类别: {c}")
            print(f"   可选: {', '.join(TestRunner.CATEGORIES.keys())}, all")
            sys.exit(1)

    runner = TestRunner(
        execute=args.execute,
        categories=categories,
        report=args.report,
    )
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
