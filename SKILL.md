---
name: stock-ta
description: Perform technical analysis on a given stock ticker and produce a recommendation (Strong Buy / Buy / Hold / Sell / Strong Sell) with explanation. Use when the user asks to analyze a stock, assess whether to buy/sell/hold, check technical indicators (RSI, MACD, EMA, Bollinger Bands, etc.), or get a TA-based trading signal for any equity or index (e.g. "analyze TSLA", "should I buy AAPL?", "TA on 2330.TW", "what do the technicals say about NVDA?").
---

# Stock Technical Analysis

Self-contained tool — the script handles all data fetching, indicator computation, scoring, and report formatting. No LLM interpretation needed for standard runs.

## Quick Start

```bash
# Formatted text report (ready to send as-is)
python3 skills/stock-ta/scripts/analyze_stock.py 2330.TW --format text

# Structured JSON (for programmatic use or piping into other tools)
python3 skills/stock-ta/scripts/analyze_stock.py 2330.TW --format json
```

## Arguments

| Argument | Default | Description |
|---|---|---|
| `ticker` | *(required)* | Any yfinance symbol: `AAPL`, `2330.TW`, `BTC-USD`, `^GSPC` |
| `--period` | `6mo` | Data period: `1mo` `3mo` `6mo` `1y` `2y` |
| `--interval` | `1d` | Bar interval: `1d` `1wk` `1mo` |
| `--format` | `json` | Output: `json` (structured) or `text` (formatted report) |

## What It Computes

- **Trend:** EMA20/50/200, SMA50, MACD (line/signal/histogram), golden/death cross
- **Momentum:** RSI(14), Stochastic %K/%D
- **Volatility:** Bollinger Bands (upper/mid/lower/pct), ATR(14)
- **Volume:** Volume ratio vs 20d average, OBV trend
- **Levels:** Pivot, R1, S1 from 20-bar window

## Scoring (built into the script)

8 signals scored +1 (bullish) or -1 (bearish), plus up to +2 bonus:

| Signal | +1 (Bullish) | -1 (Bearish) |
|--------|-------------|-------------|
| price vs EMA200 | above | below |
| golden_cross | EMA50 > EMA200 | EMA50 < EMA200 |
| MACD vs signal | above | below |
| MACD histogram | positive | negative |
| RSI(14) | 40–70 | >70 or <40 |
| Stochastic K vs D | K > D | K < D |
| BB% band | 0.2–0.8 | >0.8 or <0.2 |
| OBV trend | rising | falling |

**Bonus:** +1 for oversold bounce (RSI < 35 + price > EMA50), +1 for volume surge (>1.5× avg + positive MACD hist)

**Labels:** `STRONG BUY` (≥5) · `BUY` (2–4) · `HOLD` (–1 to 1) · `SELL` (–4 to –2) · `STRONG SELL` (≤–5)

## Text Output Format

The `--format text` flag produces a complete report with:
- Header: company name, ticker, date, price, recommendation with score
- Sections: Trend, Momentum, Volatility, Volume, Key Levels, Signals Summary
- Currency auto-detected: NT$ for `.TW`/`.TWO` tickers, $ for everything else
- Disclaimer included

This output can be sent directly to Discord/Telegram/etc. without further processing.

## Workflow

For a standard TA request:
1. Identify the ticker (e.g. user says "Realtek" → `2379.TW`)
2. Run: `python3 skills/stock-ta/scripts/analyze_stock.py 2379.TW --period 1y --format text`
3. Send the output to the user

For programmatic use (e.g. from market-scanner):
1. Run with `--format json` (default)
2. Parse the JSON for `score`, `label`, `signals`, etc.

## Dependencies

```bash
pip install yfinance pandas ta
```

## Notes

- If < 200 bars, EMA200 and golden cross will show as "insufficient data" — increase `--period`
- Taiwan stocks: `.TW` suffix. Crypto: `-USD`. Indices: `^` prefix.
- Company name is resolved from yfinance `shortName`/`longName`
- For weekly/monthly intervals, use `--period 2y` to get enough bars
- See `references/indicators.md` for detailed indicator interpretation guide
