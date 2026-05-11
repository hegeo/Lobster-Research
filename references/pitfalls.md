# 踩坑经验

> 由 AI 在实际调用中自动积累。遇到新问题后追加到此文件。

---

## 已知问题

### generate 命令静默报错

**现象**：`python main.py generate --task-id XX` 失败时只打印 `❌ 报告生成失败`，不显示具体错误原因。

**根因**：`main.py` 的 `run_generate()` 在失败分支（约行 551-554）只打印了失败提示，丢弃了 `runner.generate_report()` 返回的错误信息（`report_path` 变量在失败时实际存的是错误描述字符串）。

**排查方法**：手动验证 JSON 合法性：`python -c "import json; json.load(open('5_agent_report_input.json', encoding='utf-8'))"`。

**预防**：填写 5_agent_report_input.json 后、运行 generate 前，先用上述命令验证 JSON 格式。

---

### main.py 降级路径

**现象**：输入如"农业日报"（agri 领域无 quick_template），`日报`命中 quick_tag 后 break，继续检查 deep_tag，`研究`命中后生成研报，而非降级为快讯。

**预期**：quick_tag 命中但无模板 → 直接降级为 news

**位置**：`main.py` 行 210-227

---

### 模板引用

**结论**：prompts/json/ 全部 28 个模板均通过 main.json 引用，**无孤立文件**。旧版 SKILL.md 中"23 个孤立模板"的表述是错误的。

---

## 通用提醒

- 运行 main.py 前检查 `$env:PYTHONIOENCODING = "utf-8"`
- 禁止并行执行多个 main.py 命令
- Phase 2 必须先读完所有 JSON 再填写 5_agent_report_input.json
- 报告交付用 `deliver_attachments`，不要用 `open_result_view`

---

### 5_agent_briefing.md 用户画像字段映射硬编码

**现象**：`5_agent_briefing.md` 中的"用户画像"章节部分字段显示不正确。例如 `operation_freq="short"`（应=>"短期(6~15天)"）被显示为"短期(1-3天)"；用户实际配置的 `investment_style="value"` 和 `risk_level="steady"` 因在硬编码映射表中不存在，直接回退显示原始英文值。

**根因**：`scripts/task_runner.py:write_agent_briefing()` 内部使用硬编码的映射字典：
```python
style_map = {"conservative": "保守", "balanced": "平衡", "aggressive": "积极"}
risk_map  = {"low": "低风险", "medium": "中风险", "high": "高风险"}
freq_map  = {"short": "短期(1-3天)", "medium": "中期(3-15天)", "long": "长期(>15天)"}
```
而 `config/config.json` 的 `labels` 对象（经 pipeline 写入 `meta["user_prefs"]["labels"]`）才是唯一正确的映射源。且 `experience_level` 字段完全被遗漏。

**修复（2026-05-11）**：
1. 移除四个硬编码 map 字典
2. 改为从 `user_prefs.get("labels", {})` 动态读取所有字段映射
3. 新增 `experience_level`（经验等级）字段输出

**修改文件**：`scripts/task_runner.py:write_agent_briefing()`（约行 559-596）

---

## JSON 中文引号冲突

**现象**：Agent 填写 `5_agent_report_input.json` 时，在字符串值内使用了 ASCII 双引号（如 `"构建者—协同者—守护者"`），导致 JSON 格式错误，`json.load()` 抛出 `Expecting ',' delimiter`。

**根因**：JSON 字符串值内的 `"` 与 JSON 语法引号冲突，且 `json.dump()` 不会自动转义中文语境下的引号。

**解决**：
1. Agent 填写时应使用中文引号 `"""` 和 `"""`，避免 ASCII `"`
2. 或确保所有 `"` 都经过 `"` → `\"` 转义
3. 若已出错，用脚本批量替换 `"` → `"` / `"`

**预防**：在 `generate_report.py` 的 HTML 构建阶段，对插入内容做 HTML escape（见代码修复）。

---

## Phase 3 交付后回复过长导致截断

**现象**：`generate` 成功后，Agent 写了大段总结文字，总输出过长被系统截断（显示 `...truncated`），用户只看到残缺回复，误以为文件未交付。

**根因**：Agent 在 `preview_url` + `deliver_attachments` 之后又写了大段报告摘要、分析回顾、未来建议等内容，导致总 token 超限被截断。

**正确做法**（铁律）：
1. Phase 3 完成 → 立即调用 `preview_url`（HTML 预览）
2. 立即调用 `deliver_attachments`（PDF + HTML）
3. **只写一句话**，例如："✅ 报告已生成，HTML 已在右侧预览，PDF/HTML 已作为附件发送。"
4. **绝对不要**写报告摘要、章节回顾、数据总结 —— 这些内容都在报告本身里，重复写只会浪费 token 导致截断

**预防**：交付文件本身就是结果，不需要额外总结。少说话，多办事。

---

## smart 命令导致数据采集丢失

**现象**：用户说"个股深度分析，中联重科"，Agent 执行 `python main.py smart --input "个股深度分析，中联重科"`，结果返回的 `code=""`、`name=""`，导致 quote/kline/master 等数据采集全部失败，搜索模板渲染为 `" 最新消息..."`（无股票名）。

**根因**：SKILL.md 旧版路由说明写"一律走 smart"、"你不需要手动判断"，引导 Agent 把所有自然语言请求都交给 smart 命令。但 smart 命令只能通过 regex 提取6位数字代码（用户输入无数字则 code=""），且无法从自然语言中提取股票名称。

**修复（2026-05-11）**：
1. SKILL.md 输入路由改为"由 Agent 自行判断匹配"
2. 铁律1 合并了"Agent 必须自行确定股票代码"要求
3. 标准流程简化去重，速查表底部移除"一律走 smart"

**正确做法**：
- 能明确判断意图（个股/行业/选股等）→ 用精确命令传参
- 只有模糊请求、新闻速览、多领域混合才 fallback 到 smart
- 使用 stock/company 命令时，Agent 需自行搜索确定股票代码

**修改文件**：`SKILL.md` 输入路由（第62-80行）、铁律1（第118-136行）、标准流程（第245-293行）、速查表尾注
