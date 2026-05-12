# 项目结构与文件说明

---

## 项目文件树

```
lobster-research-v2.1/
│
├── main.py              ← 入口（主要运行这个）
├── main.json            ← Smart 路由配置（领域关键词 + 报告类型映射）
├── SKILL.md             ← 龙虾技能文档（核心约束 + 流程速查）
├── requirements.txt     ← Python 依赖
├── README.md            ← 项目说明
│
├── config/
│   ├── config.py        ← 配置+持仓管理（支持点号路径读写）
│   ├── config.json      ← 用户画象 + 输出样式（report_style/color_type/layout）
│   ├── portfolio.json   ← 真实持仓数据
│   ├── settings.json    ← API Keys + 搜索引擎配置
│   ├── emu_portfolio.json    ← 模拟盘持仓快照
│   ├── emu_operations.json   ← 模拟盘操作流水
│   └── emu_reflections.json  ← 模拟盘反思进化记录
│
├── scripts/             ← Phase 1/3 数据采集 & 报告生成引擎
│   ├── task_runner.py      ← 任务执行引擎（Phase 1 采集 + Phase 3 生成）
│   ├── ticktime.py         ← 实时行情（新浪接口）
│   ├── stock_data_collector.py ← K线 + 技术指标
│   ├── stock_master.py     ← 个股详细资料（证券之星）
│   ├── websearch_pro.py    ← 联网搜索（API 优先 + 百度/Bing 兜底）
│   ├── generate_report.py  ← 报告渲染（HTML → PDF）
│   ├── generate_alonemode.py ← Alone 模式（自动调用 LLM 生成）
│   ├── validate_quality.py ← 报告质量校验 + table 格式归一化
│   ├── akshare_api_kit.py  ← AKShare 资金流/龙虎榜
│   ├── baidu_dailynews.py  ← 百度新闻快讯
│   ├── market_state.py     ← 大盘整体状况（新浪行情页爬取）
│   ├── parse_image.py      ← 持仓截图 OCR
│   └── emu_manager.py      ← 模拟持仓管理（Phase 4：交易决策→执行→反思进化）
│
├── modules/             ← 核心算法 & 工具模块
│   ├── extend.py           ← 报告类型注册表 + 模板常量
│   ├── core.py             ← 量化算法库（估值/情绪/资金算法）
│   ├── expert_datamodel.py ← 专家模式数据模型
│   ├── expert_workflow.py  ← 专家模式工作流（遗留）
│   └── logger.py           ← 日志系统（每日日志到 logs/）
│
├── prompts/
│   ├── prompt_manager.py        ← 模板加载 + 热重载
│   ├── prompt_manager_useage.txt ← prompt_manager 使用说明
│   └── json/                   ← 29 个提示词模板
│       ├── 快报-ETF选择.json
│       ├── 快报-个股分析.json
│       ├── 快报-今日行情.json
│       ├── 快报-技术发展.json
│       ├── 快报-持仓分析.json
│       ├── 快报-短线机会.json
│       ├── 快报-科技风向.json
│       ├── 研报-个股分析.json    ← v2.1 从企业发展拆分独立
│       ├── 研报-企业发展.json
│       ├── 研报-大盘行情.json
│       ├── 研报-行业发展.json
│       ├── 研报-持仓诊断.json
│       ├── 研报-选股研究.json
│       ├── 研报-科技风向.json
│       ├── 研报-技术发展.json
│       ├── 研报-跨资产研究.json
│       ├── 研报-期货方向.json
│       ├── 研报-农业与食品.json
│       ├── 研报-资源与工业.json
│       ├── 研报-通讯与物流航运.json
│       ├── 研报-消费与潮流.json
│       ├── 研报-游戏与娱乐.json
│       ├── 研报-生物与医疗.json
│       ├── 研报-文化与艺术.json
│       ├── 研报-政治与影响力.json
│       ├── 研报-战争与军事.json
│       ├── 研报-宇宙与地理前沿研究.json
│       ├── 研报-社会发展.json
│       └── 研报-社会金融.json
│
├── keywords/             ← 24 个领域搜索词模板
│   ├── market.json      → 大盘、agri.json → 农业、tech.json → 科技…
│   └── …（完整列表 24 个领域）
│
├── styles/               ← 三维样式系统（v2.1 重构）
│   ├── style_manager.py    ← 统一管理 10 色调色板 + 3 渲染 + 3 布局
│   ├── palettes.css        ← 10 色 CSS 自定义属性（blue/purple/green/indigo/orange/…）
│   ├── base.css            ← 基础报告 CSS 结构
│   └── (无单色 .css 文件 — v2.1 全部合并到 palettes.css)
│
├── references/           ← 参考文档
│   ├── project_structure.md  ← 本文件
│   ├── phase2_guide.md       ← Phase 2 Agent 填写指南
│   ├── ps_cheatsheet.md      ← PowerShell 执行规范
│   └── pitfalls.md           ← 踩坑经验（由 AI 自动积累）
│
├── test/
│   ├── runner.py          ← 完整测试套件
│   ├── test_style.py      ← 样式测试
│   ├── test_data.py       ← 测试数据
│   └── test_output/       ← 测试产出
│
├── logs/                  ← 运行时日志（每日文件）
├── output/tasks/          ← 任务产出文件夹
├── stock_data/            ← 本地缓存行情数据
└── showcase/              ← 报告效果展示
```

---

## 任务文件夹结构

```
output/tasks/<task_id>/
├── 0_meta_task_info.json      ← 任务元信息 + 状态机 + 用户画象 + 样式参数
├── 1_market_index_tick.json   ← 大盘指数实时行情
├── 1_market_status_sina.json  ← 大盘整体状况（涨跌家数/板块/热点）
├── 1_market_akshare_macro.json← AKShare 结构化宏观数据
├── 2_stock_quote_realtime.json← 个股实时行情
├── 2_stock_kline_indicator.json← K线 + 技术指标
├── 2_stock_info_detail.json   ← 个股详细资料（证券之星）
├── 3_news_daily_all.json      ← 当日新闻快讯
├── 3_news_market_flash.json   ← 市场快讯（预留，待实现）
├── 4_search_keyword_*.json    ← 各关键词搜索结果（独立文件）
├── 4_search_batch_summary.json← 批量搜索汇总
├── 4_search_research_report.json ← 专项研究报告搜索（预留）
├── 4_search_stock_batch.json  ← 专项个股搜索（预留）
├── 0_portfolio_img__parse.json← 持仓图片解析结果（持仓诊断专用）
├── 0_portfolio_fresh.json     ← 持仓快照刷新后数据（持仓诊断专用）
├── 5_agent_briefing.md        ← Agent 工作简报（含用户画象 + 数据清单 + 大纲）
├── 5_agent_report_input.json  ← Agent 填写的报告数据（Phase 2 产出）
├── report_<task_id>.html      ← 最终报告 HTML
└── report_<task_id>.pdf       ← 最终报告 PDF
```

---

## 三层架构概览（v2.1）

```
┌─────────────────────────────────────────────────┐
│ Phase 1 — 代码驱动数据采集                       │
│   python main.py <命令> <参数>                    │
│   └─→ 输出 JSON 到 output/tasks/<task_id>/       │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ Phase 2 — Agent 整合（你的任务）                 │
│   读 JSON → 补充搜索 → 写 5_agent_report_input   │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ Phase 3 — 代码驱动报告生成                       │
│   python main.py generate --task-id <id>         │
│   └─→ 输出 HTML + PDF                           │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│ Phase 4 — 模拟持仓交易决策（部分报告类型触发）     │
│   emu_manager.py: 交易决策→执行→记录→反思进化     │
└─────────────────────────────────────────────────┘
```

---

## 命令速查表

| 用户意图 | 命令                              | 数据采集步骤                           | 默认模板               |
|:---- |:------------------------------- |:-------------------------------- |:------------------ |
| 个股分析 | `stock --code XX --name XX`     | quote→kline→master→search        | 研报-个股分析（v2.1 独立）   |
| 企业研报 | `company --code XX --name XX`   | quote→kline→master→search        | 研报-企业发展            |
| 大盘日报 | `market`                        | market_index→market_state→search | 快报-今日行情            |
| 行业/领域研报 | `smart --input "<topic>研报"`（自动匹配领域模板） | main.json 按 domain 动态决定 | main.json 按 domain 动态选择 |
| 持仓诊断 | `smart --input "分析持仓"`          | portfolio→market_index→search    | 研报-持仓诊断            |
| 快速选股 | `screener`（自动从投资风格派生选股方向） | market_index→search              | 研报-选股研究            |
| 快报加速 | 加 `--type quick`                | 跳过 master/search 耗时步骤            | 同上，数据不足 Agent 自行搜索 |
| 智能路由 | `smart --input "原话"`            | main.json 自动匹配合适步骤               | main.json 自动选模板    |

### smart 路由覆盖全部 29 个模板

`main.py smart` 通过 `main.json` 的双层关键词匹配（领域 → quick/deep），动态引用全部模板。

**7 个快报模板：** ETF选择、个股分析、今日行情、技术发展、持仓分析、短线机会、科技风向

**22 个研报模板：** 个股分析（v2.1 新增）、企业发展、大盘行情、行业发展、持仓诊断、选股研究、科技风向、技术发展、跨资产研究、期货方向、农业与食品、资源与工业、通讯与物流航运、消费与潮流、游戏与娱乐、生物与医疗、文化与艺术、政治与影响力、战争与军事、宇宙与地理前沿研究、社会发展、社会金融

---

## 样式系统（三维）

v2.1 从 2D 升级为 3D 样式系统：

| 维度   | 参数             | 可选值                                                        | 说明         |
|:---- |:-------------- |:---------------------------------------------------------- |:---------- |
| 颜色主题 | `--style`      | blue/purple/green/indigo/orange/pink/red/yellow/cyan/brown | 10 色调色板    |
| 渲染类型 | `--color-type` | solid/gradient/liquid                                      | 纯色/渐变/液态光晕 |
| 布局风格 | `--layout`     | rounded/square/minimal                                     | 圆角/方正/极简   |

样式来源优先级：**CLI 参数 > config.json > 模板默认 > 代码默认**

统一由 `styles/style_manager.py` 管理，CSS 集中在 `palettes.css` + `base.css`。

---

## 搜索引擎体系

| 引擎类型          | 引擎                           | 触发条件                |
|:------------- |:---------------------------- |:------------------- |
| 主引擎（API）      | SerpBase / Bing API / Tavily | 配置了 API Key 时优先使用   |
| 备用引擎（HTML 爬取） | 百度搜索 / Bing 国际搜索             | API Key 缺失时自动降级     |
| 数据源限定搜索       | site:数据源.com                 | keywords/ 目录按领域自动构造 |

优先级链：`settings.json` 的 `engines.primary` → `engines.secondary` → 自动循环所有可用引擎。

---

## 配置文件体系

| 文件                          | 内容                     | 是否必需         |
|:--------------------------- |:---------------------- |:------------ |
| `config/config.json`        | 用户画象（投资风格/风险/经验）+ 输出样式 | ✅ 必需         |
| `config/portfolio.json`     | 真实持仓数据                 | ✅ 持仓诊断必需     |
| `config/settings.json`      | API Keys + 搜索引擎配置      | ❌ 可选（可用百度兜底） |
| `config/emu_portfolio.json` | 模拟盘持仓                  | ❌ 可选（自动初始化）  |


