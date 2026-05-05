# 🌍 Localization Guide / 本地化改造指南

> Adapt Lobster Research to your local market.
> 将龙虾调研适配到您所在的本地市场。

---

## Table of Contents / 目录

- [Overview / 概述](#overview--概述)
- [Step 0: Know Your Local Data Sources / 了解本地数据源](#step-0-know-your-local-data-sources--了解本地数据源)
- [Step 1: Adapt Data Scripts / 改造数据脚本](#step-1-adapt-data-scripts--改造数据脚本)
- [Step 2: Translate Prompt Templates / 翻译提示词模板](#step-2-translate-prompt-templates--翻译提示词模板)
- [Step 3: Translate Code & Docs / 翻译代码与文档](#step-3-translate-code--docs--翻译代码与文档)
- [Step 4: Adapt Configurations / 适配配置](#step-4-adapt-configurations--适配配置)
- [Step 5: Test & Iterate / 测试与迭代](#step-5-test--iterate--测试与迭代)
- [Appendix: File Mapping / 附录：文件映射表](#appendix-file-mapping--附录文件映射表)

---

<a id="overview--概述"></a>
## Overview / 概述

This guide walks you through adapting Lobster Research to any financial market (US, EU, Japan, India, etc.) or language environment.

本指南帮助您将龙虾调研适配到任意金融市场（美股、欧洲、日本、印度等）或语言环境。

**The core principle / 核心原则**: The project separates **data collection** (Phase 1, Python scripts) from **content synthesis** (Phase 2, AI + prompt templates). To localize, you primarily need to:

1. **Replace data sources** — Swap Chinese market APIs for your local ones
2. **Translate prompts** — Convert report templates to your language
3. **Update config** — Adjust market codes, currency, labels

**核心原则**：项目将**数据采集**（Phase 1，Python 脚本）与**内容整合**（Phase 2，AI + 提示词模板）分离。本地化时，您主要需要：

1. **替换数据源** — 将中国市场的 API 换为您本地的
2. **翻译提示词** — 将报告模板转换为您的语言
3. **更新配置** — 调整市场代码、货币、标签

---

<a id="step-0-know-your-local-data-sources--了解本地数据源"></a>
## Step 0: Know Your Local Data Sources / 了解本地数据源

Before modifying code, research what data sources are available in your target market.

在修改代码之前，先调研目标市场有哪些可用数据源。

### Data You Need / 需要的数据

| Data Type | Chinese Source | Your Local Alternative |
|:---|:---|:---|
| Real-time quotes | Sina Finance, Tencent Finance | Yahoo Finance, Alpha Vantage, IEX Cloud, Investing.com |
| K-line / Technicals | Sina Finance, AKShare | Yahoo Finance API, Polygon.io, Quandl |
| Stock profiles | Securities Star (证券之星) | Yahoo Finance, Bloomberg API, your local exchange |
| Market indices | Sina Finance | Yahoo Finance, your central bank / stock exchange |
| Fund flows / Margin | AKShare | Your local exchange API, SEC/FINRA (US) |
| News search | Baidu, 360, Bing, Tavily | Google Search API, Bing Search, your local news aggregators |
| News headlines | Baidu Daily News | RSS feeds, NewsAPI, your local financial news sites |

### Search Engine Priority / 搜索引擎优先级

Current priority in `scripts/websearch_pro.py`:
1. Tavily API (general)
2. ProSearch (local auth gateway)
3. Baidu Search (Chinese)
4. Bing Search
5. 360 Search (Chinese)
6. Direct URL fallback

**For your market**, consider:
- **US/Global**: Tavily → Bing → Google Custom Search → Yahoo
- **EU**: Tavily → Bing → Euronews / local financial portals
- **Japan**: Tavily → Yahoo Japan → Nikkei API
- **India**: Tavily → Google → Moneycontrol / Economic Times

---

<a id="step-1-adapt-data-scripts--改造数据脚本"></a>
## Step 1: Adapt Data Scripts / 改造数据脚本

### 1.1 Real-Time Quotes / 实时行情 — `scripts/ticktime.py`

**Current**: Uses Sina Finance (`https://hq.sinajs.cn`) and Tencent Finance as fallback.

**To adapt**:
```python
# Replace Sina URLs with your local API
# Example: Yahoo Finance for US stocks
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Update stock code format logic
# Current: sz000001 (Shenzhen), sh600000 (Shanghai)
# US: AAPL, TSLA (no exchange prefix needed)
# Japan: 7203.T (Toyota on TSE)
# India: RELIANCE.NS (NSE), RELIANCE.BO (BSE)
```

**Key changes**:
- `StockDataAPI._format_code()` — Remove/add exchange prefix logic
- `StockDataAPI._sina_request()` / `_tencent_request()` — Replace with your API client
- Add error handling for different market trading hours

### 1.2 K-Line & Technicals / K线与技术指标 — `scripts/stock_data_collector.py`

**Current**: Uses Sina Finance K-line API.

**To adapt**:
```python
# Replace Sina K-line with Yahoo Finance or local API
# Example: Yahoo Finance historical data
import yfinance as yf
ticker = yf.Ticker("AAPL")
hist = ticker.history(period="6mo")
```

**Key changes**:
- Historical data source URL
- Trading calendar (remove Chinese holidays, add local ones)
- Technical indicator calculations should remain universal (MA, RSI, MACD)

### 1.3 Stock Profiles / 个股详细资料 — `scripts/stock_master.py`

**Current**: Scrapes Securities Star (证券之星).

**To adapt**:
```python
# Replace with Yahoo Finance profile or local data provider
# Example: Yahoo Finance company info
profile_url = f"https://finance.yahoo.com/quote/{symbol}/profile"
# Or use a paid API like Bloomberg, Refinitiv, or your local exchange
```

### 1.4 Market Indices / 大盘指数 — `scripts/ticktime.py` (market methods)

**Current**: Tracks 上证指数, 深证成指, 创业板指, 科创50.

**To adapt**:
```python
# Update index codes in config/config.json
"index_codes": {
    "^GSPC": "S&P 500",      # US
    "^DJI": "Dow Jones",      # US
    "^IXIC": "NASDAQ",        # US
    "^N225": "Nikkei 225"     # Japan
}
```

### 1.5 Web Search / 联网搜索 — `scripts/websearch_pro.py`

**Current**: Tavily → Baidu → Bing → 360.

**To adapt**:

Edit the engine priority and add/remove engines:

```python
# In scripts/websearch_pro.py, line ~76
PRIMARY_ENGINE = "tavily"       # Keep or change
SECONDARY_ENGINE = "bing"       # Replace baidu with bing/google
# Remove: baidu, 360 if not relevant
# Add: google_custom_search, your_local_search_api
```

Also update `config/settings.json`:
```json
{
  "websearch_pro": {
    "engines": {
      "primary": "tavily",
      "secondary": "bing",
      "enable_all": false
    },
    "apis": {
      "tavily_api_key": "your-key",
      "bing_api_key": "your-key"
    }
  }
}
```

### 1.6 Structured Data / 结构化数据 — `scripts/akshare_api_kit.py`

**Current**: Uses AKShare (Chinese financial data library).

**To adapt**:
```python
# For US market, replace with yfinance or pandas-datareader
# For other markets, find equivalent libraries:
#   - US: yfinance, pandas-datareader, alpaca-trade-api
#   - Japan: jquants-api-client
#   - India: nsepy, yfinance
#   - EU: yfinance, euronext data
```

### 1.7 News Headlines / 新闻快讯 — `scripts/baidu_dailynews.py`

**Current**: Scrapes Baidu News.

**To adapt**:
```python
# Replace with local news source
# Example: Google News RSS, NewsAPI, or your local financial news site
NEWS_URL = "https://news.google.com/rss/search?q=finance"
# Or use a news API like NewsAPI.org
```

### 1.8 Market Sentiment / 市场情绪 — `scripts/market_state.py`

**Current**: Uses Playwright to scrape Sina Finance market page.

**To adapt**:
```python
# Replace target URL with your local market overview page
# Example: Yahoo Finance market overview
MARKET_URL = "https://finance.yahoo.com/markets/"
# Or your local exchange's market data page
```

### 1.9 Summary: Script Changes / 脚本改造总结

| Script | Change Effort | What to Change |
|:---|:---|:---|
| `ticktime.py` | Medium | API URLs, stock code format, index codes |
| `stock_data_collector.py` | Medium | K-line data source, trading calendar |
| `stock_master.py` | Medium | Stock profile scraping target |
| `websearch_pro.py` | Low | Engine priority, remove/add search engines |
| `akshare_api_kit.py` | High | Replace entire AKShare dependency |
| `baidu_dailynews.py` | Low | News source URL/API |
| `market_state.py` | Low | Target scraping URL |
| `parse_image.py` | None | OCR is language-agnostic |
| `generate_report.py` | Low | Currency symbol (¥ → $/€/¥/₹) |
| `task_runner.py` | None | Orchestrator, no market-specific code |

---

<a id="step-2-translate-prompt-templates--翻译提示词模板"></a>
## Step 2: Translate Prompt Templates / 翻译提示词模板

All 28 templates live in `prompts/json/`. Each is a JSON file with translatable fields.

28 套模板全部位于 `prompts/json/`。每个都是 JSON 文件，包含以下可翻译字段。

### Template Structure / 模板结构

```json
{
  "name": "研报-企业发展",
  "type": "专家研报",
  "style": "blue",
  "parameters": {
    "stockAndMarket": "个股，企业，上市公司",
    "observationCycle": "季度",
    "observationMode": "单企业深度研究"
  },
  "recommendedKeywords": ["企业发展", "企业估值", "财务分析"],
  "recommendedDataSources": ["公司年报/季报", "交易所公告", "Wind"],
  "dataRequirements": "企业财务报表、融资历史...",
  "coreIdea": "通过对单一企业进行全面深度研究...",
  "promptBody": "企业深度研报（5000字）\n\n前置导读模块..."
}
```

### Fields to Translate / 需要翻译的字段

| Field | Description | Example (EN) |
|:---|:---|:---|
| `name` | Template name | "Research - Company Development" |
| `type` | Report type | "Expert Research" |
| `parameters.stockAndMarket` | Applicable scope | "Individual stocks, companies, listed companies" |
| `parameters.observationCycle` | Time horizon | "Quarterly" |
| `parameters.observationMode` | Analysis mode | "Single-company deep research" |
| `recommendedKeywords` | Search keywords | ["company growth", "valuation", "financial analysis"] |
| `recommendedDataSources` | Data sources | ["Annual/Quarterly Reports", "SEC Filings", "Bloomberg"] |
| `dataRequirements` | Required data | "Financial statements, funding history..." |
| `coreIdea` | Core thesis | "Conduct comprehensive deep research on a single company..." |
| `promptBody` | The full prompt | The entire report outline and chapter instructions |

### Translation Tips / 翻译建议

1. **Keep the structure**: Chapter titles, section headings, and formatting markers (```, ---, tables) should remain
2. **Adapt examples**: If the prompt mentions "沪深300", change to "S&P 500" or your local index
3. **Adjust data source references**: "Wind" → "Bloomberg", "东方财富" → "Yahoo Finance"
4. **Preserve formatting instructions**: "段落① 150字，高亮 50字" controls output structure — keep the format but translate the labels
5. **Keep output length instructions**: "5000字" → "5000 words" or keep as character count if your language uses characters

### Batch Translation Workflow / 批量翻译工作流

```bash
# 1. Create a translation script
python scripts/translate_templates.py --source-lang zh --target-lang en --input prompts/json/ --output prompts/json_en/

# 2. Review and refine manually (AI translation needs human review for financial terms)

# 3. Replace or symlink
mv prompts/json prompts/json_zh
mv prompts/json_en prompts/json
```

---

<a id="step-3-translate-code--docs--翻译代码与文档"></a>
## Step 3: Translate Code & Docs / 翻译代码与文档

### 3.1 Code Comments & Strings / 代码注释与字符串

Files with Chinese text to translate:

| File | What to Translate |
|:---|:---|
| `main.py` | CLI help text, banner messages, step labels |
| `scripts/*.py` | Docstrings, print messages, error messages |
| `config/config.py` | User-facing messages |
| `modules/*.py` | Docstrings |

**Example**:
```python
# Before
print("  ✅ 实时行情获取成功")
# After
print("  ✅ Real-time quote fetched successfully")
```

### 3.2 SKILL.md / 技能文档

This is the most important document for AI agents. Translate:
- All constraint descriptions (铁律)
- Workflow instructions
- Command reference table
- File structure descriptions

Keep the technical terms (JSON filenames, field names) unchanged.

### 3.3 References / 参考文档

| File | Priority |
|:---|:---|
| `references/phase2_guide.md` | High — guides AI content filling |
| `references/project_structure.md` | Medium — project overview |
| `references/ps_cheatsheet.md` | Low — PowerShell specific |
| `references/pitfalls.md` | Low — accumulated notes |

### 3.4 Config Labels / 配置标签

Translate labels in `config/config.json`:
```json
"labels": {
  "investment_style": {
    "conservative": "Conservative",
    "balanced": "Balanced",
    "aggressive": "Aggressive"
  }
}
```

---

<a id="step-4-adapt-configurations--适配配置"></a>
## Step 4: Adapt Configurations / 适配配置

### 4.1 Market Config / 市场配置 — `config/config.json`

```json
{
  "user": {
    "country": "US",           // Change from "CN"
    "language": "en-US"        // Change from "zh-CN"
  },
  "market": {
    "index_codes": {
      "^GSPC": "S&P 500",      // US example
      "^DJI": "Dow Jones",
      "^IXIC": "NASDAQ"
    },
    "focus_stocks": ["AAPL", "MSFT", "GOOGL"]
  },
  "cross_assets": {
    "symbols": [
      {"code": "GC=F", "name": "Gold"},
      {"code": "BTC-USD", "name": "Bitcoin"}
    ],
    "fx": [
      {"code": "EUR=X", "name": "EUR/USD"}
    ]
  }
}
```

### 4.2 Routing Config / 路由配置 — `main.json`

Update `keywords` in each domain to match your language:

```json
{
  "domains": [
    {
      "id": "market",
      "label": "Market Overview",
      "keywords": ["market", "index", "S&P", "Dow", "NASDAQ", "rally", "sell-off"]
    },
    {
      "id": "stock",
      "label": "Individual Stock",
      "keywords": ["stock", "share", "ticker", "price", "earnings"]
    }
  ],
  "news_defaults": {
    "keywords": ["news", "headlines", "updates", "breaking"]
  }
}
```

### 4.3 Search Engine Config / 搜索引擎配置 — `config/settings.json`

```json
{
  "websearch_pro": {
    "engines": {
      "primary": "tavily",
      "secondary": "bing",
      "enable_all": false
    },
    "apis": {
      "tavily_api_key": "tvly-...",
      "tavily_api_base": "https://api.tavily.com/search",
      "bing_api_key": "..."
    }
  }
}
```

### 4.4 Currency & Colors / 货币与颜色

Update currency symbols in report templates and styles:
- `styles/*.py`: Search for `¥` and replace with `$`, `€`, `£`, `₹`, etc.
- Stock price display: Red = up, Green = down (Chinese convention) → adjust for your market

---

<a id="step-5-test--iterate--测试与迭代"></a>
## Step 5: Test & Iterate / 测试与迭代

### 5.1 Unit Tests / 单元测试

Test each data script independently:

```bash
# Test real-time quotes
python scripts/ticktime.py --code AAPL 2>&1

# Test search
python scripts/websearch_pro.py "Apple stock news" 2>&1

# Test market indices
python scripts/ticktime.py --market 2>&1
```

### 5.2 Integration Tests / 集成测试

Test the full pipeline:

```bash
# Test news mode
python main.py smart --input "latest market news" 2>&1

# Test quick report mode
python main.py smart --input "Apple daily report" 2>&1

# Test deep research mode
python main.py smart --input "Tesla in-depth research" 2>&1
```

### 5.3 Validation Checklist / 验证清单

| Check | Command | Expected Result |
|:---|:---|:---|
| ✅ Quotes work | `python main.py smart --input "AAPL stock"` | 01_quote.json created with data |
| ✅ Search works | Check 05_search_*.json | Results in your language/market |
| ✅ Report generates | `python main.py generate --task-id ...` | PDF created successfully |
| ✅ Text is translated | Open PDF | All content in target language |
| ✅ Currency correct | Check PDF tables | Correct currency symbol |
| ✅ Colors correct | Check PDF | Red=up / Green=down (or your convention) |

---

<a id="appendix-file-mapping--附录文件映射表"></a>
## Appendix: File Mapping / 附录：文件映射表

### Data Scripts → Data Type / 数据脚本 → 数据类型

| Script | Data Type | Localize? | Effort |
|:---|:---|:---|:---|
| `ticktime.py` | Real-time quotes, market indices | Yes | Medium |
| `stock_data_collector.py` | K-line, technical indicators | Yes | Medium |
| `stock_master.py` | Stock profiles | Yes | Medium |
| `websearch_pro.py` | Web search | Yes | Low |
| `akshare_api_kit.py` | Structured financial data | Yes | High |
| `baidu_dailynews.py` | News headlines | Yes | Low |
| `market_state.py` | Market sentiment scraping | Yes | Low |
| `parse_image.py` | Portfolio OCR | No | None |
| `generate_report.py` | HTML/PDF rendering | Partial | Low |
| `task_runner.py` | Orchestration | No | None |

### Prompt Templates / 提示词模板

| File | Type | Words |
|:---|:---|:---|
| `快报-今日行情.json` | Quick — Market | ~500 |
| `快报-个股分析.json` | Quick — Stock | ~500 |
| `快报-ETF选择.json` | Quick — ETF | ~400 |
| `快报-持仓分析.json` | Quick — Portfolio | ~400 |
| `快报-短线机会.json` | Quick — Short-term | ~400 |
| `快报-科技风向.json` | Quick — Tech | ~400 |
| `快报-技术发展.json` | Quick — Frontier Tech | ~400 |
| `研报-企业发展.json` | Deep — Company | ~5000 |
| `研报-大盘行情.json` | Deep — Market | ~4000 |
| `研报-行业发展.json` | Deep — Industry | ~4000 |
| `研报-持仓诊断.json` | Deep — Portfolio | ~3000 |
| `研报-选股研究.json` | Deep — Stock Picking | ~3000 |
| `研报-科技风向.json` | Deep — Tech | ~4000 |
| `研报-技术发展.json` | Deep — Frontier Tech | ~4000 |
| `研报-跨资产研究.json` | Deep — Cross-Asset | ~4000 |
| `研报-期货方向.json` | Deep — Futures | ~3000 |
| `研报-农业与食品.json` | Deep — Agriculture | ~3000 |
| `研报-资源与工业.json` | Deep — Resources | ~3000 |
| `研报-通讯与物流航运.json` | Deep — Telecom | ~3000 |
| `研报-消费与潮流.json` | Deep — Consumer | ~3000 |
| `研报-游戏与娱乐.json` | Deep — Gaming | ~3000 |
| `研报-生物与医疗.json` | Deep — Biotech | ~3000 |
| `研报-文化与艺术.json` | Deep — Culture | ~3000 |
| `研报-政治与影响力.json` | Deep — Politics | ~3000 |
| `研报-战争与军事.json` | Deep — Military | ~3000 |
| `研报-宇宙与地理前沿研究.json` | Deep — Space | ~3000 |
| `研报-社会发展.json` | Deep — Society | ~3000 |
| `研报-社会金融.json` | Deep — Finance | ~3000 |

**Total prompt text to translate: ~75,000 Chinese characters / ~50,000 English words**

---

<div align="center">

_Questions? Open an issue or discussion on GitHub._<br>
_有问题？请在 GitHub 上提交 Issue 或开启 Discussion。_

</div>
