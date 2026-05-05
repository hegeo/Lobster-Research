# 项目结构与文件说明

---

## 项目文件树

```
lobster-research/
├── main.py                ←  入口（主要运行这个）
├── main.json              ←  Smart 路由配置（领域关键词 + 输出类型）
├── SKILL.md               ←  技能文档（约束 + 流程）
├── scripts/
│   ├── task_runner.py     ← Phase 1/3 执行引擎
│   ├── ticktime.py        ← 实时行情
│   ├── stock_data_collector.py ← K线+技术指标
│   ├── stock_master.py    ← 个股详细资料
│   ├── websearch_pro.py   ← 联网搜索
│   ├── generate_report.py ← 报告渲染
│   ├── akshare_api_kit.py ← AKShare 资金流/龙虎榜
│   ├── baidu_dailynews.py ← 百度新闻快讯
│   ├── market_state.py    ← 大盘整体状况
│   └── parse_image.py     ← 持仓截图 OCR
├── config/
│   ├── config.py          ← 配置+持仓管理
│   ├── config.json        ← 用户配置
│   ├── portfolio.json     ← 持仓数据
│   └── settings.json      ← API Keys
├── modules/
│   ├── extend.py          ← 研报类型注册表+模板常量
│   ├── core.py            ← 量化算法库
│   ├── expert_datamodel.py ← 专家模式数据模型
│   └── expert_workflow.py  ← 专家模式工作流（遗留）
├── prompts/json/           ← 28 个提示词模板（7 快报 + 21 研报）
├── styles/                 ← 报告 CSS 样式（blue/orange/ios_liquid）
├── references/             ← 参考文档
└── output/tasks/           ← 任务文件夹
```

---

## 任务文件夹结构

```
output/tasks/<task_id>/
├── meta.json              任务元信息 + 状态机
├── AGENT_BRIEFING.md      给你的工作说明（Phase 1 自动生成）
├── 01_quote.json          实时行情数据
├── 02_kline.json          K线 + 技术指标
├── 03_master.json         个股详细资料
├── 04_market.json         大盘指数
├── 04_market_state.json   大盘整体状况
├── 04_news_batch.json     百度新闻快讯
├── 05_search_0.json       搜索结果
├── 06_akshare.json        AKShare 结构化数据
├── 06_portfolio.json      持仓快照（持仓诊断专用）
├── 07_agent_input.json    ← 你填写的最终报告数据
├── report_<task_id>.html  最终报告 HTML
└── report_<task_id>.pdf   最终报告 PDF
```

---

## 模板覆盖

### CLI 子命令直接挂载（6 个命令）

| 命令 | 脚本步骤 | 关联模板 |
|:---|:---|:---|
| stock | quote → kline → master → search | 研报-企业发展.json |
| company | quote → kline → master → search | 研报-企业发展.json |
| market | market_index → search | 快报-今日行情.json |
| industry | search | 研报-行业发展.json |
| portfolio | portfolio → market_index → search | 研报-持仓诊断.json |
| screener | market_index → search | 研报-选股研究.json |

### Smart 路由覆盖全部 28 个模板

`main.py smart` 通过 `main.json` 的 `quick_template` / `deep_template` 动态引用全部模板，无孤立文件。

**7 个快报模板：** 大盘行情、个股分析、ETF选择、持仓分析、短线机会、科技风向、技术发展

**21 个研报模板：** 企业发展、大盘行情、行业发展、持仓诊断、选股研究、科技风向、技术发展、跨资产研究、期货方向、农业与食品、资源与工业、通讯与物流航运、消费与潮流、游戏与娱乐、生物与医疗、文化艺术、政治与影响力、战争与军事、宇宙与地理前沿研究、社会发展、社会金融

---

## 版本变更记录

| 维度 | v1.x | v2.0 |
|:---|:---|:---|
| 路由方式 | Agent 手动判断 SKILL.md 关键词表 | `main.py smart` 双层关键词自动匹配 |
| 关键词配置 | 内嵌在 SKILL.md（约 70 行表格） | 外置到 `main.json`（可热更新） |
| 匹配精度 | 单层匹配，"猪肉"直接进研报 | 双层匹配：领域+类型 |
| 快讯模式 | Agent 在 SKILL.md 里读规则自行判断 | main.py 输出 tier=news + agent_hint |
| 覆盖领域 | 28 种（硬编码） | 23 个领域 × 3 种输出 |
| 持仓数据 | `portfolio --file <json>` 手动传 | `config/portfolio.json` 统一存储，smart 自动读 |
| 持仓诊断 | 仅 search，无实时价格 | `run_portfolio()` 刷新价格后写入 06_portfolio.json |
