# -*- coding: utf-8 -*-
"""
龙虾调研助手 — Alone 模式独立运行引擎
=========================================
职责：Phase 2 自动生成报告，无需 Agent 介入。

工作流：
  1. consolidate: 读取所有数据文件 → 合并为 5_agent_briefing.json
  2. pick_api: 根据配置选择 LLM 提供商（kimi / mimo / deepseek）
  3. call_llm: OpenAI 兼容接口调用，带工具调用（function calling）
  4. tool_call → 写入 5_agent_report_input.json
  5. 无工具调用 → CLI 纯文本输出或降级为 MD 保存
"""
from __future__ import annotations

import io, json, os, sys, requests, copy
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import get_settings, get

# 质量校验
from scripts.validate_quality import check_report_input, format_quality_report


# ─────────────────────────────────────────────────────────
# API 提供商配置
# ─────────────────────────────────────────────────────────
_API_PROVIDERS = {
    "kimi": {
        "key_field":   "kimi_api_key",
        "base_field":  "kimi_base_url",
        "model_field": "kimi_model",
        "default_base": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
    },
    "mimo": {
        "key_field":   "mimo_api_key",
        "base_field":  "mimo_base_url",
        "model_field": "mimo_model",
        "default_base": "https://api.minimax.chat/v1",
        "default_model": "minimax-text-01",
    },
    "deepseek": {
        "key_field":   "deepseek_api_key",
        "base_field":  "deepseek_base_url",
        "model_field": "deepseek_model",
        "default_base": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
}

# API 尝试顺序
_API_ORDER = ["kimi", "mimo", "deepseek"]


def _load_file_content(path: str, max_chars: int = 8000) -> str:
    """读取文件内容，超大文件截断"""
    if not path or not os.path.exists(path):
        return "（文件不存在）"
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if len(text) > max_chars:
            return text[:max_chars] + f"\n...（截断，原长 {len(text)} 字符）"
        return text
    except Exception as e:
        return f"（读取失败: {e}）"


def consolidate_briefing(task_dir: str, meta: dict) -> dict:
    """
    将所有数据文件 + 指令合并为一个 dict，供 LLM 上下文使用。
    返回:
      {
        "task_id": "...",
        "report_type": "...",
        "agent_hint": "...",
        "data_files": { "market_index": {content...}, "search": [...] },
        "report_schema": { ... },  # 用于工具调用的 schema
        "briefing_text": "...",    # 给 LLM 的纯文本版本
      }
    """
    files = meta.get("files", {})
    data_files = {}

    for key, val in files.items():
        if isinstance(val, list):
            items = []
            for p in val:
                content = _load_file_content(p)
                items.append({"path": os.path.basename(p), "content": content})
            data_files[key] = items
        elif val:
            content = _load_file_content(val)
            data_files[key] = {"path": os.path.basename(val), "content": content}

    # 从 task_runner 获取 schema（直接 import 复用）
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scripts.task_runner import TaskRunner
    runner = TaskRunner.__new__(TaskRunner)
    runner.task_dir = task_dir
    runner.meta = meta
    runner.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema = runner._get_agent_input_schema(meta)

    # 构建纯文本版本给 LLM
    briefing_text = f"""# 龙虾调研 - Agent 任务简报

## 任务信息
- 任务ID: {meta['task_id']}
- 报告类型: {meta.get('label', '')} ({meta.get('report_type', '')})
- 日期: {meta.get('date', '')}

## 任务说明
{meta.get('agent_hint', '')}

## 数据文件
"""
    for key, val in files.items():
        if isinstance(val, list):
            for p in val:
                briefing_text += f"- {os.path.basename(p)}\n"
        elif val:
            briefing_text += f"- {os.path.basename(val)}\n"

    briefing_text += f"""
## 输出结构要求

请按以下 JSON Schema 填充 5_agent_report_input.json：

```json
{json.dumps(schema, ensure_ascii=False, indent=2)}
```

所有以 _ 开头的字段是注释占位，需填入实际内容后删除 _ 前缀。
"""
    search_queries = meta.get("search_queries", [])
    if search_queries:
        briefing_text += "\n## 可补充搜索关键词\n"
        for q in search_queries:
            briefing_text += f"- {q}\n"

    return {
        "task_id": meta["task_id"],
        "report_type": meta.get("report_type", ""),
        "agent_hint": meta.get("agent_hint", ""),
        "data_files": data_files,
        "report_schema": schema,
        "briefing_text": briefing_text,
    }


def pick_api(settings: dict, preferred: str = "kimi") -> dict:
    """
    根据配置和可用 API Key 选择 LLM 提供商。
    返回: {"base_url": "...", "api_key": "...", "model": "..."}
    失败: 抛出 ValueError
    """
    apis = settings.get("apis", {})

    # 如果 preferred 有 key，优先用它
    if preferred in _API_PROVIDERS:
        cfg = _API_PROVIDERS[preferred]
        key = apis.get(cfg["key_field"], "").strip()
        if key:
            base = apis.get(cfg["base_field"], "") or cfg["default_base"]
            model = apis.get(cfg["model_field"], "") or cfg["default_model"]
            return {"base_url": base.rstrip("/"), "api_key": key, "model": model}

    # 按顺序找第一个有 key 的
    for name in _API_ORDER:
        cfg = _API_PROVIDERS[name]
        key = apis.get(cfg["key_field"], "").strip()
        if key:
            base = apis.get(cfg["base_field"], "") or cfg["default_base"]
            model = apis.get(cfg["model_field"], "") or cfg["default_model"]
            return {"base_url": base.rstrip("/"), "api_key": key, "model": model}

    raise ValueError(
        "❌ 未找到可用的 LLM API Key。请先在 settings.json 的 apis 段配置：\n"
        "   kimi_api_key / mimo_api_key / deepseek_api_key\n"
        "   或用命令配置: python config/config.py settings set apis.kimi_api_key YOUR_KEY"
    )


def call_llm(api_cfg: dict, briefing: dict, task_dir: str) -> dict:
    """
    调用 OpenAI 兼容 API，支持工具调用。
    如果工具调用成功 → 写 5_agent_report_input.json
    如果失败        → 返回纯文本
    返回: {"success": True, "tool_called": True/False, "output": "...", "path": "..."}
    """
    system_msg = {
        "role": "system",
        "content": (
            "你是🦞龙虾财经研究院的资深分析师。你的任务是：\n"
            "1. 读取用户提供的所有数据文件和任务说明\n"
            "2. 基于数据进行分析，生成完整报告\n"
            "3. 使用 write_report_input_json 工具将结果写入 5_agent_report_input.json\n"
            "4. 如果无法使用工具，请直接输出完整的报告 Markdown 内容\n\n"
            "注意：所有_开头的字段是占位注释，请填入实际数据后去掉_前缀。"
        ),
    }

    user_msg = {
        "role": "user",
        "content": briefing["briefing_text"],
    }

    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "write_report_input_json",
                "description": "将完整的报告数据以 JSON 格式写入 5_agent_report_input.json",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report_json": {
                            "type": "string",
                            "description": "完整的 5_agent_report_input.json 内容，合法的 JSON 字符串",
                        }
                    },
                    "required": ["report_json"],
                },
            },
        }
    ]

    url = f"{api_cfg['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_cfg['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": api_cfg["model"],
        "messages": [system_msg, user_msg],
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.3,
        "max_tokens": 16384,
    }

    print(f"\n  🌐 调用 API: {api_cfg['base_url']} | 模型: {api_cfg['model']}")
    print(f"  ⏳ 等待响应...", end="", flush=True)

    result = {"success": False, "tool_called": False, "output": "", "path": "", "error": ""}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
            print(f"\n  ❌ {result['error']}")
            return result

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "")

        # 检查工具调用
        tool_calls = message.get("tool_calls", [])
        if tool_calls and finish_reason == "tool_calls":
            for tc in tool_calls:
                func = tc.get("function", {})
                if func.get("name") == "write_report_input_json":
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                        report_json_str = args.get("report_json", "")
                        report_data = json.loads(report_json_str)
                    except (json.JSONDecodeError, KeyError):
                        # arguments 直接是 JSON 字符串，无需 report_json 包装
                        try:
                            report_data = json.loads(func.get("arguments", "{}"))
                        except json.JSONDecodeError:
                            result["error"] = "工具参数 JSON 解析失败"
                            print(f"\n  ❌ {result['error']}")
                            return result

            # 写入文件
            out_path = os.path.join(task_dir, "5_agent_report_input.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            # 清理 _ 注释字段
            clean_data = _remove_meta_keys(report_data)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=2)

            result["success"] = True
            result["tool_called"] = True
            result["output"] = "工具调用成功，已写入 5_agent_report_input.json"
            result["path"] = out_path
            print(f"\n  ✅ 工具调用成功 → {os.path.basename(out_path)}")

        else:
            # 无工具调用 — 纯文本输出
            content = message.get("content", "")
            result["success"] = True
            result["tool_called"] = False
            result["output"] = content
            print(f"\n  💬 收到文本响应（{len(content)} 字符）")

    except requests.exceptions.Timeout:
        result["error"] = "API 请求超时（120s）"
        print(f"\n  ❌ {result['error']}")
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"API 连接失败: {e}"
        print(f"\n  ❌ {result['error']}")
    except Exception as e:
        result["error"] = str(e)
        print(f"\n  ❌ {result['error']}")

    return result


def _remove_meta_keys(obj):
    """递归删除 JSON 中所有以 _ 开头的 key"""
    if isinstance(obj, dict):
        return {k: _remove_meta_keys(v) for k, v in obj.items() if not k.startswith("_")}
    elif isinstance(obj, list):
        return [_remove_meta_keys(item) for item in obj]
    return obj


def run_alone_mode(task_dir: str, meta: dict, project_root: str) -> dict:
    """
    独立运行入口 — 被 main.py 调用。

    返回:
      {"success": True/False, "mode": "alone", "tool_called": True/False, ...}
    """
    result = {"success": False, "mode": "alone", "tool_called": False,
              "output": "", "path": "", "error": ""}

    # Step 1: Consolidate
    print("\n  📦 合并数据文件...")
    briefing = consolidate_briefing(task_dir, meta)
    print(f"     数据文件: {len(briefing['data_files'])} 项")

    # 写合并后的 5_agent_briefing.json
    briefing_path = os.path.join(task_dir, "5_agent_briefing.json")
    with open(briefing_path, "w", encoding="utf-8") as f:
        # 只存数据内容，不含 briefing_text（冗余）
        write_data = copy.deepcopy(briefing)
        write_data.pop("briefing_text", None)
        json.dump(write_data, f, ensure_ascii=False, indent=2)

    # Step 2: 选择 API
    settings = get_settings()
    alone_cfg = get("alone", {})
    preferred = alone_cfg.get("preferred_api", "kimi")

    try:
        api_cfg = pick_api(settings, preferred)
    except ValueError as e:
        result["error"] = str(e)
        print(f"\n  ❌ {e}")
        print("  💡 降级为 skill 模式，等待 Agent 手动处理")
        return result

    # Step 3: 调用 LLM（带质量校验重试）
    max_retries = alone_cfg.get("quality_max_retries", 2)
    retry_feedback = ""
    api_result = None

    for attempt in range(1, max_retries + 2):  # 首次 + N 次重试
        if retry_feedback:
            print(f"\n  🔄 重试第 {attempt-1} 次（质量不达标）...")
            # 动态注入反馈到 system prompt
            _briefing = copy.deepcopy(briefing)
            _briefing["briefing_text"] += f"\n\n## 上一版质量问题\n{retry_feedback}\n\n请针对以上问题改进报告内容，特别是篇幅和数据丰富度。"
        else:
            _briefing = briefing

        api_result = call_llm(api_cfg, _briefing, task_dir)
        if not api_result["success"]:
            result["error"] = api_result.get("error", "API 调用失败")
            return result

        # 仅当工具调用成功时进行质量校验
        if api_result.get("tool_called"):
            input_path = os.path.join(task_dir, "5_agent_report_input.json")
            try:
                with open(input_path, encoding="utf-8") as f:
                    report_data = json.load(f)
                quality = check_report_input(report_data, meta.get("prompt_template"))
                print(f"  {format_quality_report(quality)}")

                if quality["ok"] and not quality["warnings"]:
                    print(f"  ✅ 质量校验通过（第 {attempt} 次）")
                    break  # 合格，退出重试循环
                else:
                    # 构造反馈
                    retry_feedback = "\n".join(quality["warnings"][:5])
                    if attempt <= max_retries:
                        print(f"  ⚠️ 质量不合格，剩余重试 {max_retries - attempt + 1} 次")
                        # 重置 api_result 使循环继续
                        continue
                    else:
                        print(f"  ⚠️ 已达最大重试次数，使用当前结果")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                retry_feedback = f"JSON 文件问题: {e}"
                if attempt <= max_retries:
                    print(f"  ⚠️ JSON 读取失败，剩余重试 {max_retries - attempt + 1} 次")
                    continue
        else:
            # 无工具调用，无法校验
            break

    result["success"] = True
    result["tool_called"] = api_result["tool_called"]
    result["output"] = api_result["output"]
    result["path"] = api_result.get("path", "")

    # Step 4: 处理输出模式
    output_mode = alone_cfg.get("output_mode", "cli")

    if not api_result["tool_called"] and api_result["output"]:
        # 无工具调用，纯文本输出
        text = api_result["output"]
        if output_mode == "cli":
            print(f"\n{'─'*60}")
            print("📋 Alone 模式报告（纯文本）")
            print(f"{'─'*60}\n")
            print(text)
            print(f"\n{'─'*60}")
        else:
            # report 模式：保存为 MD，然后走 generate 生成 HTML+PDF
            md_path = os.path.join(task_dir, "report_alone.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"\n  📄 报告文本已保存: {os.path.basename(md_path)}")

    elif api_result["tool_called"]:
        # 工具调用成功，已有 5_agent_report_input.json
        if output_mode == "report":
            # 调用 generate_report 生成 HTML+PDF
            print("\n  📄 生成报告文件（HTML+PDF）...")
            try:
                from scripts.task_runner import TaskRunner
                runner = TaskRunner(task_dir, meta, project_root)
                agent_input_path = os.path.join(task_dir, "5_agent_report_input.json")
                gen_ok, gen_result = runner.generate_report(agent_input_path)
                if gen_ok:
                    result["html_path"] = gen_result.get("html_path", "")
                    result["pdf_path"] = gen_result.get("pdf_path", "")
                    print(f"  ✅ HTML: {os.path.basename(gen_result.get('html_path', ''))}")
                    print(f"  ✅ PDF:  {os.path.basename(gen_result.get('pdf_path', ''))}")
                else:
                    print(f"  ⚠️ 报告生成失败: {gen_result.get('error', '')}")
            except Exception as e:
                print(f"  ⚠️ 报告生成异常: {e}")
        else:
            # cli 模式
            print(f"\n  📋 5_agent_report_input.json 已就绪，可运行以下命令生成报告文件：")
            print(f"     python main.py generate --task-id {meta['task_id']}")

    return result
