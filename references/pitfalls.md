# 踩坑经验

> 由 AI 在实际调用中自动积累。遇到新问题后追加到此文件。

---

## 已知问题

### generate 命令静默报错

**现象**：`python main.py generate --task-id XX` 失败时只打印 `❌ 报告生成失败`，不显示具体错误原因。

**根因**：`main.py` 的 `run_generate()` 在失败分支（约行 551-554）只打印了失败提示，丢弃了 `runner.generate_report()` 返回的错误信息（`report_path` 变量在失败时实际存的是错误描述字符串）。

**排查方法**：手动验证 JSON 合法性：`python -c "import json; json.load(open('07_agent_input.json', encoding='utf-8'))"`。

**预防**：填写 07_agent_input.json 后、运行 generate 前，先用上述命令验证 JSON 格式。

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
- Phase 2 必须先读完所有 JSON 再填写 07_agent_input.json
- 报告交付用 `deliver_attachments`，不要用 `open_result_view`

---

## JSON 中文引号冲突

**现象**：Agent 填写 `07_agent_input.json` 时，在字符串值内使用了 ASCII 双引号（如 `"构建者—协同者—守护者"`），导致 JSON 格式错误，`json.load()` 抛出 `Expecting ',' delimiter`。

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
