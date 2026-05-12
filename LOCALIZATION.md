# Localization Guide

> Adapt Lobster Research to your local market.

## Overview

This guide walks you through adapting Lobster Research to any financial market (US, EU, Japan, India, etc.) or language environment.

**Core principle**: The project separates **data collection** (Phase 1, Python scripts) from **content synthesis** (Phase 2, AI + prompt templates). To localize, you primarily need to:

1. **Replace data sources** — Swap Chinese market APIs for your local ones
2. **Translate prompts** — Convert report templates to your language
3. **Update config** — Adjust market codes, currency, labels

---

## Project Structure (for reference)

```
lobster-research/
├── main.py              # Entry point + Smart NLP router
├── main.json            # Routing config (domains + output types)
├── SKILL.md             # Agent skill instructions
├── modules/             # Core algorithms & tools
│   ├── core.py          # Signal system, trend judgment, scoring models
│   ├── extend.py        # Report template library + REPORT_TYPES
│   ├── expert_*.py      # Expert mode workflows
│   └── logger.py        # Logging system
├── scripts/             # Data collection & report generation
│   ├── task_runner.py   # Phase 1/3 execution engine
│   ├── ticktime.py      # Real-time quotes (Sina/Tencent)
│   ├── stock_data_collector.py  # K-line + technical indicators
│   ├── stock_master.py  # Stock profiles
│   ├── websearch_pro.py # Multi-engine search
│   ├── akshare_api_kit.py       # AKShare structured data
│   ├── baidu_dailynews.py       # News headlines
│   ├── market_state.py  # Market sentiment (Playwright)
│   ├── parse_image.py   # Portfolio screenshot OCR
│   ├── generate_report.py       # HTML/PDF renderer
│   ├── generate_alonemode.py    # Alone mode: auto LLM API
│   └── emu_manager.py           # Simulated portfolio (Phase 4)
├── config/              # Configuration
│   ├── config.py        # Settings manager + CLI
│   ├── config.json      # User preferences + market config
│   ├── portfolio.json   # Real portfolio holdings
│   ├── emu_portfolio.json       # Simulated portfolio holdings
│   ├── emu_operations.json      # Simulated trade log
│   ├── emu_reflections.json     # Simulated reflection log
│   └── settings.json    # API keys
├── keywords/            # 24 domain search templates
├── prompts/json/        # 29 report prompt templates (7 quick + 22 deep)
├── styles/              # Pure CSS style system
│   ├── palettes.css     # 10 color palettes as CSS custom properties
│   ├── base.css         # Report CSS template (var() + data-* driven)
│   └── style_manager.py # Loader (reads CSS files, generates HTML attrs)
├── references/          # Documentation
├── test/                # Test suite
│   └── runner.py        # Full test runner: python -m test.runner
└── output/tasks/        # Task output folders
```

---

## Step 1: Adapt Data Scripts

### 1.1 Real-Time Quotes — `scripts/ticktime.py`

**Current**: Uses Sina Finance (`https://hq.sinajs.cn`) and Tencent Finance.

**To adapt**: Replace the API URLs and stock code format logic.

```python
# Replace Sina URLs with your local API
# Example: Yahoo Finance for US stocks
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# Update stock code format logic
# Current: sz000001 (Shenzhen), sh600000 (Shanghai)
# US: AAPL, TSLA
# Japan: 7203.T
# India: RELIANCE.NS
```

### 1.2 K-Line & Technicals — `scripts/stock_data_collector.py`

**Current**: Uses Sina Finance K-line API.

```python
# Replace with yfinance or your local API
import yfinance as yf
ticker = yf.Ticker("AAPL")
hist = ticker.history(period="6mo")
```

### 1.3 Stock Profiles — `scripts/stock_master.py`

**Current**: Scrapes Securities Star (证券之星).

```python
# Replace with Yahoo Finance profile or your data provider
profile_url = f"https://finance.yahoo.com/quote/{symbol}/profile"
```

### 1.4 Market Indices — `scripts/ticktime.py`

**Current**: Tracks Chinese indices (上证指数, 深证成指, etc.).

**To adapt**: Update index codes in `config/config.json`:

```json
"index_codes": {
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones",
    "^IXIC": "NASDAQ",
    "^N225": "Nikkei 225"
}
```

### 1.5 Web Search — `scripts/websearch_pro.py`

**Current**: Tavily → Baidu → Bing → 360.

**To adapt**: Edit engine priority and API keys in `config/settings.json`:

```json
{
  "websearch_pro": {
    "engines": {
      "primary": "tavily",
      "secondary": "bing"
    },
    "apis": {
      "tavily_api_key": "tvly-...",
      "bing_api_key": "..."
    }
  }
}
```

### 1.6 Structured Data — `scripts/akshare_api_kit.py`

**Current**: Uses AKShare (exclusively Chinese markets). Requires full replacement.

```python
# US: yfinance, pandas-datareader, alpaca-trade-api
# Japan: jquants-api-client
# India: nsepy, yfinance
# EU: yfinance, euronext data
```

### 1.7 News Headlines — `scripts/baidu_dailynews.py`

**Current**: Scrapes Baidu News RSS.

```python
# Replace with NewsAPI or your local financial news site
NEWS_URL = "https://newsapi.org/v2/everything?q=finance"
```

### 1.8 Market Sentiment — `scripts/market_state.py`

**Current**: Uses Playwright to scrape Sina Finance market page.

```python
# Replace with your local market overview page
MARKET_URL = "https://finance.yahoo.com/markets/"
```

### 1.9 Simulated Portfolio (Phase 4) — `scripts/emu_manager.py`

No market-specific logic. Just configure in `config/config.py`:
- `emu.enabled`: enable/disable
- `emu.follow_user_prefs`: use user's portfolio settings
- `emu.independent_capital`: set independent capital if not following user prefs

### 1.10 Summary

| Script | Effort | What to Change |
|--------|--------|----------------|
| `ticktime.py` | Medium | API URLs, stock code format, index codes |
| `stock_data_collector.py` | Medium | K-line data source, trading calendar |
| `stock_master.py` | Medium | Stock profile scraping target |
| `websearch_pro.py` | Low | Engine priority, API keys |
| `akshare_api_kit.py` | High | Replace entire dependency |
| `baidu_dailynews.py` | Low | News source URL |
| `market_state.py` | Low | Target scraping URL |
| `parse_image.py` | None | OCR is language-agnostic |
| `generate_report.py` | Low | Currency symbol, date format |
| `task_runner.py` | None | No market-specific code |
| `emu_manager.py` | None | No market-specific code |

---

## Step 2: Translate Prompt Templates

All 29 templates live in `prompts/json/`. Each is a JSON file with these translatable fields:

```json
{
  "name": "快报-个股分析",
  "type": "专家快报",
  "style": "purple",
  "parameters": {
    "stockAndMarket": "个股，股票，上市公司",
    "observationCycle": "分钟级",
    "observationMode": "单只股票分析"
  },
  "recommendedKeywords": ["个股行情", "技术分析", "资金流向"],
  "recommendedDataSources": ["交易所行情", "财经新闻", "公司公告"],
  "dataRequirements": "实时行情数据、K线数据、成交数据...",
  "coreIdea": "单只股票的分钟级快报..."
}
```

### Fields to Translate

| Field | Description | Example (EN) |
|-------|-------------|---------------|
| `name` | Template name | "Quick - Stock Analysis" |
| `type` | Report type | "Expert Quick Report" |
| `style` | Color palette | Keep as-is (CSS handles it) |
| `parameters.stockAndMarket` | Applicable scope | "Stocks, listed companies" |
| `parameters.observationCycle` | Time horizon | "Minute-level" |
| `parameters.observationMode` | Analysis mode | "Single stock analysis" |
| `recommendedKeywords` | Search keywords | ["stock quote", "technical analysis", "fund flow"] |
| `recommendedDataSources` | Data sources | ["Exchange data", "Financial news", "Company filings"] |
| `dataRequirements` | Required data | "Real-time quotes, K-line data..." |
| `coreIdea` | Core thesis | Short description of the report's purpose |

### Style Parameter

The `style` field in templates maps to one of 10 color palettes:
- `blue`, `purple`, `green`, `indigo`, `orange`, `pink`, `red`, `yellow`, `cyan`, `brown`

This is passed to the 3D style system as `--style`. The render type (`--color-type`) and layout (`--layout`) can be overridden via CLI flags. You don't need to change these.

---

## Step 3: Translate Code & Docs

### 3.1 SKILL.md

This is the most important document for AI agents. Translate:
- All constraint rules (铁律)
- Workflow instructions
- Command reference table
- File structure descriptions

Keep technical terms (JSON filenames, command names, field names) unchanged.

### 3.2 references/

| File | Priority | Purpose |
|------|----------|---------|
| `phase2_guide.md` | High | AI content filling guide |
| `project_structure.md` | Medium | Project overview |
| `ps_cheatsheet.md` | Low | PowerShell-specific |
| `pitfalls.md` | Low | Accumulated notes |

### 3.3 Code strings

Files with user-facing Chinese text:

| File | What to Translate |
|------|-------------------|
| `main.py` | CLI help text, banner messages, step labels |
| `scripts/*.py` | Docstrings, print/output messages |
| `config/config.py` | Config descriptions, CLI help |
| `modules/*.py` | Docstrings |

### 3.4 Test Help Text

Translate test descriptions in `test/runner.py` if needed. The test framework uses `log.section()`, `log.ok()`, `log.fail()` etc.

---

## Step 4: Adapt Configurations

### 4.1 Market Config — `config/config.json`

```json
{
  "user": {
    "country": "US",
    "language": "en-US"
  },
  "market": {
    "index_codes": {
      "^GSPC": "S&P 500",
      "^DJI": "Dow Jones",
      "^IXIC": "NASDAQ"
    },
    "focus_stocks": ["AAPL", "MSFT", "GOOGL"]
  }
}
```

### 4.2 Output Style Config

```json
"output": {
    "mode": "expert",
    "format": "markdown",
    "report_style": "blue",
    "color_type": "liquid",
    "layout": "rounded"
}
```

Three independent dimensions:
- `report_style`: 10 color palettes (blue/purple/green/indigo/orange/pink/red/yellow/cyan/brown)
- `color_type`: solid (flat colors) | gradient | liquid (glow + frosted glass)
- `layout`: rounded | square | minimal

Edit color values directly in `styles/palettes.css` (CSS custom properties).

### 4.3 Routing Config — `main.json`

Update keywords in each domain to match your language:

```json
{
  "domains": [
    {
      "id": "market",
      "label": "Market Overview",
      "keywords": ["market", "index", "S&P", "Dow", "NASDAQ"]
    },
    {
      "id": "stock",
      "label": "Individual Stock",
      "keywords": ["stock", "share", "ticker", "price", "earnings"]
    }
  ]
}
```

### 4.4 Search Keywords — `keywords/`

The 24 domain search templates in `keywords/` contain Chinese search queries. Translate each domain's search groups, keeping the `sites` field if using Chinese data sources (replace if switching to local sources).

### 4.5 Currency & Colors

- **Currency symbol**: Edit in the data sources and any hardcoded references. The CSS files (`styles/base.css`, `styles/palettes.css`) contain color values only, not currency symbols.
- **Red/Green convention**: Chinese market uses Red = up, Green = down. Adjust `stock_data_collector.py` and reporting scripts if your market uses the opposite convention.

### 4.6 User Preferences — `config/config.py`

Translate the config schema labels if your CLI users need them. Key defaults:

```python
"user": {
    "investment_style": "value",    # value | growth | balanced
    "operation_freq": "short",      # short | medium | long
    "experience_level": "entry",    # entry | intermediate | advanced
    "risk_level": "steady",         # steady | balanced | aggressive
}
```

---

## Step 5: Test & Iterate

### 5.1 Test data scripts independently

```bash
# Test real-time quotes
python scripts/ticktime.py --code AAPL

# Test search
python scripts/websearch_pro.py "Apple stock news"

# Test market indices
python scripts/ticktime.py --market
```

### 5.2 Test the full pipeline

```bash
# Quick report
python main.py smart --input "AAPL daily report"

# Deep research
python main.py smart --input "Tesla in-depth research"

# Generate report
python main.py generate --task-id <task_id>
```

### 5.3 Run the test suite

```bash
python -m test.runner --dry-run       # Dry run all categories
python -m test.runner --category style # Test style system
python -m test.runner --execute       # Execute all tests
```

### 5.4 Validation Checklist

| Check | How |
|-------|-----|
| ✅ Quotes work | Check `2_stock_quote_realtime.json` has data |
| ✅ Search works | Check `4_search_batch_summary.json` has results |
| ✅ Report generates | `python main.py generate --task-id ...` creates PDF |
| ✅ Text is translated | Open PDF — all content in target language |
| ✅ Currency correct | Check PDF tables for correct currency symbol |
| ✅ Colors correct | Check PDF for Red=up / Green=down convention |
| ✅ CSS renders correctly | Check HTML preview for proper glass/gradient effects |

---

## Appendix: File Mapping

### Scripts → Data Type

| Script | Data Type | Localize? | Effort |
|--------|-----------|-----------|--------|
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
| `emu_manager.py` | Simulated portfolio | No | None |

### Prompt Templates (29 total — 7 quick + 22 deep)

| File | Type | Est. Words |
|------|------|------------|
| `快报-今日行情.json` | Quick — Market | ~500 |
| `快报-个股分析.json` | Quick — Stock | ~500 |
| `快报-ETF选择.json` | Quick — ETF | ~400 |
| `快报-持仓分析.json` | Quick — Portfolio | ~400 |
| `快报-短线机会.json` | Quick — Short-term | ~400 |
| `快报-科技风向.json` | Quick — Tech | ~400 |
| `快报-技术发展.json` | Quick — Frontier Tech | ~400 |
| `研报-个股分析.json` | Deep — Stock | ~5000 |
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

---

### Style System (no localization needed)

The CSS files in `styles/` are localization-neutral:
- `palettes.css` — Only color hex values, no text
- `base.css` — Only CSS property values, no text
- `style_manager.py` — No user-facing text

To change colors, edit `palettes.css` directly:

```css
[data-palette="blue"] {
  --primary: #007AFF;
  --primary-bg: #E8F1FF;
  /* ... */
}
```

---

_Questions? Open an issue or discussion on GitHub._
