# 踩坑经验

> 由 AI 在实际调用中自动积累。遇到新问题后追加到此文件。

---

## 已知问题

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
