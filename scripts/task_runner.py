# -*- coding: utf-8 -*-
"""
龙虾调研助手 - TaskRunner
============================
职责：代码驱动地调用各工具脚本，把结果规范写入任务文件夹的 JSON 文件。
Agent 不参与此阶段，只在 Phase 2（整合补充）时读取这些 JSON。

JSON 文件命名规范（按数据类型分层）：
  0_portfolio_img__parse.json     持仓图片解析结果（用户上传图片时）
  2_stock_quote_realtime.json     实时行情
  2_stock_kline_indicator.json    K线 + 技术指标
  2_stock_info_detail.json        个股详细资料（证券之星）
  1_market_index_tick.json        大盘指数（ticktime）
  1_market_status_sina.json       大盘整体状况（Playwright 爬取新浪行情页）
  3_news_daily_all.json           当日新闻快讯（财经/科技/社会等频道）
  4_search_keyword_01.json        搜索结果（第1个关键词）
  4_search_keyword_02.json        搜索结果（第2个关键词）...
  4_search_batch_summary.json     批量搜索汇总结果
  1_market_akshare_macro.json     AKShare 结构化数据（个股新闻/北向资金/融资融券）
  0_portfolio_fresh.json          持仓数据（刷新行情后）
  5_agent_briefing.md             给 Agent 的工作说明
  5_agent_report_input.json       ← Agent 填写，最终报告数据
"""

import sys
import os
import io
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TaskRunner:
    def __init__(self, task_dir: str, meta: dict, project_root: str):
        self.task_dir    = task_dir
        self.meta        = meta
        self.project_root = project_root
        self.python      = sys.executable  # 使用当前 Python

    # ─────────────────────────────────────────────────────────
    # 工具方法
    # ─────────────────────────────────────────────────────────

    def _write_json(self, filename: str, data: Any) -> str:
        """写入 JSON 文件，返回文件路径"""
        path = os.path.join(self.task_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def _run_script(self, script_args: list, timeout: int = 60) -> Tuple[bool, str]:
        """
        运行脚本，返回 (成功?, stdout文本)
        script_args 示例: ["scripts/ticktime.py", "--code", "000063"]
        """
        cmd = [self.python] + script_args
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONPATH"] = self.project_root
            # Playwright 的 Node 不支持 NODE_OPTIONS（如 --use-system-ca），需清除
            env.pop("NODE_OPTIONS", None)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=self.project_root,
                env=env,
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr or result.stdout
        except subprocess.TimeoutExpired:
            return False, f"超时（{timeout}s）"
        except Exception as e:
            return False, str(e)

    # ─────────────────────────────────────────────────────────
    # Step 1: 实时行情
    # ─────────────────────────────────────────────────────────

    def run_quote(self, stock_code: str) -> Tuple[bool, str]:
        """
        采集个股实时行情，写入 2_stock_quote_realtime.json
        使用 ticktime.StockDataAPI
        """
        try:
            from scripts.ticktime import StockDataAPI
            api = StockDataAPI()

            # 尝试深圳 / 上海
            result = api.get_realtime_stock(f"sz{stock_code}")
            if not result.get("success"):
                result = api.get_realtime_stock(f"sh{stock_code}")

            if result.get("success"):
                raw = result.get("data", {})
                data = {
                    "_meta": {
                        "step": "quote",
                        "stock_code": stock_code,
                        "fetched_at": datetime.now().isoformat(),
                        "source": raw.get("数据源", "sina/tencent"),
                    },
                    "quote": {
                        "code":         stock_code,
                        "name":         raw.get("名称", ""),
                        "price":        raw.get("当前价", 0.0),
                        "change":       raw.get("涨跌额", 0.0),
                        "change_pct":   raw.get("涨跌幅(%)", 0.0),
                        "open":         raw.get("今开", 0.0),
                        "high":         raw.get("最高", 0.0),
                        "low":          raw.get("最低", 0.0),
                        "pre_close":    raw.get("昨收", 0.0),
                        "volume":       raw.get("成交量(手)", 0),
                        "turnover":     raw.get("成交额(元)", 0.0),
                        "time":         raw.get("时间", ""),
                    }
                }
                path = self._write_json("2_stock_quote_realtime.json", data)
                return True, path
            else:
                # 写入空占位文件
                data = {
                    "_meta": {"step": "quote", "stock_code": stock_code, "status": "failed"},
                    "quote": {}
                }
                path = self._write_json("2_stock_quote_realtime.json", data)
                return False, path

        except Exception as e:
            data = {"_meta": {"step": "quote", "error": str(e)}, "quote": {}}
            path = self._write_json("2_stock_quote_realtime.json", data)
            return False, path

    # ─────────────────────────────────────────────────────────
    # Step 2: K线 + 技术指标
    # ─────────────────────────────────────────────────────────

    def run_kline(self, stock_code: str, days: int = 90) -> Tuple[bool, str]:
        """
        采集历史K线并计算技术指标，写入 2_stock_kline_indicator.json
        """
        try:
            from scripts.stock_data_collector import (
                get_history_kline,
                get_realtime_quote,
                calculate_technical_indicators,
            )

            kline_data    = get_history_kline(stock_code, days)
            realtime_data = get_realtime_quote(stock_code)
            tech          = calculate_technical_indicators(kline_data, realtime_data)

            # 只保留最近30条K线，避免 JSON 太大
            kline_summary = kline_data[-30:] if kline_data else []

            data = {
                "_meta": {
                    "step": "kline",
                    "stock_code": stock_code,
                    "days_requested": days,
                    "kline_count": len(kline_data),
                    "fetched_at": datetime.now().isoformat(),
                },
                "technical": tech,
                "kline_recent_30": kline_summary,
            }
            path = self._write_json("2_stock_kline_indicator.json", data)
            return True, path

        except Exception as e:
            data = {"_meta": {"step": "kline", "error": str(e)}, "technical": {}, "kline_recent_30": []}
            path = self._write_json("2_stock_kline_indicator.json", data)
            return False, path

    # ─────────────────────────────────────────────────────────
    # Step 3: 个股详细资料（证券之星）
    # ─────────────────────────────────────────────────────────

    def run_master(self, stock_code: str) -> Tuple[bool, str]:
        """
        通过 stock_master.py 爬取证券之星个股详细资料
        由于 stock_master.py 是面向文件输出的，
        我们先运行它，再读取生成的 txt 文件，写入 JSON
        """
        try:
            # stock_master.py 将结果写入 stock_data/<code>/ 目录
            ok, stdout = self._run_script(
                ["scripts/stock_master.py", stock_code],
                timeout=120,
            )
            # 查找生成的 txt 文件
            stock_data_dir = os.path.join(self.project_root, "stock_data", stock_code)
            txt_files = []
            if os.path.exists(stock_data_dir):
                txt_files = [
                    f for f in os.listdir(stock_data_dir)
                    if f.endswith(".txt") and "market_state" not in f
                ]

            combined_text = ""
            if txt_files:
                for fname in sorted(txt_files)[:5]:  # 最多读5个文件
                    fpath = os.path.join(stock_data_dir, fname)
                    try:
                        with open(fpath, encoding="utf-8", errors="replace") as f:
                            combined_text += f"\n\n=== {fname} ===\n" + f.read()[:8000]
                    except:
                        pass

            data = {
                "_meta": {
                    "step": "master",
                    "stock_code": stock_code,
                    "fetched_at": datetime.now().isoformat(),
                    "files_read": txt_files,
                    "run_success": ok,
                },
                "raw_text": combined_text[:20000],  # 限制 20k 字符
                "agent_note": "请从 raw_text 中提取：公司简介、主营业务、财务数据、股东信息等关键内容，填入 5_agent_report_input.json",
            }
            path = self._write_json("2_stock_info_detail.json", data)
            return bool(combined_text), path

        except Exception as e:
            data = {"_meta": {"step": "master", "error": str(e)}, "raw_text": ""}
            path = self._write_json("2_stock_info_detail.json", data)
            return False, path

    # ─────────────────────────────────────────────────────────
    # Step 4: 大盘指数
    # ─────────────────────────────────────────────────────────

    def run_market_index(self) -> Tuple[bool, str]:
        """采集实时大盘指数，写入 1_market_index_tick.json"""
        try:
            from scripts.ticktime import StockDataAPI
            api = StockDataAPI()
            result = api.get_realtime_index()

            data = {
                "_meta": {
                    "step": "market_index",
                    "fetched_at": datetime.now().isoformat(),
                },
                "indices": result if result else {},
                "agent_note": "请基于此大盘数据分析今日市场情绪、趋势、操作建议",
            }
            path = self._write_json("1_market_index_tick.json", data)
            return bool(result), path

        except Exception as e:
            data = {"_meta": {"step": "market_index", "error": str(e)}, "indices": {}}
            path = self._write_json("1_market_index_tick.json", data)
            return False, path

    # ─────────────────────────────────────────────────────────
    # Step 5: 联网搜索
    # ─────────────────────────────────────────────────────────

    def run_search(self, queries: List[str]) -> List[str]:
        """
        兼容旧模式：对每个关键词调用 websearch_pro.py，结果写入 4_search_keyword_N.json
        返回生成的文件路径列表
        """
        paths = []
        for i, query in enumerate(queries):
            try:
                ok, stdout = self._run_script(
                    ["scripts/websearch_pro.py", query],
                    timeout=45,
                )
                data = {
                    "_meta": {
                        "step": "search",
                        "query": query,
                        "query_index": i,
                        "fetched_at": datetime.now().isoformat(),
                        "success": ok,
                    },
                    "raw_output": stdout[:8000] if stdout else "",
                    "agent_note": f"请从此搜索结果中提取与报告相关的关键信息（关键词：{query}）",
                }
                path = self._write_json(f"4_search_keyword_{i+1:02d}.json", data)
                paths.append(path)

            except Exception as e:
                data = {
                    "_meta": {"step": "search", "query": query, "error": str(e)},
                    "raw_output": "",
                }
                path = self._write_json(f"4_search_keyword_{i+1:02d}.json", data)
                paths.append(path)

        return paths

    def run_batch_search(self, keyword_groups: List[dict]) -> List[str]:
        """
        批量搜索模式：关键词组 × 数据源组，循环搜索后汇总。
        结果写入 4_search_batch_summary.json

        参数:
            keyword_groups: 传给 websearch_pro.run_batch_search 的参数
                [{
                    "keywords": ["关键词1", "关键词2"],
                    "sources": ["eastmoney", "cninfo.com.cn"],  # 可选
                    "max_per_keyword": 10,   # 可选
                    "max_per_source": 8,     # 可选，有 sources 时生效
                    "group_label": "组标签",  # 可选
                }]
        返回生成的文件路径列表
        """
        try:
            # 使用 websearch_pro 的 API 模式（不通过命令行子进程）
            sys.path.insert(0, os.path.join(self.project_root, "scripts"))
            from websearch_pro import run_batch_search

            result = run_batch_search(
                keyword_groups=keyword_groups,
                fresh=False,
            )

            # 构建输出数据
            data = {
                "_meta": {
                    "step": "search_batch",
                    "keyword_groups": keyword_groups,
                    "fetched_at": datetime.now().isoformat(),
                    "success": True,
                },
                "summary": result["summary"],
                "groups": [],
                "all_results": result["all_results"],
                "agent_note": (
                    "这是批量搜索结果，包含多个关键词组的数据。"
                    "all_results 是全局去重汇总，groups 是按组分组的原始结果。"
                    "请综合所有结果提取与报告相关的关键信息。"
                ),
            }

            # 每个组的结构化结果
            for g in result.get("groups", []):
                group_entry = {
                    "label": g["label"],
                    "keywords": g["keywords"],
                    "sources": g.get("sources"),
                    "result_count": g["result_count"],
                    "results": g["results"],
                }
                data["groups"].append(group_entry)

            # 生成文本版输出（方便 Agent 快速浏览）
            # 已移除 raw_output 和 4_search_batch_summary.txt，减少冗余

            path = self._write_json("4_search_batch_summary.json", data)

            return [path]

        except Exception as e:
            data = {
                "_meta": {
                    "step": "search_batch",
                    "keyword_groups": keyword_groups,
                    "error": str(e),
                    "fetched_at": datetime.now().isoformat(),
                    "success": False,
                },
                "agent_note": f"批量搜索失败: {str(e)}",
            }
            path = self._write_json("4_search_batch_summary.json", data)
            return [path]


    # ─────────────────────────────────────────────────────────
    # Step 10: 持仓诊断
    # ─────────────────────────────────────────────────────────

    def run_portfolio(self, portfolio_file: str = None) -> Tuple[bool, str]:
        """
        从 config/portfolio.json 或用户指定的 portfolio_file 读取持仓
        → 刷新最新价 → 计算盈亏 → 写入 0_portfolio_fresh.json
        → 对每个持仓股执行行情/K线搜索（按 domain steps）

        持仓诊断任务的核心入口方法。
        """
        import sys as _sys
        _sys.path.insert(0, os.path.join(self.project_root, "config"))
        from config import refresh_portfolio_live, get_portfolio, save_portfolio, _PORTFOLIO_JSON
        import shutil

        backup_path = _PORTFOLIO_JSON + ".backup"
        used_backup = False

        if portfolio_file and os.path.exists(portfolio_file):
            # 备份原 portfolio.json，加载用户指定文件
            if os.path.exists(_PORTFOLIO_JSON):
                shutil.copy2(_PORTFOLIO_JSON, backup_path)
                used_backup = True
            with open(portfolio_file, encoding="utf-8") as f:
                user_pf = json.load(f)
            save_portfolio(user_pf)

        # ── Step 1: 刷新持仓行情 ──
        try:
            refresh_result = refresh_portfolio_live()

            # ── Step 2: 读取完整持仓（带最新价）──
            pf = get_portfolio()

            data = {
                "_meta": {
                    "step": "portfolio",
                    "fetched_at": datetime.now().isoformat(),
                    "refresh": {
                        "success": refresh_result["success"],
                        "updated_count": refresh_result["updated_count"],
                        "failed_count": refresh_result["failed_count"],
                        "failed_codes": refresh_result["failed_codes"],
                    },
                },
                "account": pf["account"],
                "positions": pf["positions"],
                "summary": pf["summary"],
                "agent_note": (
                    "这是用户的最新持仓快照（已刷新实时行情）。"
                    "请基于此数据分析：持仓结构、风险敞口、盈亏分布、行业分布，"
                    "给出优化建议。最终分析填入 5_agent_report_input.json。"
                ),
            }
            path = self._write_json("0_portfolio_fresh.json", data)

            # ── Step 3: 对每个持仓股采集行情数据 ──
            stock_steps = []
            for p in pf["positions"]:
                code = p["code"]
                name = p["name"]

                # 实时行情
                ok_quote, path_q = self.run_quote(code)
                self.meta.setdefault("files", {})
                if ok_quote:
                    self.meta["files"][f"quote_{code}"] = path_q

                # K线
                ok_kline, path_k = self.run_kline(code)
                if ok_kline:
                    self.meta["files"][f"kline_{code}"] = path_k

                stock_steps.append({
                    "code": code,
                    "name": name,
                    "quote_ok": ok_quote,
                    "kline_ok": ok_kline,
                })

            data["_meta"]["stock_steps"] = stock_steps
            # 重新写入（加了 stock_steps）
            self._write_json("0_portfolio_fresh.json", data)

            # 更新 meta
            self.meta.setdefault("steps", {})
            self.meta["steps"]["portfolio"] = "done" if refresh_result["success"] else "failed"

            return refresh_result["success"], path
        finally:
            if used_backup and os.path.exists(backup_path):
                shutil.copy2(backup_path, _PORTFOLIO_JSON)
                os.remove(backup_path)

    # ─────────────────────────────────────────────────────────
    # Agent 简报文件
    # ─────────────────────────────────────────────────────────

    def write_agent_briefing(self):
        """
        生成 5_agent_briefing.md：
        告诉 Agent：任务是什么、有哪些数据文件、需要填写什么、输出格式是什么
        如果有 prompt_template，会注入 dataRequirements 和 promptBody
        """
        meta = self.meta
        files_list = ""
        for key, val in meta.get("files", {}).items():
            if isinstance(val, list):
                for p in val:
                    files_list += f"  - {os.path.basename(p)}\n"
            elif val:
                files_list += f"  - {os.path.basename(val)}\n"

        # 读取 agent_input 模板
        schema = self._get_agent_input_schema(meta)
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)

        # 从 prompt_template 提取额外信息
        tpl = meta.get("prompt_template", {})
        tpl_name = tpl.get("name", "")
        data_req = tpl.get("dataRequirements", "")
        data_sources = tpl.get("recommendedDataSources", [])
        core_idea = tpl.get("coreIdea", "")
        prompt_body = tpl.get("promptBody", "")

        # 构建数据检查清单
        data_check_section = ""
        if data_req:
            separator = "\n"
            data_items = [item.strip() for item in data_req.replace("、", ",").split(",") if item.strip()]
            check_rows = [f"| {item} | _注明文件名_ | ⬜待检查 |" for item in data_items]
            data_check_header = """
## 数据完整性检查清单

请逐一确认以下数据是否已在数据文件或搜索结果中获取。**缺失的项需补充搜索获取。**

| 数据项 | 来源文件 | 状态 |
|:---|:---|:---|
"""
            data_check_section = data_check_header + separator.join(check_rows) + separator

        # 构建报告结构参考
        structure_section = ""
        if prompt_body:
            structure_section = f"""
## 报告结构参考（来自模板：{tpl_name}）

以下是大纲结构，按此结构组织报告内容：

```
{prompt_body}
```
"""

        # 数据来源
        sources_section = ""
        if data_sources:
            joined_sources = ", ".join(data_sources)
            sources_section = "\n**推荐数据源**：" + joined_sources + "\n"

        # 核心思路段落（提前构建避免嵌套 f-string）
        core_idea_section = ""
        if core_idea:
            core_idea_section = "\n**核心分析思路**：" + core_idea

        # 搜索关键词列表（提前构建）
        search_list = chr(10).join('- ' + q for q in meta.get('search_queries', []))

        # 数据检查的占位文本
        data_check_text = data_check_section if data_check_section else "请先读取所有数据文件，确认数据是否完整。"

        # 模板来源行（已全量嵌入 briefing 和 schema 中，不输出文件名避免误导 Agent）
        template_line = ''

        # ── 用户画像（从 user_prefs 构建） ──
        user_prefs = meta.get("user_prefs", {})
        user_section = ""
        if user_prefs:
            u = user_prefs.get("user", {})
            m = user_prefs.get("market", {})

            style_map = {"conservative": "保守", "balanced": "平衡", "aggressive": "积极"}
            risk_map  = {"low": "低风险", "medium": "中风险", "high": "高风险"}
            freq_map  = {"short": "短期(1-3天)", "medium": "中期(3-15天)", "long": "长期(>15天)"}
            asset_map = {"below_10w": "10万以下", "10w_to_50w": "10-50万", "50w_to_100w": "50-100万", "above_100w": "100万以上"}

            style     = style_map.get(u.get("investment_style", ""), u.get("investment_style", "未设置"))
            risk      = risk_map.get(u.get("risk_level", ""), u.get("risk_level", "未设置"))
            freq      = freq_map.get(u.get("operation_freq", ""), u.get("operation_freq", "未设置"))
            assets    = asset_map.get(u.get("total_assets_range", ""), u.get("total_assets_range", "未设置"))
            focus     = ", ".join(m.get("focus_news_types", [])) or "未设置"
            focus_stk = ", ".join(m.get("focus_stocks", [])) or "未设置"

            user_section = f"""
## 用户画像（必须据此调整报告风格）

**投资风格**: {style}
**风险偏好**: {risk}
**操作周期**: {freq}
**资产规模**: {assets}
**关注领域**: {focus}
**关注标的**: {focus_stk}

⚠️ **铁律：你必须根据以上用户画像调整报告内容！**
- 保守型/低风险用户：侧重低估值、高股息、防御性标的，仓位控制更严格，止损更窄
- 积极型/高风险用户：可覆盖追涨、打板、连板接力等激进策略
- 平衡型用户：确定性仓位为主，博弈性仓位为辅
- 报告中的仓位配比、止损幅度、持股周期、选股风格必须与用户画像一致
- 不同用户收到的报告内容应有实质性差异，禁止写万能模板
"""

        content = f"""# 🦞 龙虾调研 Agent 工作简报

**任务ID**: {meta['task_id']}
**报告类型**: {meta['label']} (`{meta['report_type']}`)
**日期**: {meta['date']}
**任务目录**: {self.task_dir}
{template_line}
{user_section}

---

## Phase 1 数据采集结果（代码已完成）

以下文件已由程序自动生成，供你参考：

{files_list}
每个文件都有 `agent_note` 字段说明你需要从中提取什么。
{sources_section}
---

## Phase 2 你的任务：整合 + 补充

### 第一步：检查数据完整性
{data_check_text}

### 第二步：补充搜索
以下关键词搜索结果已在 4_search_keyword_*.json 中，**但你仍可自行补充搜索**
来获取更新、更深入的信息：
{search_list}
{core_idea_section}

### 第三步：填写 5_agent_report_input.json
按大纲结构，把分析内容填入 `5_agent_report_input.json`。
**填写质量决定报告质量。**
{structure_section}
---

## 5_agent_report_input.json 填写模板

```json
{schema_str}
```

---

## 填写完成后

运行：
```powershell
python main.py generate --task-id {meta['task_id']}
```

---

**提示**：{meta['agent_hint']}
"""
        briefing_path = os.path.join(self.task_dir, "5_agent_briefing.md")
        with open(briefing_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 同时写入空的 5_agent_report_input.json 占位
        schema_path = os.path.join(self.task_dir, "5_agent_report_input.json")
        if not os.path.exists(schema_path):
            with open(schema_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)

    def _get_agent_input_schema(self, meta: dict) -> dict:
        """
        返回 5_agent_report_input.json 的结构模板（带注释字段）
        根据报告类型给出对应结构。
        如果 meta 中有 prompt_template，会把 promptBody 作为参考注入。
        """
        report_type = meta.get("report_type", "gupiao_fenxi")
        stock_name = meta["args"].get("name", "")
        stock_code = meta["args"].get("code", "")
        today      = meta.get("date", datetime.now().strftime("%Y-%m-%d"))
        tpl = meta.get("prompt_template", {})

        # 通用元数据
        base = {
            "_fill_instructions": "请删除所有以_开头的注释字段，填入真实内容后保存",
            "_task_id": meta["task_id"],
            "_report_type": report_type,

            # 报告基础信息（必填）
            "title":    f"{stock_name or '报告主题'} - {meta['label']}",
            "subtitle": "深度分析 · 数据驱动",
            "date":     today,
            "author":   "🦞 龙虾财经研究院",
            "summary":  "_AI从数据文件和搜索结果中提炼，200字以内的核心摘要",
            "quote":    "投资不是赌方向，而是计算概率与赔率后的理性决策。",
            "disclaimer": "免责声明：本报告由AI生成，数据来源于公开网络，仅供参考，不构成投资建议。",
        }

        # 按报告类型添加特定字段
        if report_type in ("gupiao_fenxi", "qiye_baogao"):
            base.update({
                "metrics": [
                    {"label": "当前股价", "value": "_从2_stock_quote_realtime.json提取", "change": "_涨跌幅"},
                    {"label": "技术评分", "value": "_从2_stock_kline_indicator.json提取", "change": "_评级"},
                    {"label": "市盈率PE", "value": "_从搜索结果提取", "change": ""},
                    {"label": "52周区间", "value": "_高/低", "change": ""},
                ],
                "overview_table": {
                    "headers": ["维度", "评估", "信号", "要点"],
                    "rows": [
                        ["近期表现", "_5日/20日涨跌", "_🟢🟡🔴", "_摘要"],
                        ["技术趋势", "_短/中期趋势", "_信号", "_评分"],
                        ["基本面",   "_业绩评估", "_信号", "_核心数据"],
                        ["机构评级", "_买入/增持等", "_👍", "_目标价"],
                        ["短期建议", "_操作建议", "_", "_目标价"],
                    ]
                },
                "sections": [
                    {
                        "title": "🦞 行情指标与投资导航",
                        "subsections": [
                            {
                                "title": "近期表现",
                                "content": "_基于2_stock_quote_realtime.json和2_stock_kline_indicator.json的技术分析，200-300字",
                            },
                            {
                                "title": "机构观点与投资建议",
                                "content": "_基于搜索结果整理，≥3家券商评级，300字",
                            }
                        ]
                    },
                    {
                        "title": "一、公司概况",
                        "subsections": [
                            {"title": "基本信息与主营业务", "content": "_从2_stock_info_detail.json和搜索提取，300字"},
                            {"title": "核心竞争力与护城河", "content": "_分析竞争优势，200字"},
                        ]
                    },
                    {
                        "title": "二、财务分析",
                        "subsections": [
                            {
                                "title": "核心财务指标",
                                "content": "_营收/利润/毛利率/ROE近3年数据，300字",
                                "table": {
                                    "headers": ["指标", "2023", "2024", "2025E", "趋势"],
                                    "rows": [
                                        ["营收(亿元)", "_", "_", "_", "_"],
                                        ["净利润(亿元)", "_", "_", "_", "_"],
                                        ["毛利率", "_", "_", "_", "_"],
                                        ["ROE", "_", "_", "_", "_"],
                                    ]
                                }
                            },
                        ]
                    },
                    {
                        "title": "三、行业与竞争",
                        "subsections": [
                            {"title": "行业发展趋势", "content": "_行业规模、增速、政策，200字"},
                            {"title": "竞争格局", "content": "_主要竞争对手、市场份额，200字"},
                        ]
                    },
                    {
                        "title": "四、投资亮点与风险",
                        "subsections": [
                            {"title": "核心投资亮点", "content": "_3-5个亮点，每个2-3句话"},
                            {
                                "title": "主要风险因素",
                                "content": "_3-5个风险，每个2-3句话",
                                "table": {
                                    "headers": ["风险类别", "描述", "影响", "概率", "应对"],
                                    "rows": [["_", "_", "_", "_", "_"]]
                                }
                            }
                        ]
                    },
                    {
                        "title": "五、估值与投资建议",
                        "subsections": [
                            {"title": "估值分析", "content": "_PE/PB/目标价分析，200字"},
                            {"title": "综合投资建议", "content": "_短期/中期/长期建议，200字"},
                        ]
                    }
                ]
            })

        elif report_type == "dapan_ribao":
            base.update({
                "metrics": [
                    {"label": "上证指数", "value": "_点位", "change": "_涨跌幅"},
                    {"label": "深证成指", "value": "_点位", "change": "_涨跌幅"},
                    {"label": "创业板",   "value": "_点位", "change": "_涨跌幅"},
                    {"label": "北向资金", "value": "_亿元", "change": ""},
                ],
                "sections": [
                    {
                        "title": "🦞 大盘概况",
                        "subsections": [
                            {"title": "今日行情",      "content": "_基于1_market_index_tick.json，200字"},
                            {"title": "市场情绪信号",   "content": "_涨跌停、情绪指标，200字"},
                        ]
                    },
                    {
                        "title": "一、板块动态",
                        "subsections": [
                            {"title": "强势板块",  "content": "_今日领涨板块，200字"},
                            {"title": "弱势板块",  "content": "_调整板块，100字"},
                        ]
                    },
                    {
                        "title": "二、资金面",
                        "subsections": [
                            {"title": "北向资金", "content": "_动向分析，150字"},
                            {"title": "融资融券", "content": "_余额变化，100字"},
                        ]
                    },
                    {
                        "title": "🦞 龙虾总结",
                        "subsections": [
                            {"title": "操作建议", "content": "_明日策略建议，200字",
                             "highlight": "_核心判断一句话"},
                        ]
                    }
                ]
            })

        elif report_type == "hangye_baogao":
            topic = meta["args"].get("topic", "")
            base.update({
                "sections": [
                    {
                        "title": "🦞 行业核心速览",
                        "subsections": [
                            {"title": "行业概况", "content": "_市场规模、增速，200字"},
                            {"title": "投资评级", "content": "_机构整体评级，150字"},
                        ]
                    },
                    {"title": "一、行业全景",
                     "subsections": [
                         {"title": "市场规模与增速", "content": "_数据+图示，300字"},
                         {"title": "产业链结构",    "content": "_上中下游，200字"},
                     ]},
                    {"title": "二、竞争格局",
                     "subsections": [
                         {"title": "龙头企业分析", "content": "_3-5家核心企业，300字",
                          "table": {"headers": ["企业", "市占率", "核心优势", "评级"],
                                    "rows": [["_","_","_","_"]]}},
                     ]},
                    {"title": "三、政策与催化剂",
                     "subsections": [
                         {"title": "政策支持", "content": "_近期政策梳理，200字"},
                         {"title": "技术催化", "content": "_技术突破点，200字"},
                     ]},
                    {"title": "四、投资机会与风险",
                     "subsections": [
                         {"title": "核心投资机会", "content": "_3个机会，每个100字"},
                         {"title": "主要风险",     "content": "_3个风险，每个100字"},
                     ]},
                    {"title": "🦞 龙虾总结",
                     "subsections": [
                         {"title": "配置建议", "content": "_超配/标配/低配及理由，200字",
                          "highlight": "_核心判断"},
                     ]},
                ]
            })

        else:
            # 通用结构
            base["sections"] = [
                {
                    "title": "一、核心概况",
                    "subsections": [{"title": "概览", "content": "_综合所有数据文件，300字"}]
                },
                {
                    "title": "二、详细分析",
                    "subsections": [{"title": "分析", "content": "_深入分析，500字"}]
                },
                {
                    "title": "🦞 龙虾总结",
                    "subsections": [{"title": "结论与建议", "content": "_结论，200字",
                                     "highlight": "_一句话判断"}]
                }
            ]

        # 注入 prompt 模板的参考信息（以下划线开头，会被清理）
        if tpl:
            if tpl.get("promptBody"):
                base["_prompt_body"] = tpl["promptBody"]
            if tpl.get("coreIdea"):
                base["_core_idea"] = tpl["coreIdea"]
            if tpl.get("dataRequirements"):
                base["_data_requirements"] = tpl["dataRequirements"]
            if tpl.get("recommendedDataSources"):
                base["_data_sources"] = tpl["recommendedDataSources"]

        return base

    # ─────────────────────────────────────────────────────────
    # Phase 3: 生成报告
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _fix_json_chinese_quotes(raw: str) -> str:
        """
        自动修复 JSON 字符串值中的中文引号冲突。
        Agent 填写内容时常用 ASCII 双引号 "..." 表示中文引用，
        但 ASCII " 在 JSON 中是字符串定界符，会导致解析失败。
        本方法将成对的、非 JSON 结构性的 " 替换为 Unicode 中文引号 "..."。
        """
        result = []
        i = 0
        in_string = False
        escape_next = False

        while i < len(raw):
            c = raw[i]

            # 处理转义字符
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

            if c == '"':
                if not in_string:
                    in_string = True
                    result.append(c)
                else:
                    # 判断这个 " 是 JSON 字符串终止符还是内容中的中文引号
                    rest = raw[i + 1:].lstrip()
                    # 如果后面紧跟 JSON 结构字符 → 是真正的终止符
                    if rest and rest[0] in ':,]}\n\r':
                        in_string = False
                        result.append(c)
                    elif rest and rest[0] == '"':
                        # "key": "value" 或 "key": "" 的情况 → 终止符
                        in_string = False
                        result.append(c)
                    else:
                        # 内容中的中文引号，向前找配对的闭合引号
                        j = i + 1
                        close_pos = -1
                        while j < len(raw):
                            if raw[j] == '"':
                                rest2 = raw[j + 1:].lstrip()
                                # 闭合引号后面也应该是非 JSON 结构字符
                                if rest2 and rest2[0] in ':,]}\n\r':
                                    break  # 这是真正的字符串终止符，不是配对
                                elif rest2 and rest2[0] == '"':
                                    break  # 也不是配对
                                else:
                                    close_pos = j
                                    break
                            j += 1

                        if close_pos > 0:
                            inner = raw[i + 1:close_pos]
                            result.append('\u201c')   # "
                            result.append(inner)
                            result.append('\u201d')   # "
                            i = close_pos + 1
                            continue
                        else:
                            # 找不到配对，当作终止符处理
                            in_string = False
                            result.append(c)

                i += 1
                continue

            result.append(c)
            i += 1

        return ''.join(result)

    def generate_report(self, agent_input_path: str) -> Tuple[bool, dict]:
        """
        读取 5_agent_report_input.json，调用 generate_report 生成 HTML + PDF

        返回:
            (ok, result_dict) 其中 result_dict 包含:
                - pdf_path: PDF 文件路径
                - html_path: HTML 文件路径
                - error: 失败时的错误信息
        """
        try:
            with open(agent_input_path, encoding="utf-8") as f:
                raw_text = f.read()

            # 第一次尝试：直接解析
            try:
                report_data = json.loads(raw_text)
            except json.JSONDecodeError:
                # 自动修复中文引号冲突后重试
                fixed_text = self._fix_json_chinese_quotes(raw_text)
                report_data = json.loads(fixed_text)
                # 将修复后的 JSON 回写文件，避免下次再出错
                with open(agent_input_path, "w", encoding="utf-8") as f:
                    f.write(fixed_text)

            # 清理 _开头的注释字段
            report_data = self._clean_schema_comments(report_data)

            report_type = self.meta.get("report_type", "gupiao_fenxi")
            style       = self.meta["args"].get("style", "blue")
            task_id     = self.meta["task_id"]

            from scripts.generate_report import generate_report
            result = generate_report(
                user_input=f"{report_data.get('title', '')}",
                explicit_type=report_type,
                data=report_data,
                output_format="pdf",
                output_path=os.path.join(self.task_dir, f"report_{task_id}.pdf"),
                style=style,
            )

            if result.get("success"):
                pdf_path = result.get("path", "")
                html_path = result.get("html_path", "")
                # 降级为 HTML 时，path 本身就是 html_path
                if not html_path:
                    html_path = pdf_path
                # 确保 html_path 存在（有些情况 PDF 生成失败会降级）
                if pdf_path.endswith(".html"):
                    html_path = pdf_path
                return True, {"pdf_path": pdf_path, "html_path": html_path}
            else:
                return False, {"error": result.get("error", "未知错误")}

        except Exception as e:
            return False, {"error": str(e)}

    # ─────────────────────────────────────────────────────────
    # Step 6: 百度新闻快讯
    # ─────────────────────────────────────────────────────────

    def run_baidu_news(self, channels: List[str] = None, limit: int = 10) -> Tuple[bool, str]:
        """
        从百度新闻 RSS 采集快讯，写入 04_daily_news.json

        channels: 频道关键词列表，如 ["财经", "科技", "社会"]
                  None 时默认采集 财经+科技+社会 三个频道
        limit:    每个频道最多条数
        """
        BAIDU_CHANNELS = {
            "国际焦点": "http://news.baidu.com/n?cmd=1&class=internews&tn=rss",
            "军事焦点": "http://news.baidu.com/n?cmd=1&class=mil&tn=rss",
            "财经焦点": "http://news.baidu.com/n?cmd=1&class=finannews&tn=rss",
            "互联网焦点": "http://news.baidu.com/n?cmd=1&class=internet&tn=rss",
            "科技焦点": "http://news.baidu.com/n?cmd=1&class=technnews&tn=rss",
            "社会焦点": "http://news.baidu.com/n?cmd=1&class=socianews&tn=rss",
            "房产焦点": "http://news.baidu.com/n?cmd=1&class=housenews&tn=rss",
            "汽车焦点": "http://news.baidu.com/n?cmd=1&class=autonews&tn=rss",
        }

        import requests as _req
        import xml.etree.ElementTree as ET
        import re as _re

        def _clean(s):
            if not s:
                return ""
            s = _re.sub(r'<.*?>', '', s)
            s = _re.sub(r'&nbsp;|&quot;|&amp;|&lt;|&gt;', ' ', s)
            return _re.sub(r'\s+', ' ', s).strip()

        def _fetch(channel_name, url, lim):
            items = []
            try:
                resp = _req.Session().get(url, timeout=5)
                resp.encoding = 'utf-8'
                root = ET.fromstring(resp.text)
                for item in root.findall("./channel/item"):
                    if len(items) >= lim:
                        break
                    items.append({
                        "title":   _clean(item.findtext("title", "")),
                        "desc":    _clean(item.findtext("description", ""))[:200],
                        "pubDate": item.findtext("pubDate", "")[:19],
                        "channel": channel_name,
                    })
            except Exception as e:
                items.append({"title": f"获取失败: {e}", "channel": channel_name})
            return items

        # 确定要采集的频道
        if channels is None:
            channels = ["财经", "科技", "社会"]

        target_channels = {}
        for kw in channels:
            for name, url in BAIDU_CHANNELS.items():
                if kw in name:
                    target_channels[name] = url
                    break

        all_news = []
        channel_stats = {}
        for name, url in target_channels.items():
            items = _fetch(name, url, limit)
            all_news.extend(items)
            channel_stats[name] = len(items)

        data = {
            "_meta": {
                "step": "baidu_news",
                "channels": list(target_channels.keys()),
                "total": len(all_news),
                "channel_stats": channel_stats,
                "fetched_at": datetime.now().isoformat(),
            },
            "news": all_news,
            "agent_note": "请从以上新闻中提取与报告主题相关的重要资讯，整合进报告的新闻动态章节",
        }
        path = self._write_json("3_news_daily_all.json", data)
        return bool(all_news), path

    # ─────────────────────────────────────────────────────────
    # Step 7: AKShare 结构化金融数据
    # ─────────────────────────────────────────────────────────

    def run_akshare_data(self, stock_code: str = "") -> Tuple[bool, str]:
        """
        采集 AKShare 结构化金融数据，写入 1_market_akshare_macro.json
        包含：个股新闻、北向资金、今日资金流排名
        stock_code: 有值时额外采集个股新闻（如 "000063"）
        """
        try:
            import akshare as ak
            import pandas as pd

            result = {
                "_meta": {
                    "step": "akshare",
                    "stock_code": stock_code,
                    "fetched_at": datetime.now().isoformat(),
                },
                "agent_note": "北向资金、融资融券、个股新闻等结构化数据，请整合进报告相关章节",
            }

            # 1. 个股新闻（有 stock_code 时）
            if stock_code:
                try:
                    df = ak.stock_news_em(symbol=stock_code)
                    cols = [c for c in ["发布时间", "新闻标题", "新闻内容", "文章来源"] if c in df.columns]
                    news_rows = df[cols].head(15).to_dict(orient="records")
                    result["stock_news"] = news_rows
                except Exception as e:
                    result["stock_news"] = [{"error": str(e)}]

            # 2. 北向资金概览
            try:
                df = ak.stock_hsgt_fund_flow_summary_em()
                result["hsgt_fund_flow"] = df.to_dict(orient="records")
            except Exception as e:
                result["hsgt_fund_flow"] = [{"error": str(e)}]

            # 3. 今日资金流排名（前20）
            try:
                df = ak.stock_individual_fund_flow_rank(indicator="今日")
                result["fund_flow_rank"] = df.head(20).to_dict(orient="records")
            except Exception as e:
                result["fund_flow_rank"] = [{"error": str(e)}]

            # 4. 融资融券余额（市场整体）
            try:
                df = ak.stock_margin_sse_summary()
                result["margin_summary"] = df.tail(5).to_dict(orient="records")
            except Exception as e:
                result["margin_summary"] = [{"error": str(e)}]

            path = self._write_json("1_market_akshare_macro.json", result)
            return True, path

        except Exception as e:
            data = {
                "_meta": {"step": "akshare", "error": str(e)},
                "agent_note": f"AKShare 数据采集失败: {e}",
            }
            path = self._write_json("1_market_akshare_macro.json", data)
            return False, path

    # ─────────────────────────────────────────────────────────
    # Step 8: 大盘整体状况（Playwright 爬取新浪行情页）
    # ─────────────────────────────────────────────────────────

    def run_market_state(self) -> Tuple[bool, str]:
        """
        通过 market_state.py 爬取新浪行情页，获取大盘整体状况
        使用 --output 直接写入 1_market_status_sina.json（不再解析 stdout）
        """
        out_path = os.path.join(self.task_dir, "1_market_status_sina.json")
        try:
            ok, stdout = self._run_script(
                ["scripts/market_state.py", "--output", out_path, "--format", "rawtext"],
                timeout=60,
            )
            if ok and os.path.exists(out_path):
                return True, out_path
            # 即使返回码非0，文件可能已部分写入
            if os.path.exists(out_path) and os.path.getsize(out_path) > 50:
                return True, out_path
            # 写一个带错误信息的兜底文件
            data = {
                "_meta": {"step": "market_state", "fetched_at": datetime.now().isoformat(), "run_success": False},
                "raw_html": "",
                "raw_text": stdout[:5000] if stdout else "",
                "agent_note": f"大盘状况采集失败: {stdout[:200]}" if stdout else "大盘状况采集失败",
            }
            path = self._write_json("1_market_status_sina.json", data)
            return False, path
        except Exception as e:
            data = {
                "_meta": {"step": "market_state", "error": str(e)},
                "raw_html": "",
                "raw_text": "",
                "agent_note": f"大盘状况采集失败: {e}",
            }
            path = self._write_json("1_market_status_sina.json", data)
            return False, path

    # ─────────────────────────────────────────────────────────
    # Step 9: 图片解析（持仓截图 → 结构化数据）
    # ─────────────────────────────────────────────────────────

    def run_parse_image(self, image_path: str) -> Tuple[bool, str]:
        """
        调用 parse_image.py 解析持仓截图，写入 0_portfolio_img__parse.json
        image_path: 用户上传的图片绝对路径
        """
        out_path = os.path.join(self.task_dir, "0_portfolio_img__parse.json")
        try:
            ok, stdout = self._run_script(
                ["scripts/parse_image.py", image_path, out_path],
                timeout=120,
            )

            # parse_image.py 会自己写 out_path，直接读取
            if os.path.exists(out_path):
                with open(out_path, encoding="utf-8") as f:
                    parsed = json.load(f)

                # 补充 _meta
                parsed["_meta"] = {
                    "step": "parse_image",
                    "image_path": image_path,
                    "fetched_at": datetime.now().isoformat(),
                    "run_success": ok,
                }
                parsed["agent_note"] = (
                    "这是用户持仓截图的解析结果。"
                    "type 字段说明图片类型，stocks 字段包含持仓明细。"
                    "请基于此数据进行持仓诊断分析。"
                )
                # 重新写入（加了 _meta）
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, ensure_ascii=False, indent=2)

                return True, out_path
            else:
                # parse_image 没有写文件，把 stdout 存下来
                data = {
                    "_meta": {
                        "step": "parse_image",
                        "image_path": image_path,
                        "fetched_at": datetime.now().isoformat(),
                        "run_success": False,
                    },
                    "raw_output": stdout[:5000],
                    "agent_note": "图片解析未生成结构化文件，请参考 raw_output 手动提取持仓信息",
                }
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return False, out_path

        except Exception as e:
            data = {
                "_meta": {"step": "parse_image", "error": str(e)},
                "agent_note": f"图片解析失败: {e}",
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return False, out_path

    # ═══════════════════════════════════════════════════════════
    # 预留步骤：注册路由但尚未实现，创建占位 JSON 文件
    # ═══════════════════════════════════════════════════════════
    # 3_ — 快讯类
    #   news_market_flash  → 3_news_market_flash.json
    #   news_stock_flash   → 3_news_stock_flash.json
    # 4_ — 搜索类
    #   search_research    → 4_search_research_report.json
    #   search_market_batch→ 4_search_market_batch.json
    #   search_stock_batch → 4_search_stock_batch.json
    # 6_ — 模拟盘类
    #   emu_portfolio      → 6_emu_portfolio.json
    #   emu_operation      → 6_emu_operation_log.json
    #   emu_reflection     → 6_emu_reflection_review.json

    _RESERVED_STEP_FILES = {
        "news_market_flash":   "3_news_market_flash.json",
        "news_stock_flash":    "3_news_stock_flash.json",
        "search_research":     "4_search_research_report.json",
        "search_market_batch": "4_search_market_batch.json",
        "search_stock_batch":  "4_search_stock_batch.json",
        "emu_portfolio":       "6_emu_portfolio.json",
        "emu_operation":       "6_emu_operation_log.json",
        "emu_reflection":      "6_emu_reflection_review.json",
    }

    def run_reserved_step(self, step: str) -> Tuple[bool, str]:
        """预留步骤 stub：创建占位 JSON，不执行实际数据采集"""
        filename = self._RESERVED_STEP_FILES.get(step, f"{step}.json")
        data = {
            "_meta": {
                "step": step,
                "status": "reserved_placeholder",
                "note": "此步骤尚未实现具体逻辑，当前为占位文件",
                "fetched_at": datetime.now().isoformat(),
            },
            "data": {},
            "agent_note": f"🟡 步骤「{step}」({filename}) 尚未实现。请手动补充所需数据后继续。",
        }
        path = self._write_json(filename, data)
        return True, path

    def _clean_schema_comments(self, obj: Any) -> Any:
        """递归删除 JSON 中所有以 _ 开头的注释字段"""
        if isinstance(obj, dict):
            return {
                k: self._clean_schema_comments(v)
                for k, v in obj.items()
                if not k.startswith("_")
            }
        elif isinstance(obj, list):
            return [self._clean_schema_comments(item) for item in obj]
        return obj
