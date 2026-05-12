# -*- coding: utf-8 -*-
"""
龙虾调研助手 - 代码驱动主入口
=====================================
核心设计理念：
  【代码】负责：任务创建 → 工具调用 → 数据写入 JSON → 状态跟踪
  【Agent】负责：读取 JSON → 搜索补充资料 → 填充分析内容 → 生成报告

使用方式：
  # 个股分析 / 企业研报
  python main.py stock --code 000063 --name 中兴通讯 --type qiye_baogao

  # 大盘日报
  python main.py market

  # 行业研报（使用 smart 自动匹配领域模板）
  python main.py smart --input "AI芯片行业研报"

  # 持仓诊断（输入持仓数据文件）
  python main.py portfolio --file portfolio.json

  # 快速选股
  python main.py screener

  # 查看任务状态
  python main.py status --task-id <task_id>

  # 列出所有任务
  python main.py list

任务文件夹结构（output/tasks/<task_id>/）：
  0_meta_task_info.json            ← 任务元信息 + 状态机
  0_portfolio_img__parse.json      ← 持仓图片解析结果
  0_portfolio_fresh.json           ← 持仓数据（刷新行情后）
  1_market_index_tick.json         ← 大盘指数数据
  1_market_status_sina.json        ← 大盘整体状况
  1_market_akshare_macro.json      ← AKShare 结构化数据
  2_stock_quote_realtime.json      ← 实时行情数据
  2_stock_kline_indicator.json     ← K线 + 技术指标
  2_stock_info_detail.json         ← 个股详细资料（证券之星）
  3_news_daily_all.json            ← 当日新闻快讯
  4_search_keyword_*.json          ← 搜索结果（多个关键词）
  4_search_batch_summary.json      ← 批量搜索汇总结果
  5_agent_briefing.md              ← Agent 工作说明
  5_agent_report_input.json        ← Agent 整合后的输入数据（Agent填写）
  report.html                      ← 最终报告
  report.pdf                       ← 最终报告PDF
"""

import sys
import os
import io
import json
import argparse
import subprocess
import re
from datetime import datetime
from typing import Optional

from config.config import get as get_user_config

# 龙虾日志
from modules.logger import get_logger as _get_logger_main
_log = _get_logger_main("main")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 确保项目根目录在 path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from scripts.task_runner import TaskRunner

# ═══════════════════════════════════════════════════════════
# 配置加载 — 从 main.json 统一读取（Smart 路由 + CLI 子命令）
# ═══════════════════════════════════════════════════════════
# CLI 子命令（stock/company/market/portfolio/screener）
# 与 smart 路由共用同一份 main.json，通过 domain id 索引。
# CLI 专属字段（在 domain 条目中）：
#   cli_default_type     → 任务 report_type 默认值
#   cli_prompt_template  → CLI 使用的 prompt 模板（不区分 quick/deep）
# 注意：agent_hint 在 CLI 中使用 deep_hint（最详尽的说明）
#
# Smart 路由匹配逻辑（双层关键词）：
#   Layer 1: 匹配 domain（领域关键词）→ 确定用户在问什么
#   Layer 2: 匹配 tier_tag（输出类型关键词）→ 确定输出格式
#   规则：domain 命中但 tier_tag 未命中 → 默认走 news 快讯
#   特殊：news_defaults 关键词直接走快讯（不需要 domain）

def _load_smart_config() -> dict:
    """从 main.json 加载路由配置，失败时返回空配置"""
    config_path = os.path.join(PROJECT_ROOT, "main.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  ⚠️ 加载 main.json 失败: {e}")
    return {"tier_tags": {}, "domains": [], "news_defaults": {}}

SMART_CONFIG = _load_smart_config()


def _load_user_config() -> dict:
    """从 config/config.json 加载用户偏好配置，失败时返回空 dict"""
    try:
        from config.config import get
        return get() or {}
    except Exception as e:
        print(f"  ⚠️ 加载用户配置失败: {e}")
        return {}


def _style_from_config(user_prefs: dict, key: str, fallback: str) -> str:
    """
    从 config.json output 节读取样式值。
    优先级：config.json > fallback
    """
    try:
        return user_prefs.get("output", {}).get(key, fallback) or fallback
    except Exception:
        return fallback


# CLI 子命令对应的 domain id 映射（"命令名" → "domain id"）
# company 和 stock 都对应 main.json 中各自的 domain，
# 但 company 有更详细的 search_templates（参见 company domain 配置）
_CLI_DOMAIN_MAP = {
    "stock":     "stock",
    "company":   "company",
    "market":    "market",
    "portfolio": "portfolio",
    "screener":  "screener",
}

# 从 main.json domains 列表建立 id → domain 索引
_DOMAIN_INDEX: dict = {d["id"]: d for d in SMART_CONFIG.get("domains", [])}


def _build_report_types() -> dict:
    """
    从 main.json 动态构建 REPORT_TYPES。
    兼容旧接口，将 domain 字段映射为 create_task/run_task 期望的格式：
      label, default_type, prompt_template, steps, search_templates, agent_hint
    """
    result = {}
    for cmd, domain_id in _CLI_DOMAIN_MAP.items():
        d = _DOMAIN_INDEX.get(domain_id)
        if not d:
            continue
        result[cmd] = {
            "label":             d.get("label", cmd),
            "default_type":      d.get("cli_default_type", f"{cmd}_report"),
            "prompt_template":   d.get("cli_prompt_template") or d.get("deep_template") or "",
            "steps":             d.get("steps", ["search"]),
            "search_templates":  d.get("search_templates", []),
            # CLI 模式使用 deep_hint 作为 agent_hint（最详尽）
            "agent_hint":        d.get("deep_hint") or d.get("quick_hint") or "",
        }
    return result


REPORT_TYPES = _build_report_types()

# 预留步骤（待实现，已注册路由和 stub 方法）
# 触发时自动创建占位文件，不会中断流程
RESERVED_STEPS = frozenset({
    "news_market_flash",
    "search_research",
    "search_market_batch",
    "search_stock_batch",
    "emu_portfolio",
    "emu_operation",
    "emu_reflection",
})


def smart_match(user_input: str, code: str = "", name: str = "", topic: str = "") -> dict:
    """
    双层关键词匹配路由。

    匹配流程（重要：领域优先于纯新闻词）：
      1. 匹配 domain（领域）→ 长词优先，无领域匹配时才退到 news_defaults
      2. 匹配 tier_tag（输出类型）:
         - deep 关键词  → 研报（需有 deep_template）
         - quick 关键词 → 快报（需有 quick_template）
         - "报告" 无修饰 → quick 优先（比 deep 轻量）
      3. domain 命中的默认 → news 快讯
      4. domain 未命中 + news_defaults 命中 → news 纯快讯
      5. 都没命中 → reject
    """
    result = {
        "tier": "reject",
        "domain": None,
        "matched_domain_keyword": None,
        "matched_tier_tag": None,
        "code": code,
        "name": name,
        "topic": topic,
    }

    if not user_input:
        return result

    text = user_input.lower()

    # 提取股票代码（6位纯数字）
    code_match = re.search(r'(?<!\d)(\d{6})(?!\d)', user_input)
    if code_match and not code:
        result["code"] = code_match.group(1)

    # ── Step 1: 匹配 domain（长词优先）──
    domains = SMART_CONFIG.get("domains", [])
    tier_tags = SMART_CONFIG.get("tier_tags", {})
    quick_tags = [t.lower() for t in tier_tags.get("quick", [])]
    deep_tags  = [t.lower() for t in tier_tags.get("deep", [])]

    best_domain = None
    best_domain_score = 0
    best_domain_kw = None

    # 先统计每domain在输入中的关键词命中总数
    hits_per_domain = {}
    for domain in domains:
        did = domain["id"]
        hits_per_domain[did] = 0
        for kw in domain.get("keywords", []):
            if kw.lower() in text:
                hits_per_domain[did] += 1

    # 再遍历决胜：长词优先，同长按域内命中数
    for domain in domains:
        did = domain["id"]
        for kw in domain.get("keywords", []):
            if kw.lower() in text:
                if len(kw) > best_domain_score:
                    best_domain = domain
                    best_domain_score = len(kw)
                    best_domain_kw = kw
                elif len(kw) == best_domain_score and best_domain:
                    if hits_per_domain.get(did, 0) > hits_per_domain.get(best_domain["id"], 0):
                        best_domain = domain
                        best_domain_kw = kw

    if best_domain:
        # domain 命中 → 在领域内判断 tier
        result["domain"] = best_domain
        result["matched_domain_keyword"] = best_domain_kw
        result["topic"] = topic or user_input.strip()

        # 先查 deep（更深度的关键词优先）
        for tag in deep_tags:
            if tag in text:
                if best_domain.get("deep_template"):
                    result["tier"] = "deep"
                    result["matched_tier_tag"] = tag
                    return result
                break

        # 再查 quick
        for tag in quick_tags:
            if tag in text:
                if best_domain.get("quick_template"):
                    result["tier"] = "quick"
                    result["matched_tier_tag"] = tag
                    return result
                break

        # "报告" 单独处理：无配套的 deep/quick 修饰词时默认 quick
        if "报告" in text:
            if best_domain.get("quick_template"):
                result["tier"] = "quick"
                result["matched_tier_tag"] = "报告"
                return result
            elif best_domain.get("deep_template"):
                result["tier"] = "deep"
                return result

        # 领域特定启发式：company domain + "分析" → deep
        if best_domain["id"] == "company" and "分析" in text:
            if best_domain.get("deep_template"):
                result["tier"] = "deep"
                result["matched_tier_tag"] = "分析"
                return result

        # 领域命中但无 tier 关键词 → 默认 news
        result["tier"] = "news"
        return result

    # ── Step 2: domain 未命中 → 检查 news_defaults（纯新闻词）──
    news_defaults = SMART_CONFIG.get("news_defaults", {})
    news_keywords = news_defaults.get("keywords", [])
    for kw in news_keywords:
        if kw.lower() in text:
            result["tier"] = "news"
            result["news_hint"] = news_defaults.get("hint", "")
            result["topic"] = topic or user_input.strip()
            return result

    # ── Step 2.5: 有股票代码但无 domain 匹配 → 退到 stock domain ──
    if result.get("code"):
        stock_domain = next((d for d in domains if d["id"] == "stock"), None)
        if stock_domain:
            result["domain"] = stock_domain
            result["matched_domain_keyword"] = "code:" + result["code"]
            result["topic"] = topic or user_input.strip()
            # 在 stock domain 下重新判断 tier
            for tag in deep_tags:
                if tag in text:
                    result["tier"] = "deep"
                    result["matched_tier_tag"] = tag
                    return result
            for tag in quick_tags:
                if tag in text:
                    result["tier"] = "quick"
                    result["matched_tier_tag"] = tag
                    return result
            if "报告" in text:
                result["tier"] = "quick"
                result["matched_tier_tag"] = "报告"
                return result
            result["tier"] = "news"
            return result

    # ── Step 2.75: 无代码无domain但有tier关键词→默认stock domain──
    # 处理"中联重科研报""给我一份中联重科的报告"等无领域关键词但有意图的输入
    stock_domain = next((d for d in domains if d["id"] == "stock"), None)
    all_tier_words = quick_tags + deep_tags + ["报告"]
    if stock_domain:
        for tw in all_tier_words:
            if tw in text:
                result["domain"] = stock_domain
                result["matched_domain_keyword"] = "tier:" + tw
                result["topic"] = topic or user_input.strip()
                # 重新判断tier
                if tw in deep_tags and stock_domain.get("deep_template"):
                    result["tier"] = "deep"
                elif tw in quick_tags and stock_domain.get("quick_template"):
                    result["tier"] = "quick"
                elif tw == "报告":
                    result["tier"] = "quick" if stock_domain.get("quick_template") else "news"
                else:
                    result["tier"] = "news"
                result["matched_tier_tag"] = tw
                return result

    # ── Step 3: 都没命中 → reject ──
    return result


# ═══════════════════════════════════════════════════════════
# 任务状态管理
# ═══════════════════════════════════════════════════════════
class TaskState:
    PENDING   = "pending"
    RUNNING   = "running"
    DATA_DONE = "data_done"    # 数据采集完成，等 Agent 填充
    AGENT_DONE = "agent_done"  # Agent 填充完成，等生成报告
    DONE      = "done"
    FAILED    = "failed"

    STEP_STATES = {
        "quote":        "pending",
        "kline":        "pending",
        "master":       "pending",
        "market_index": "pending",
        "search":       "pending",
    }


def load_prompt_template(template_name: str) -> dict:
    """
    从 prompts/json/ 加载提示词模板
    返回模板数据字典，文件不存在则返回空 dict
    """
    if not template_name:
        return {}
    path = os.path.join(PROJECT_ROOT, "prompts", "json", template_name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def create_task(cmd: str, args: argparse.Namespace) -> dict:
    """创建新任务，返回任务元信息"""
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    cfg = REPORT_TYPES[cmd]
    today = datetime.now().strftime("%Y-%m-%d")

    # 加载 prompt 模板
    prompt_tpl = load_prompt_template(cfg.get("prompt_template", ""))

    # 加载用户配置（含投资画像）
    user_prefs = _load_user_config()

    # 填充搜索关键词模板（命令自带的）
    tpl_vars = {
        "name":  getattr(args, "name", ""),
        "code":  getattr(args, "code", ""),
        "topic": getattr(args, "topic", getattr(args, "name", "")),
        "date":  today,
    }

    # screener 未指定 topic 时，根据投资风格自动派生选股方向
    if cmd == "screener" and not tpl_vars["topic"]:
        style = user_prefs.get("user", {}).get("investment_style", "")
        style_topic_map = {
            "value":  "蓝筹 低估值 高股息 白马股",
            "growth": "高科技 高成长 新兴 景气赛道",
            "band":   "活跃 波段 资金轮动 箱体",
            "trend":  "趋势 上升通道 资金流入",
        }
        derived = style_topic_map.get(style, "低估值蓝筹")
        tpl_vars["topic"] = derived
        _log.info(f"   🎯 投资风格《{style}》→ 自动派生选股主题: {derived}")

    search_queries = [q.format(**tpl_vars) for q in cfg["search_templates"]]

    # 从 prompt 模板追加 recommendedKeywords（智能去重）
    # 策略：只保留与 search_templates 不重叠的关键词，且最多追加 2 个
    kw_set = set(q.format(**tpl_vars) for q in cfg["search_templates"])
    _template_words = set()
    for q in search_queries:
        _template_words.update(q.split())
    added = 0
    for kw in prompt_tpl.get("recommendedKeywords", []):
        if added >= 2:
            break
        kw_formatted = f"{kw} {today}"
        if kw_formatted in kw_set:
            continue
        # 如果新关键词的核心词（去掉日期）有 70%+ 已在模板关键词中出现，跳过
        kw_core = set(kw.split())
        overlap = len(kw_core & _template_words) / len(kw_core) if kw_core else 0
        if overlap >= 0.7:
            continue
        search_queries.append(kw_formatted)
        kw_set.add(kw_formatted)
        added += 1

    # 构造 keyword_groups（批量搜索模式）
    # 从 prompt 模板的 recommendedDataSources 提取数据源
    data_sources = prompt_tpl.get("recommendedDataSources", [])
    keyword_groups = []

    if data_sources:
        # 有数据源：构造"关键词组 × 数据源组"
        # 把推荐数据源拆成组
        source_domains = []
        for src in data_sources:
            # 常见财经数据源域名映射
            src_domain_map = {
                "东方财富": "eastmoney.com",
                "同花顺": "10jqka.com.cn",
                "Wind": "wind.com.cn",
                "新浪财经": "finance.sina.com.cn",
                "证券时报": "stcn.com",
                "上海证券报": "cnstock.com",
                "财新": "caixin.com",
                "36氪": "36kr.com",
                "雪球": "xueqiu.com",
            }
            domain = src_domain_map.get(src, src.lower())
            source_domains.append(domain)

        # 所有搜索关键词分成一组，附带所有数据源
        keyword_groups.append({
            "keywords": search_queries,
            "sources": source_domains,
            "max_per_source": 8,
            "group_label": f"{cfg['label']}_数据源搜索",
        })

    # 无论是否有数据源，都加一个通用关键词组（用标准引擎搜索）
    keyword_groups.append({
        "keywords": search_queries,
        "max_per_keyword": 12,
        "group_label": f"{cfg['label']}_通用搜索",
    })

    is_quick = getattr(args, "type", None) == "quick"
    steps_list = cfg.get("quick_steps", cfg["steps"]) if is_quick else cfg["steps"]

    # 从 config.json 读取输出样式（统一优先级：CLI参数 > config.json > 模板默认 > 代码默认）
    cfg_style      = _style_from_config(user_prefs, "report_style", prompt_tpl.get("style", "blue"))
    cfg_color_type = _style_from_config(user_prefs, "color_type", prompt_tpl.get("color_type", "liquid"))
    cfg_layout     = _style_from_config(user_prefs, "layout", prompt_tpl.get("layout", "rounded"))

    meta = {
        "task_id":     task_id,
        "cmd":         cmd,
        "report_type": getattr(args, "type", None) or cfg["default_type"],
        "label":       cfg["label"],
        "created_at":  datetime.now().isoformat(),
        "date":        today,
        "status":      TaskState.PENDING,
        "args": {
            "code":   getattr(args, "code", ""),
            "name":   getattr(args, "name", ""),
            "topic":  tpl_vars.get("topic", getattr(args, "topic", "")),
            "style":  getattr(args, "style", cfg_style),
            "color_type": getattr(args, "color_type", cfg_color_type),
            "layout": getattr(args, "layout", cfg_layout),
            "output": getattr(args, "output", "output"),
            "portfolio_file": getattr(args, "file", ""),
        },
        "steps": {step: "pending" for step in steps_list},
        "search_queries": search_queries,       # 旧模式兼容
        "keyword_groups": keyword_groups,       # 新模式：批量搜索参数
        "files": {},     # 记录各步骤生成的文件路径
        "agent_hint": cfg["agent_hint"],
        # prompt 模板数据，task_runner 用来注入 5_agent_briefing
        "prompt_template": prompt_tpl,
        "report_path": "",
        "error": "",
        "user_prefs": user_prefs,       # 注入用户画像
    }
    _log.info(f"📁 创建任务 {task_id} [{cmd}] '{getattr(args, 'topic', '') or getattr(args, 'name', '')}'")
    _log.info(f"   🎨 样式: {cfg_style}/{cfg_color_type}/{cfg_layout}")
    return meta, task_id


def load_meta(task_dir: str) -> dict:
    meta_path = os.path.join(task_dir, "0_meta_task_info.json")
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


def save_meta(task_dir: str, meta: dict):
    meta_path = os.path.join(task_dir, "0_meta_task_info.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════
# 打印工具
# ═══════════════════════════════════════════════════════════
def banner(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def step_ok(step: str, detail: str = ""):
    mark = detail[:80] if detail else ""
    print(f"  ✅ [{step}] {mark}")

def step_warn(step: str, detail: str = ""):
    print(f"  ⚠️  [{step}] {detail[:80]}")

def step_fail(step: str, detail: str = ""):
    print(f"  ❌ [{step}] {detail[:120]}")


# ═══════════════════════════════════════════════════════════
# 核心流程：运行任务
# ═══════════════════════════════════════════════════════════
def run_task(cmd: str, args: argparse.Namespace):
    meta, task_id = create_task(cmd, args)
    cfg = REPORT_TYPES[cmd]

    # 建立任务文件夹
    task_dir = os.path.join(PROJECT_ROOT, meta["args"]["output"], "tasks", task_id)
    os.makedirs(task_dir, exist_ok=True)
    meta["task_dir"] = task_dir
    meta["status"] = TaskState.RUNNING
    save_meta(task_dir, meta)
    _log.info(f"▶ run_task 启动 | 目录: {task_dir}")

    banner(f"🦞 龙虾调研 V3 ｜ {meta['label']} ｜ 任务 {task_id}")
    print(f"  任务目录：{task_dir}")

    runner = TaskRunner(task_dir, meta, PROJECT_ROOT)

    # ── Step 1: 数据采集（代码驱动，无 Agent 介入）──────────
    print(f"\n【Phase 1】数据采集（代码驱动）")

    is_quick = getattr(args, "type", None) == "quick"
    steps = cfg.get("quick_steps", cfg["steps"]) if is_quick else cfg["steps"]
    _log.info(f"▶ Phase 1 开始 | 步骤: {steps}")

    for step in steps:
        try:
            _log.info(f"  ▶ 执行步骤: {step}")
            if step == "quote":
                ok, path = runner.run_quote(meta["args"]["code"])
                meta["steps"]["quote"] = "done" if ok else "failed"
                if ok:
                    meta["files"]["quote"] = path
                    step_ok("quote", f"实时行情 → {os.path.basename(path)}")
                else:
                    step_warn("quote", "实时行情获取失败，将使用空数据")

            elif step == "kline":
                ok, path = runner.run_kline(meta["args"]["code"])
                meta["steps"]["kline"] = "done" if ok else "failed"
                if ok:
                    meta["files"]["kline"] = path
                    step_ok("kline", f"K线+技术指标 → {os.path.basename(path)}")
                else:
                    step_warn("kline", "K线数据获取失败")

            elif step == "master":
                ok, path = runner.run_master(meta["args"]["code"])
                meta["steps"]["master"] = "done" if ok else "failed"
                if ok:
                    meta["files"]["master"] = path
                    step_ok("master", f"个股详细资料 → {os.path.basename(path)}")
                else:
                    step_warn("master", "个股详细资料获取失败")

            elif step == "market_index":
                ok, path = runner.run_market_index()
                meta["steps"]["market_index"] = "done" if ok else "failed"
                if ok:
                    meta["files"]["market_index"] = path
                    step_ok("market_index", f"大盘指数 → {os.path.basename(path)}")
                else:
                    step_warn("market_index", "大盘数据获取失败")

            elif step == "market_state":
                ok, path = runner.run_market_state()
                meta["steps"]["market_state"] = "done" if ok else "failed"
                if ok:
                    meta["files"]["market_state"] = path
                    step_ok("market_state", f"大盘整体状况 → {os.path.basename(path)}")
                else:
                    step_warn("market_state", "大盘整体状况获取失败，可手动补充")

            elif step == "news_stock_flash":
                ok, path = runner.run_news_stock_flash(meta["args"]["code"])
                meta["steps"]["news_stock_flash"] = "done" if ok else "failed"
                if ok:
                    meta["files"]["news_stock_flash"] = path
                    step_ok("news_stock_flash", f"个股新闻快讯 → {os.path.basename(path)}")
                else:
                    step_warn("news_stock_flash", "个股新闻获取失败，将使用空数据")

            elif step == "portfolio":
                portfolio_file = meta["args"].get("portfolio_file", "")
                ok, path = runner.run_portfolio(portfolio_file if portfolio_file else None)
                meta["steps"]["portfolio"] = "done" if ok else "failed"
                if ok:
                    meta["files"]["portfolio"] = path
                    step_ok("portfolio", f"持仓诊断 → {os.path.basename(path)}")
                else:
                    step_warn("portfolio", "持仓数据获取失败")

            elif step == "search":
                # 优先使用批量搜索模式（关键词组 × 数据源组）
                keyword_groups = meta.get("keyword_groups", [])
                if keyword_groups:
                    paths = runner.run_batch_search(keyword_groups)
                    meta["steps"]["search"] = "done" if paths else "failed"
                    meta["files"]["search"] = paths
                    step_ok("search", f"批量搜索完成（{len(keyword_groups)} 组）")
                else:
                    # 回退到旧模式
                    paths = runner.run_search(meta["search_queries"])
                    meta["steps"]["search"] = "done" if paths else "failed"
                    meta["files"]["search"] = paths
                    step_ok("search", f"搜索完成 {len(paths)} 个关键词")

            elif step in RESERVED_STEPS:
                ok, path = runner.run_reserved_step(step)
                meta["steps"][step] = "done" if ok else "failed"
                if ok:
                    meta["files"][step] = path
                    step_ok(step, f"{os.path.basename(path)}（预留占位，待实现）")
                else:
                    step_warn(step, f"{step} 生成占位文件失败")

        except Exception as e:
            meta["steps"][step] = "failed"
            step_fail(step, str(e))

        save_meta(task_dir, meta)

    meta["status"] = TaskState.DATA_DONE
    save_meta(task_dir, meta)
    _log.info(f"✅ Phase 1 完成 | 任务 {task_id} | status=DATA_DONE | 步骤状态: {meta['steps']}")

    # ── Step 2: 生成 Agent 指引文件 ──────────────────────────
    runner.write_agent_briefing()

    # ── Alone 模式检查 ──
    run_mode = get_user_config("system.run_mode", "skill")
    _log.info(f"  ▶ run_mode={run_mode}")
    if run_mode == "alone":
        from scripts.generate_alonemode import run_alone_mode
        alone_result = run_alone_mode(task_dir, meta, PROJECT_ROOT)
        if alone_result.get("success"):
            meta["status"] = TaskState.DONE
            if alone_result.get("html_path"):
                meta["html_path"] = alone_result["html_path"]
            if alone_result.get("pdf_path"):
                meta["report_path"] = alone_result["pdf_path"]
            save_meta(task_dir, meta)
            _log.info(f"✅ Alone 模式完成 | 任务 {task_id} | HTML: {alone_result.get('html_path','')} | PDF: {alone_result.get('pdf_path','')}")
            print(f"\n{'─'*60}")
            print(f"  ✅ Alone 模式完成")
            print(f"{'─'*60}\n")
            print(f"  任务ID: {task_id}")
            if alone_result.get("tool_called"):
                print(f"  📝 报告数据: 5_agent_report_input.json")
            if alone_result.get("html_path"):
                print(f"  🌐 HTML: {alone_result['html_path']}")
            if alone_result.get("pdf_path"):
                print(f"  📄 PDF:  {alone_result['pdf_path']}")
            print()
            return task_id, task_dir
        else:
            _log.warn(f"⚠️ Alone 模式失败: {alone_result.get('error', '未知错误')}，降级为 skill 模式")
            print(f"\n  ⚠️ Alone 模式失败: {alone_result.get('error', '未知错误')}")
            print(f"  降级为 skill 模式，继续打印 Agent 指导")

    # ── 打印 Agent 操作指南 ──────────────────────────────────
    _log.info(f"📋 Phase 2 已就绪 | 任务 {task_id} | 等待 Agent 填充 5_agent_report_input.json")
    print(f"\n{'─'*60}")
    print(f"【Phase 2】Agent 整合阶段 ← 现在需要你介入")
    print(f"{'─'*60}")
    print(f"\n  任务目录：{task_dir}")
    print(f"\n  已生成数据文件：")
    for key, val in meta["files"].items():
        if isinstance(val, list):
            for p in val:
                print(f"    📄 {os.path.basename(p)}")
        elif val:
            print(f"    📄 {os.path.basename(val)}")

    print(f"\n  📋 Agent 任务说明：")
    print(f"    🔹 请先阅读 5_agent_briefing.md，里面有完整的工作流程、数据结构说明和填写规范")
    print(f"    🔹 读取各数据文件 → 补充搜索 → 按大纲组织内容 → 填写 5_agent_report_input.json")
    print(f"    📌 {meta['agent_hint']}")
    print(f"\n  目标输出文件：")
    print(f"    📝 {task_dir}\\5_agent_report_input.json")
    print(f"\n  ⚡ Agent 完成填充后，运行：")
    print(f"    python main.py generate --task-id {task_id}")
    print(f"\n{'─'*60}\n")

    return task_id, task_dir


def run_generate(task_id: str, base_output: str = "output"):
    """Phase 3：读取 5_agent_report_input.json，生成最终报告（HTML + PDF）"""
    task_dir = os.path.join(PROJECT_ROOT, base_output, "tasks", task_id)
    if not os.path.exists(task_dir):
        _log.error(f"找不到任务目录：{task_dir}")
        print(f"❌ 找不到任务目录：{task_dir}")
        return

    meta = load_meta(task_dir)
    agent_input_path = os.path.join(task_dir, "5_agent_report_input.json")
    _log.info(f"📄 Generate 任务 {task_id} (类型: {meta.get('report_type','?')})")

    if not os.path.exists(agent_input_path):
        _log.error(f"找不到 Agent 输入文件：{agent_input_path}")
        print(f"❌ 找不到 Agent 输入文件：{agent_input_path}")
        print(f"   请先让 Agent 填充 5_agent_report_input.json 再运行 generate")
        return

    banner(f"🦞 Phase 3：生成报告 ｜ 任务 {task_id}")
    _log.info(f"▶ Phase 3 开始: generate_report({task_id})")

    runner = TaskRunner(task_dir, meta, PROJECT_ROOT)
    ok, result = runner.generate_report(agent_input_path)

    if ok:
        meta["status"] = TaskState.DONE
        meta["report_path"] = result.get("pdf_path", "")
        meta["html_path"] = result.get("html_path", "")
        save_meta(task_dir, meta)
        _log.info(f"✅ 报告生成成功 [{meta.get('report_type','?')}] {result.get('pdf_path','')}")
        print(f"\n  ✅ 报告生成成功！")
        print(f"     PDF:  {result.get('pdf_path', '')}")
        print(f"     HTML: {result.get('html_path', '')}")
        print(f"\n  📦 交付指引（铁律 5/7）：")
        print(f"     1. preview_url(url=\"{result.get('html_path', '')}\")")
        print(f"     2. deliver_attachments(attachments=[\"{result.get('pdf_path', '')}\", \"{result.get('html_path', '')}\"])")
        print(f"     3. 只写一句话：\"✅ 报告已生成，HTML 已在右侧预览，PDF/HTML 已作为附件发送。\"")
        print(f"\n  ⚠️ 禁止写摘要/总结/回顾 — 交付文件本身就是结果")
    else:
        meta["status"] = TaskState.FAILED
        meta["error"] = result.get("error", "未知错误")
        save_meta(task_dir, meta)
        _log.error(f"报告生成失败: {result.get('error', '未知错误')}")
        print(f"\n  ❌ 报告生成失败")
        print(f"     原因：{result.get('error', '未知错误')}")


def cmd_status(task_id: str, base_output: str = "output"):
    """查看任务状态"""
    task_dir = os.path.join(PROJECT_ROOT, base_output, "tasks", task_id)
    if not os.path.exists(task_dir):
        print(f"❌ 找不到任务：{task_id}")
        return
    meta = load_meta(task_dir)
    print(f"\n任务 {task_id}")
    print(f"  类型：{meta['label']}")
    print(f"  状态：{meta['status']}")
    print(f"  创建：{meta['created_at']}")
    print(f"  目录：{task_dir}")
    print(f"  步骤：")
    for step, state in meta["steps"].items():
        icon = "✅" if state == "done" else ("❌" if state == "failed" else "⏳")
        print(f"    {icon} {step}: {state}")
    if meta.get("report_path"):
        print(f"  报告：{meta['report_path']}")


def cmd_list(base_output: str = "output"):
    """列出所有任务"""
    tasks_dir = os.path.join(PROJECT_ROOT, base_output, "tasks")
    if not os.path.exists(tasks_dir):
        print("暂无任务记录")
        return
    tasks = sorted(os.listdir(tasks_dir), reverse=True)
    print(f"\n{'任务ID':<20} {'类型':<16} {'状态':<12} {'创建时间'}")
    print("─" * 70)
    for t in tasks[:20]:
        td = os.path.join(tasks_dir, t)
        meta_path = os.path.join(td, "0_meta_task_info.json")
        if not os.path.exists(meta_path):
            continue
        try:
            m = json.load(open(meta_path, encoding="utf-8"))
            icon = {"done": "✅", "data_done": "📊", "running": "🔄", "failed": "❌"}.get(m["status"], "⏳")
            print(f"{t:<20} {m['label'][:14]:<16} {icon} {m['status']:<10} {m['created_at'][:19]}")
        except:
            pass


# ═══════════════════════════════════════════════════════════
# Smart 命令：自然语言 → 自动路由 → 执行
# ═══════════════════════════════════════════════════════════
def cmd_smart(user_input: str, code: str = "", name: str = "", topic: str = "",
              style: str = "blue", color_type: str = "liquid", layout: str = "rounded",
              base_output: str = "output"):
    """
    Smart 模式入口：接收自然语言，自动匹配路由，执行对应流程。
    输出 JSON 到 stdout，Agent 读取后决定下一步。
    """
    # Step 1: 匹配路由（双层关键词）
    result = smart_match(user_input, code=code, name=name, topic=topic)
    tier = result["tier"]
    domain = result["domain"]
    code = result.get("code", "")
    name = result.get("name", "")
    topic = result.get("topic", "")

    _log.info(f"🔍 Smart 匹配: '{user_input}' → tier={tier} domain={result.get('matched_domain_keyword','?')}")

    output = {
        "user_input": user_input,
        "tier": tier,
        "domain_id": domain["id"] if domain else None,
        "domain_label": domain["label"] if domain else None,
        "matched_domain_keyword": result.get("matched_domain_keyword"),
        "matched_tier_tag": result.get("matched_tier_tag"),
        "code": code,
        "name": name,
        "topic": topic,
    }

    if tier == "reject":
        output["action"] = "reject"
        output["message"] = f"未匹配到任何已知功能。用户输入：{user_input}"
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    if tier == "news":
        # ── 快讯模式：采集数据 → Agent 整理 → 文字回复 ──
        output["action"] = "text_reply"
        agent_hint = result.get("news_hint") or (domain.get("news_hint", "") if domain else "")
        output["agent_hint"] = agent_hint

        steps = domain["steps"] if domain else []
        search_templates = domain.get("search_templates", []) if domain else []

        # 执行数据采集步骤，结果写入任务文件夹
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_dir = os.path.join(PROJECT_ROOT, base_output, "tasks", task_id)
        os.makedirs(task_dir, exist_ok=True)
        output["task_id"] = task_id
        output["task_dir"] = task_dir

        today = datetime.now().strftime("%Y-%m-%d")
        tpl_vars = {"name": name, "code": code, "topic": topic, "date": today}

        meta = {
            "task_id": task_id,
            "cmd": "smart",
            "report_type": domain["id"] if domain else "news",
            "label": domain["label"] if domain else "快讯",
            "created_at": datetime.now().isoformat(),
            "date": today,
            "status": TaskState.RUNNING,
            "args": {"code": code, "name": name, "topic": topic, "style": style, "color_type": color_type, "output": base_output},
            "steps": {step: "pending" for step in steps},
            "search_queries": [q.format(**tpl_vars) for q in search_templates],
            "keyword_groups": [],
            "files": {},
            "agent_hint": agent_hint,
            "prompt_template": {},
            "report_path": "",
            "error": "",
            "smart_tier": "news",
        }
        save_meta(task_dir, meta)

        runner = TaskRunner(task_dir, meta, PROJECT_ROOT)

        domain_label = domain["label"] if domain else "快讯"
        banner(f"🦞 Smart ｜ {domain_label} ｜ 快讯模式 ｜ 任务 {task_id}")
        print(f"  任务目录：{task_dir}")

        # 执行采集步骤
        for step in steps:
            try:
                if step == "market_index":
                    ok, path = runner.run_market_index()
                    meta["steps"]["market_index"] = "done" if ok else "failed"
                    if ok:
                        meta["files"]["market_index"] = path
                        step_ok("market_index", f"大盘指数 → {os.path.basename(path)}")
                    else:
                        step_warn("market_index", "大盘数据获取失败")
                elif step == "market_state":
                    ok, path = runner.run_market_state()
                    meta["steps"]["market_state"] = "done" if ok else "failed"
                    if ok:
                        meta["files"]["market_state"] = path
                        step_ok("market_state", f"大盘整体状况 → {os.path.basename(path)}")
                    else:
                        step_warn("market_state", "大盘整体状况获取失败，可手动补充")
                elif step == "portfolio":
                    portfolio_file = meta["args"].get("portfolio_file", "")
                    ok, path = runner.run_portfolio(portfolio_file if portfolio_file else None)
                    meta["steps"]["portfolio"] = "done" if ok else "failed"
                    if ok:
                        meta["files"]["portfolio"] = path
                        step_ok("portfolio", f"持仓诊断 → {os.path.basename(path)}")
                    else:
                        step_warn("portfolio", "持仓数据获取失败")

                elif step == "search":
                    queries = meta["search_queries"]
                    if queries:
                        paths = runner.run_search(queries)
                        meta["steps"]["search"] = "done" if paths else "failed"
                        meta["files"]["search"] = paths
                        step_ok("search", f"搜索完成 {len(paths)} 个关键词")

                elif step in RESERVED_STEPS:
                    ok, path = runner.run_reserved_step(step)
                    meta["steps"][step] = "done" if ok else "failed"
                    if ok:
                        meta["files"][step] = path
                        step_ok(step, f"{os.path.basename(path)}（预留占位，待实现）")
                    else:
                        step_warn(step, f"{step} 生成占位文件失败")

            except Exception as e:
                meta["steps"][step] = "failed"
                step_fail(step, str(e))
            save_meta(task_dir, meta)

        meta["status"] = TaskState.DATA_DONE
        save_meta(task_dir, meta)

        # 输出给 Agent 的数据文件列表
        output["data_files"] = {}
        for key, val in meta["files"].items():
            if isinstance(val, list):
                output["data_files"][key] = val
            elif val:
                output["data_files"][key] = val

        print(f"\n{'─'*60}")
        print(f"⚡ 快讯模式：数据采集完成，请 Agent 读取数据后直接文字回复")
        print(f"{'─'*60}\n")

    elif tier in ("quick", "deep"):
        # ── 快报 / 研报模式：采集数据 → Agent 填 07 → 生成 PDF ──
        output["action"] = "generate_report"

        # 选择模板
        template_key = f"{tier}_template"
        prompt_template = domain.get(template_key) if domain else None
        hint_key = f"{tier}_hint"
        agent_hint = domain.get(hint_key, "") if domain else ""
        output["agent_hint"] = agent_hint
        # prompt_template 内容已全量嵌入 5_agent_briefing.md 和 5_agent_report_input.json，
        # 不输出文件名给 Agent，避免误导 Agent 去读取这个 JSON 文件
        output["prompt_embedded"] = True

        import argparse as ap
        args = ap.Namespace(
            code=code, name=name, topic=topic,
            style=style, color_type=color_type, layout=layout, output=base_output,
        )

        task_id, task_dir, meta = run_smart_task(domain, tier, prompt_template, agent_hint, args)

        output["task_id"] = task_id
        output["task_dir"] = task_dir

        # 填充数据文件列表（修复：quick/deep 模式也需要返回 data_files）
        output["data_files"] = {}
        for key, val in meta.get("files", {}).items():
            if isinstance(val, list):
                output["data_files"][key] = val
            elif val:
                output["data_files"][key] = val

    print(json.dumps(output, ensure_ascii=False, indent=2))


def run_smart_task(domain: dict, tier: str, prompt_template: str, agent_hint: str,
                   args: argparse.Namespace) -> tuple:
    """
    Smart 模式的任务执行（快报/研报）。
    从 domain 配置中获取 steps/search_templates，从 prompt_template 加载模板。
    
    返回: (task_id, task_dir, meta) - 包含完整 meta 对象供 cmd_smart 使用
    """
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    today = datetime.now().strftime("%Y-%m-%d")
    tpl_vars = {
        "name":  getattr(args, "name", ""),
        "code":  getattr(args, "code", ""),
        "topic": getattr(args, "topic", getattr(args, "name", "")),
        "date":  today,
    }

    # screener 未指定 topic 时，根据投资风格自动派生选股方向
    if domain["id"] == "screener" and not tpl_vars["topic"]:
        _user_prefs = _load_user_config()
        style = _user_prefs.get("user", {}).get("investment_style", "")
        style_topic_map = {
            "value":  "蓝筹 低估值 高股息 白马股",
            "growth": "高科技 高成长 新兴 景气赛道",
            "band":   "活跃 波段 资金轮动 箱体",
            "trend":  "趋势 上升通道 资金流入",
        }
        derived = style_topic_map.get(style, "低估值蓝筹")
        tpl_vars["topic"] = derived
        _log.info(f"   🎯 投资风格《{style}》→ 自动派生选股主题: {derived}")

    # 加载 prompt 模板
    prompt_tpl = load_prompt_template(prompt_template) if prompt_template else {}

    # ── 搜索关键词 ──
    # 1. topic 清洗：去掉逗号、多余空格，剥离 tier_tag 关键词
    topic_raw = tpl_vars.get("topic", "")
    clean_topic = topic_raw.replace("，", " ").replace(",", " ").strip()
    # 剥离 tier_tags（快报/日报/研报/深度...）避免污染搜索词
    tier_tags_conf = SMART_CONFIG.get("tier_tags", {})
    all_tier_words = []
    for words in tier_tags_conf.values():
        if isinstance(words, list):
            all_tier_words.extend(words)
    for tw in all_tier_words:
        clean_topic = clean_topic.replace(tw, "").strip()
    # 再次清理多余空格
    clean_topic = re.sub(r"\s+", " ", clean_topic).strip()
    clean_vars = {**tpl_vars, "topic": clean_topic}

    # 2. search_templates 渲染（核心关键词）
    search_queries = [q.format(**clean_vars) for q in domain.get("search_templates", [])]
    kw_set = set(search_queries)

    # 3. recommendedKeywords：智能追加时效性关键词（带去重）
    #    不再盲目追加所有 recommendedKeywords（它们是报告结构标签，不是搜索词）
    #    选股类特殊处理：追加高质量时效性关键词（去重后最多追加 2 个）
    if domain["id"] == "screener":
        extra_kws = [
            f"今日涨停复盘 {today}",
            f"连板股 龙虎榜 {today}",
            f"主力资金 游资动向 {today}",
        ]
        _template_words = set()
        for q in search_queries:
            _template_words.update(q.split())
        added = 0
        for kw in extra_kws:
            if added >= 2:
                break
            if kw in kw_set:
                continue
            kw_core = set(kw.split())
            overlap = len(kw_core & _template_words) / len(kw_core) if kw_core else 0
            if overlap >= 0.7:
                continue
            search_queries.append(kw)
            kw_set.add(kw)
            _template_words.update(kw.split())
            added += 1

    # ── keyword_groups：去重，不再重复搜两遍 ──
    keyword_groups = []
    data_sources = prompt_tpl.get("recommendedDataSources", [])
    # 过滤掉非域名的数据源标签（如"通达信""龙虎榜""交易所公告"等）
    src_domain_map = {
        "东方财富": "eastmoney.com", "同花顺": "10jqka.com.cn",
        "Wind": "wind.com.cn", "新浪财经": "finance.sina.com.cn",
        "证券时报": "stcn.com", "上海证券报": "cnstock.com",
        "财新": "caixin.com", "36氪": "36kr.com", "雪球": "xueqiu.com",
        "巨潮资讯": "cninfo.com.cn",
    }
    if data_sources:
        source_domains = []
        for s in data_sources:
            mapped = src_domain_map.get(s)
            if mapped:
                source_domains.append(mapped)
        if source_domains:
            keyword_groups.append({
                "keywords": search_queries,
                "sources": source_domains,
                "max_per_source": 8,
                "group_label": f"{domain['label']}_数据源搜索",
            })
    # 通用搜索：只用核心关键词（search_templates），不重复全部
    keyword_groups.append({
        "keywords": search_queries,
        "max_per_keyword": 12,
        "group_label": f"{domain['label']}_通用搜索",
    })

    base_output = getattr(args, "output", "output")
    task_dir = os.path.join(PROJECT_ROOT, base_output, "tasks", task_id)
    os.makedirs(task_dir, exist_ok=True)

    # 加载用户配置
    user_prefs = _load_user_config()

    steps_to_run = domain.get("quick_steps", domain["steps"]) if tier == "quick" else domain["steps"]

    # 从 config.json 读取输出样式（配置优先级：CLI参数 > config.json > 模板默认 > 代码默认）
    cfg_style      = _style_from_config(user_prefs, "report_style", prompt_tpl.get("style", "blue"))
    cfg_color_type = _style_from_config(user_prefs, "color_type", prompt_tpl.get("color_type", "liquid"))
    cfg_layout     = _style_from_config(user_prefs, "layout", prompt_tpl.get("layout", "rounded"))

    _log.info(f"🔍 Smart 路由: domain={domain['id']} tier={tier} → 任务 {task_id}")
    meta = {
        "task_id":     task_id,
        "cmd":         "smart",
        "report_type": domain["id"],
        "label":       domain["label"],
        "created_at":  datetime.now().isoformat(),
        "date":        today,
        "status":      TaskState.PENDING,
        "user_prefs":  user_prefs,  # 注入用户配置
        "args": {
            "code":   getattr(args, "code", ""),
            "name":   getattr(args, "name", ""),
            "topic":  getattr(args, "topic", ""),
            "style":  getattr(args, "style", cfg_style),
            "color_type": getattr(args, "color_type", cfg_color_type),
            "layout": getattr(args, "layout", cfg_layout),
            "output": base_output,
        },
        "steps": {step: "pending" for step in steps_to_run},
        "search_queries": search_queries,
        "keyword_groups": keyword_groups,
        "files": {},
        "agent_hint": agent_hint,
        "prompt_template": prompt_tpl,
        "report_path": "",
        "error": "",
        "smart_tier": tier,
    }
    save_meta(task_dir, meta)

    tier_label = {"quick": "快报", "deep": "研报"}[tier]
    banner(f"🦞 Smart ｜ {domain['label']} ｜ {tier_label} ｜ 任务 {task_id}")
    print(f"  任务目录：{task_dir}")

    runner = TaskRunner(task_dir, meta, PROJECT_ROOT)

    # ── Phase 1: 数据采集 ──
    print(f"\n【Phase 1】数据采集（代码驱动）")
    _log.info(f"▶ Phase 1 开始 (smart) | 步骤: {steps_to_run}")
    meta["status"] = TaskState.RUNNING
    save_meta(task_dir, meta)

    for step in steps_to_run:
        try:
            _log.info(f"  ▶ 执行步骤: {step}")
            if step == "quote":
                ok, path = runner.run_quote(meta["args"]["code"])
                meta["steps"]["quote"] = "done" if ok else "failed"
                if ok: meta["files"]["quote"] = path; step_ok("quote", os.path.basename(path))
                else: step_warn("quote", "实时行情获取失败")

            elif step == "kline":
                ok, path = runner.run_kline(meta["args"]["code"])
                meta["steps"]["kline"] = "done" if ok else "failed"
                if ok: meta["files"]["kline"] = path; step_ok("kline", os.path.basename(path))
                else: step_warn("kline", "K线数据获取失败")

            elif step == "master":
                ok, path = runner.run_master(meta["args"]["code"])
                meta["steps"]["master"] = "done" if ok else "failed"
                if ok: meta["files"]["master"] = path; step_ok("master", os.path.basename(path))
                else: step_warn("master", "个股详细资料获取失败")

            elif step == "market_index":
                ok, path = runner.run_market_index()
                meta["steps"]["market_index"] = "done" if ok else "failed"
                if ok: meta["files"]["market_index"] = path; step_ok("market_index", os.path.basename(path))
                else: step_warn("market_index", "大盘数据获取失败")

            elif step == "market_state":
                ok, path = runner.run_market_state()
                meta["steps"]["market_state"] = "done" if ok else "failed"
                if ok: meta["files"]["market_state"] = path; step_ok("market_state", os.path.basename(path))
                else: step_warn("market_state", "大盘整体状况获取失败，可手动补充")

            elif step == "portfolio":
                portfolio_file = meta["args"].get("portfolio_file", "")
                ok, path = runner.run_portfolio(portfolio_file if portfolio_file else None)
                meta["steps"]["portfolio"] = "done" if ok else "failed"
                if ok: meta["files"]["portfolio"] = path; step_ok("portfolio", os.path.basename(path))
                else: step_warn("portfolio", "持仓数据获取失败")

            elif step == "search":
                keyword_groups = meta.get("keyword_groups", [])
                if keyword_groups:
                    paths = runner.run_batch_search(keyword_groups)
                    meta["steps"]["search"] = "done" if paths else "failed"
                    meta["files"]["search"] = paths
                    step_ok("search", f"批量搜索完成（{len(keyword_groups)} 组）")
                else:
                    paths = runner.run_search(meta["search_queries"])
                    meta["steps"]["search"] = "done" if paths else "failed"
                    meta["files"]["search"] = paths
                    step_ok("search", f"搜索完成 {len(paths)} 个关键词")

            elif step in RESERVED_STEPS:
                ok, path = runner.run_reserved_step(step)
                meta["steps"][step] = "done" if ok else "failed"
                if ok:
                    meta["files"][step] = path
                    step_ok(step, f"{os.path.basename(path)}（预留占位，待实现）")
                else:
                    step_warn(step, f"{step} 生成占位文件失败")

        except Exception as e:
            meta["steps"][step] = "failed"
            step_fail(step, str(e))
        save_meta(task_dir, meta)

    meta["status"] = TaskState.DATA_DONE
    save_meta(task_dir, meta)
    _log.info(f"✅ Phase 1 完成 (smart) | 任务 {task_id} | status=DATA_DONE | 步骤状态: {meta['steps']}")

    # ── 生成 Agent 指引 ──
    runner.write_agent_briefing()

    # ── Alone 模式检查 ──
    run_mode = get_user_config("system.run_mode", "skill")
    _log.info(f"  ▶ run_mode={run_mode}")
    if run_mode == "alone":
        from scripts.generate_alonemode import run_alone_mode
        alone_result = run_alone_mode(task_dir, meta, PROJECT_ROOT)
        if alone_result.get("success"):
            meta["status"] = TaskState.DONE
            if alone_result.get("html_path"):
                meta["html_path"] = alone_result["html_path"]
            if alone_result.get("pdf_path"):
                meta["report_path"] = alone_result["pdf_path"]
            save_meta(task_dir, meta)
            _log.info(f"✅ Alone 模式完成 | 任务 {task_id} | HTML: {alone_result.get('html_path','')}")
            print(f"\n{'─'*60}")
            print(f"  ✅ Alone 模式完成")
            print(f"{'─'*60}\n")
            # 跳过 Agent 指导打印，只输出关键信息
            print(f"\n  任务ID: {task_id}")
            if alone_result.get("tool_called"):
                print(f"  📝 报告数据: 5_agent_report_input.json")
            if alone_result.get("html_path"):
                print(f"  🌐 HTML: {alone_result['html_path']}")
            if alone_result.get("pdf_path"):
                print(f"  📄 PDF:  {alone_result['pdf_path']}")
            print()
            return task_id, task_dir, meta
        else:
            _log.warn(f"⚠️ Alone 模式失败: {alone_result.get('error', '未知错误')}，降级为 skill 模式")
            print(f"\n  ⚠️ Alone 模式失败: {alone_result.get('error', '未知错误')}")
            print(f"  降级为 skill 模式，继续打印 Agent 指导")

    # ── 打印 Agent 操作指南 ──
    _log.info(f"📋 Phase 2 已就绪 (smart) | 任务 {task_id} | 等待 Agent 填充 5_agent_report_input.json")
    print(f"\n{'─'*60}")
    print(f"【Phase 2】Agent 整合阶段 ← {tier_label}模式")
    print(f"{'─'*60}")
    print(f"\n  任务目录：{task_dir}")
    print(f"\n  已生成数据文件：")
    for key, val in meta["files"].items():
        if isinstance(val, list):
            for p in val:
                print(f"    📄 {os.path.basename(p)}")
        elif val:
            print(f"    📄 {os.path.basename(val)}")
    print(f"\n  📋 Agent 任务说明：")
    print(f"    🔹 请先阅读 5_agent_briefing.md，里面有完整的工作流程、数据结构说明和填写规范")
    print(f"    🔹 读取各数据文件 → 补充搜索 → 按大纲组织内容 → 填写 5_agent_report_input.json")
    print(f"    📌 {agent_hint}")
    print(f"\n  目标输出文件：")
    print(f"    📝 {task_dir}\\5_agent_report_input.json")
    print(f"\n  ⚡ Agent 完成填充后，运行：")
    print(f"    python main.py generate --task-id {task_id}")
    print(f"\n{'─'*60}\n")

    return task_id, task_dir, meta


# ═══════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="🦞 龙虾调研助手 V3 — 代码驱动主入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python main.py stock --code 000063 --name 中兴通讯
  python main.py stock --code 000063 --name 中兴通讯 --type qiye_baogao
  python main.py market
  python main.py screener
  python main.py generate --task-id 20260426_103000
  python main.py status  --task-id 20260426_103000
  python main.py list
        """
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    _color_type_help = "渲染类型：solid(纯色)/gradient(渐变)/liquid(液态)"

    # stock / company
    for cmd_name in ["stock", "company"]:
        p = sub.add_parser(cmd_name, help=REPORT_TYPES[cmd_name]["label"])
        p.add_argument("--code",   "-c", required=True,  help="股票代码，如 000063")
        p.add_argument("--name",   "-n", required=True,  help="股票/公司名称")
        p.add_argument("--type",   "-t", default=None,   help="报告类型（可选覆盖）")
        p.add_argument("--style",  "-s", default="blue", help="颜色主题（blue/purple/green/...）")
        p.add_argument("--color-type", "-C", default="liquid", help=_color_type_help)
        p.add_argument("--layout", "-l", default="rounded", help="布局风格：rounded(圆角)/square(方正)/minimal(极简)")
        p.add_argument("--output", "-o", default="output")

    # market
    p = sub.add_parser("market", help=REPORT_TYPES["market"]["label"])
    p.add_argument("--style",  "-s", default="blue")
    p.add_argument("--color-type", "-C", default="liquid", help=_color_type_help)
    p.add_argument("--layout", "-l", default="rounded", help="布局风格")
    p.add_argument("--output", "-o", default="output")

    # portfolio
    p = sub.add_parser("portfolio", help=REPORT_TYPES["portfolio"]["label"])
    p.add_argument("--file",  "-f", required=True, help="持仓数据JSON文件路径")
    p.add_argument("--style", "-s", default="blue")
    p.add_argument("--color-type", "-C", default="liquid", help=_color_type_help)
    p.add_argument("--layout","-l", default="rounded", help="布局风格")
    p.add_argument("--output","-o", default="output")

    # screener
    p = sub.add_parser("screener", help=REPORT_TYPES["screener"]["label"])
    p.add_argument("--topic", "-T", default="", help=argparse.SUPPRESS)
    p.add_argument("--style", "-s", default="blue")
    p.add_argument("--color-type", "-C", default="liquid", help=_color_type_help)
    p.add_argument("--layout","-l", default="rounded", help="布局风格")
    p.add_argument("--output","-o", default="output")

    # smart — 自然语言入口，自动匹配路由
    p = sub.add_parser("smart", help="🦞 自然语言入口，自动匹配快讯/快报/研报")
    p.add_argument("--input", "-i", required=True, help="用户自然语言输入")
    p.add_argument("--code",  "-c", default="", help="股票代码（可选）")
    p.add_argument("--name",  "-n", default="", help="股票/公司名称（可选）")
    p.add_argument("--topic", "-T", default="", help="主题（可选，默认从 input 提取）")
    p.add_argument("--style",  "-s", default="blue")
    p.add_argument("--color-type", "-C", default="liquid", help=_color_type_help)
    p.add_argument("--layout", "-l", default="rounded", help="布局风格")
    p.add_argument("--output", "-o", default="output")

    # generate（Phase 3）
    p = sub.add_parser("generate", help="读取 agent_input.json 生成最终报告")
    p.add_argument("--task-id", "-i", required=True, help="任务ID")
    p.add_argument("--output",  "-o", default="output")

    # status
    p = sub.add_parser("status", help="查看任务状态")
    p.add_argument("--task-id", "-i", required=True)
    p.add_argument("--output",  "-o", default="output")

    # list
    p = sub.add_parser("list", help="列出所有任务")
    p.add_argument("--output", "-o", default="output")

    # emu — 模拟持仓（Phase 4）
    p_emu = sub.add_parser("emu", help="🎮 模拟持仓管理（Phase 4）")
    emu_sub = p_emu.add_subparsers(dest="emu_cmd")
    emu_sub.add_parser("show", help="查看模拟持仓")
    emu_sub.add_parser("ops", help="查看操作记录")
    emu_sub.add_parser("reflect", help="运行反思复盘")
    emu_sub.add_parser("init", help="初始化模拟持仓")
    emu_sub.add_parser("reset", help="重置模拟持仓")

    args = parser.parse_args()

    _log.info(f"🚀 CLI 启动: {args.cmd}")

    if args.cmd == "generate":
        run_generate(args.task_id, args.output)
    elif args.cmd == "status":
        cmd_status(args.task_id, args.output)
    elif args.cmd == "list":
        cmd_list(args.output)
    elif args.cmd == "smart":
        cmd_smart(args.input, code=args.code, name=args.name,
                  topic=args.topic, style=args.style,
                  color_type=args.color_type, layout=args.layout,
                  base_output=args.output)
    elif args.cmd == "emu":
        _cmd_emu(args)
    else:
        run_task(args.cmd, args)


def _cmd_emu(args):
    """模拟持仓 CLI 入口（Phase 4）"""
    try:
        _SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")
        if _SCRIPTS_DIR not in sys.path:
            sys.path.insert(0, _SCRIPTS_DIR)
        from emu_manager import cmd_show, cmd_ops, cmd_reflect, cmd_reset
        from emu_manager import init_emu_portfolio
    except ImportError as e:
        print(f"❌ 模拟持仓模块未安装: {e}")
        return

    cmd = getattr(args, "emu_cmd", "")
    if cmd == "show":
        cmd_show()
    elif cmd == "ops":
        cmd_ops()
    elif cmd == "reflect":
        cmd_reflect()
    elif cmd == "init":
        init_emu_portfolio(force=True)
        print("✅ 模拟持仓已初始化")
    elif cmd == "reset":
        cmd_reset()
    else:
        print("可用命令: show, ops, reflect, init, reset")


if __name__ == "__main__":
    main()
