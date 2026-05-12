# -*- coding: utf-8 -*-
"""
Lobster Logger - 龙虾日志系统

用法:
    from logs import get_logger
    log = get_logger("test_runner")
    log.info("开始测试...")
    log.cmd("python main.py stock --code 000063 --name 中兴通讯")  # 记录测试指令
    log.ok("测试通过")
    log.fail("测试失败")

日志文件: logs/lobster_YYYY-MM-DD.log (按天切割)
"""

import os, sys, logging, traceback
from datetime import datetime

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_GLOBAL_LEVEL = logging.DEBUG


class LobsterLogger:
    """龙虾日志器，封装 logging + 额外指令记录"""

    def __init__(self, name: str = "lobster"):
        self._name = name
        self._logger = logging.getLogger(f"🦞{name}")
        self._logger.setLevel(_GLOBAL_LEVEL)
        self._logger.handlers.clear()

        # ── 格式 ──
        _fmt_file = logging.Formatter(
            "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        _fmt_console = logging.Formatter(
            "%(levelname)s | %(message)s"
        )

        # ── 文件 Handler ──
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(_LOG_DIR, f"lobster_{today}.log")
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(_fmt_file)
        self._logger.addHandler(fh)

        # ── 控制台 Handler ──
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(_fmt_console)
        self._logger.addHandler(ch)

    def _log(self, level: int, msg: str):
        self._logger.log(level, msg)

    # ── 标准级别 ──
    def debug(self, msg: str):   self._log(logging.DEBUG, msg)
    def info(self, msg: str):    self._log(logging.INFO, msg)
    def warn(self, msg: str):    self._log(logging.WARNING, f"⚠️  {msg}")
    def error(self, msg: str):   self._log(logging.ERROR, f"❌  {msg}")
    def exception(self, msg: str):
        self._log(logging.ERROR, f"💥  {msg}")
        self._log(logging.DEBUG, traceback.format_exc())

    # ── 专用方法 ──
    def cmd(self, command: str):
        """记录测试指令（带标记）"""
        self._log(logging.INFO, f"━━━ 🧪 指令: {command}")

    def ok(self, msg: str):
        """测试通过"""
        self._log(logging.INFO, f"  ✅ {msg}")

    def fail(self, msg: str):
        """测试失败"""
        self._log(logging.ERROR, f"  ❌ {msg}")

    def section(self, title: str):
        """章节分隔"""
        self._log(logging.INFO, "")
        self._log(logging.INFO, f"{'='*60}")
        self._log(logging.INFO, f"  {title}")
        self._log(logging.INFO, f"{'='*60}")

    def summary(self, passed: int, total: int):
        """测试汇总"""
        ratio = f"{passed}/{total}"
        if passed == total:
            self._log(logging.INFO, f"\n🎉 全部通过 ({ratio})")
        else:
            self._log(logging.WARNING, f"\n⚠️  通过 {ratio} | 失败 {total - passed}")


# ── 全局默认实例（模块级单例） ──
_DEFAULT = LobsterLogger("lobster")


def get_logger(name: str = "lobster") -> LobsterLogger:
    """获取（或创建）一个日志器"""
    return LobsterLogger(name)


def set_global_level(level: int):
    """设置全局日志级别"""
    global _GLOBAL_LEVEL
    _GLOBAL_LEVEL = level
