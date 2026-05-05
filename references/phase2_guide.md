# Phase 2 详细指南

> 如何读取数据文件并填写 07_agent_input.json

---

## 读取数据

| 文件 | 关键字段 | 用途 |
|:---|:---|:---|
| 01_quote.json | quote.price / quote.change_pct / quote.volume | 实时行情 |
| 02_kline.json | technical.tech_score / technical.ma5 / technical.support_1 | 技术指标 |
| 03_master.json | raw_text | 个股详细资料（证券之星），需自行提取 |
| 04_market.json | 大盘指数数据 | 市场情绪 |
| 05_search_*.json | raw_output | 联网搜索结果，需提炼 |
| 06_portfolio.json | 持仓快照（持仓诊断专用，含实时价格） | 持仓分析 |
| 06_akshare.json | 资金流/融资融券/龙虎榜 | 补充数据 |
| AGENT_BRIEFING.md | 任务说明 + hint | 了解 Phase 1 产出 |

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
          "content": "中兴通讯（000063）成立于1985年...[基于03_master.json和搜索结果填写]",
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
