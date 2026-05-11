# Phase 2 详细指南

> 如何读取数据文件并填写 5_agent_report_input.json

---

## ⚠️ 第零步：读取用户画像（必须最先做）

**5_agent_briefing.md 中有「用户画像」章节**，字段映射自 `config/config.json`：

| 字段 | 枚举值 | 影响 |
|:---|:---|:---|
| `investment_style` 投资风格 | `value` 价值 / `growth` 成长 / `band` 波段 / `trend` 趋势 | 决定选股方向 |
| `risk_level` 风险承受度 | `conservative` 保守(±5%) / `steady` 稳健(±10%) / `aggressive` 积极(±18%) / `bold` 进取(±25%) | 决定止损幅度和仓位集中度 |
| `operation_freq` 操作频率 | `ultra_short` 超短线(1~5天) / `short` 短期(6~15天) / `medium` 中期(16~30天) / `long` 长期(30天以上) | 决定持股周期和介入策略 |
| `experience_level` 经验等级 | `beginner` 小白 / `entry` 入门 / `intermediate` 进阶 / `professional` 专业 | 决定报告复杂度 |
| `total_assets_range` 资产规模 | `below_10w` / `10w_to_50w` / `50w_to_100w` / `above_100w` | 决定仓位配比和分散程度 |

**调整规则：**

| 用户类型 | 选股风格 | 仓位策略 | 止损设置 | 持股周期 |
|:---|:---|:---|:---|:---|
| 保守(risk=conservative) | 低估值、高股息、防御性 | 单票≤15%，总仓位≤60% | 破3日线减仓 | 与操作周期对齐 |
| 稳健(risk=steady) | 价值为主，适度参与成长 | 单票≤20%，总仓位≤70% | 破5日线减仓 | 与操作周期对齐 |
| 积极(risk=aggressive) | 龙头+中军为主 | 单票≤25%，总仓位≤75% | 破5日线减仓 | 与操作周期对齐 |
| 进取(risk=bold) | 追涨打板、连板接力 | 单票≤30%，总仓位≤80% | 破5日线减仓 | 与操作周期对齐 |

❌ 禁止忽略用户画像写万能模板
❌ 禁止给保守/稳健用户推荐打板追涨策略
❌ 禁止资产规模10万以下建议单票≥30%仓位

❌ 禁止忽略用户画像写万能模板
❌ 禁止给低风险用户推荐打板策略

---

## 读取数据（文件名因任务类型而异，请以实际文件为准）

| 文件模式 | 关键字段 | 用途 |
|:---|:---|:---|
| `2_stock_quote_realtime.json` | quote.price / quote.change_pct / quote.volume | 实时行情 |
| `2_stock_kline_indicator.json` | technical.tech_score / technical.ma5 / technical.support_1 | 技术指标 |
| `2_stock_info_detail.json` | raw_text | 个股详细资料（证券之星），需自行提取 |
| `1_market_*.json`  | 大盘指数/板块涨跌数据 | 市场情绪 |
| `4_search_*.json` | 联网搜索 results / snippet | 搜索结果，需提炼 |
| `0_portfolio_fresh.json` | 持仓快照（持仓诊断专用，含实时价格） | 持仓分析 |
| `5_agent_briefing.md` | 任务说明 + user_prefs | 了解 Phase 1 产出 + 用户画像 |

**每个 JSON 文件都有 `agent_note` 字段，说明需要从中提取什么。**

---

## 填写 sections

```json
{
  "sections": [
    {
      "title": "一、公司概况",
      "subsections": [
        {
          "title": "基本信息",
          "content": "中兴通讯（000063）成立于1985年...[基于2_stock_info_detail.json和搜索结果填写]",
          "table": {
            "headers": ["指标", "数值"],
            "rows": [["总市值", "XXX亿元"], ["PE", "XX倍"]]
          }
        }
      ]
    }
  ]
}
```

---

## 专家模式字数要求

| 章节 | 最少字数 |
|:---|:---|
| 🦞 导航（机构评级+建议） | 400字 |
| 公司概况 | 400字 |
| 财务分析 | 500字+表格 |
| 行业竞争 | 400字 |
| 投资亮点+风险 | 500字+表格 |
| 估值建议 | 400字 |
| **合计** | **4000-7000字** |

---

## 内容质量标准

- ✅ 必须基于实际读取的 JSON 数据
- ✅ 来源于搜索结果的内容必须标注"据[来源]"
- ✅ 普通模式：每章 200-400 字
- ✅ 专家模式：每章 400-800 字，全文 4000-7000 字
- ❌ 禁止保留 "_" 开头的占位符文本
- ❌ 禁止填写"待分析"、"暂无数据"等空洞内容
- ❌ 禁止数据与 JSON 文件不一致
