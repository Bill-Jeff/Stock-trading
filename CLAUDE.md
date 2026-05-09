# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

红杉选股 (Sequoia Stock Screener) — a Chinese A-share stock screening system. Fetches real-time quotes from EastMoney via AKShare, applies hard filters (price change, volume, market cap, turnover) and moving-average bullish alignment checks, then pushes a markdown report to a DingTalk bot.

## Commands

```bash
# Run screening (single pass)
python main.py

# Run in daemon mode (schedules daily at config schedule.time)
python main.py --daemon
```

No test suite exists. Dependencies: `akshare`, `pandas`, `requests`, `pyyaml`.

## Architecture

4 modules, linear pipeline:

1. **`main.py`** — Entry point. Loads `config.yaml`, checks weekday trading day, orchestrates the pipeline: fetch → filter → report → push. Supports `--daemon` mode for daily scheduled runs.

2. **`fetcher.py`** — Data acquisition via `akshare`:
   - `fetch_realtime_quotes()` — full A-share spot data from `ak.stock_zh_a_spot_em()`
   - `fetch_history(code, days)` — daily K-line history from `ak.stock_zh_a_hist()`
   - `fetch_list_date(code)` — IPO date from `ak.stock_individual_info_em()`

3. **`filter.py`** — Screening logic:
   - `apply_hard_filters()` — filters by change %, turnover, market cap, excludes ST/科创板/北交所
   - `check_ma_bullish()` — verifies MA5 > MA10 > MA20 > MA60 alignment
   - `screen_stocks()` — full pipeline: hard filters → new-stock exclusion (sampled) → MA check per stock

4. **`push.py`** — DingTalk webhook push with optional HMAC signing. `build_report()` formats results as a markdown table.

## Config

`config.yaml` controls DingTalk webhook URL/secret, screening thresholds (change %, amount, turnover, market cap range, MA periods, min listing days), and daemon schedule time.

## Key Dependencies

- `akshare` — stock data from EastMoney (API changes frequently, may need `pip install akshare --upgrade`)
- `requests` — DingTalk webhook push
- `pandas` — data manipulation
- `pyyaml` — config loading
