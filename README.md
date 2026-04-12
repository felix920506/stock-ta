# stock-ta

Standalone CLI for technical analysis of any yfinance-supported ticker,
with optional AI-driven company research and Discord webhook output.

Originally a Claude Code / Openclaw skill; extracted so it can run on its
own. The deterministic TA scoring is always shown — the AI layer is
additive, not a replacement.

## Install

**As a CLI / standalone:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and fill in keys you want to use
```

**As a library, from Git** (for consuming projects):

```bash
pip install git+https://github.com/felix920506/stock-ta.git
# pin to a tag:
pip install git+https://github.com/felix920506/stock-ta.git@v0.1.0
```

Then:

```python
import ta_core
result = ta_core.analyze("AAPL", period="6mo", interval="1d")
print(result["score"], result["label"])

import ai_research  # requires OPENAI_API_KEY in env
result["ai_research"] = ai_research.research(result)
```

The installed package also exposes a `stock-ta` console command equivalent to `python analyze.py`.

## Usage

```bash
# Plain TA report
python analyze.py AAPL

# Different window
python analyze.py 2330.TW --period 1y --interval 1d

# Structured JSON (for piping)
python analyze.py NVDA --format json

# Add AI research on recent company developments
python analyze.py TSLA --ai

# Post the report to Discord
python analyze.py TSLA --ai --discord

# Re-render a previously saved JSON result (skips the data fetch)
python analyze.py --from-json result.json
cat result.json | python analyze.py --from-json -
```

### Flags

| Flag | Default | Notes |
|---|---|---|
| `ticker` | required | `AAPL`, `2330.TW`, `BTC-USD`, `^GSPC`, … |
| `--period` | `6mo` | `1mo` `3mo` `6mo` `1y` `2y` |
| `--interval` | `1d` | `1d` `1wk` `1mo` |
| `--format` | `text` | `text` or `json` |
| `--ai` | off | Append AI research section |
| `--discord` | off | Post output to `DISCORD_WEBHOOK_URL` |
| `--discord-url` | — | Override the env webhook |
| `--from-json SRC` | — | Render from existing JSON result — file path, `-` for stdin, or raw JSON string |

### `.env`

```
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
DISCORD_WEBHOOK_URL=
```

`OPENAI_BASE_URL` accepts any OpenAI-compatible endpoint — OpenAI,
OpenRouter, Perplexity, Groq, LM Studio, Ollama, etc.

### Caching

Uses [`yfinance-cache`](https://pypi.org/project/yfinance-cache/) by
default — a smarter drop-in for `yfinance` that understands market hours
and refetches only when new bars are expected, greatly reducing
rate-limit risk on repeated runs.

| Env | Default | |
|---|---|---|
| `STOCK_TA_CACHE_DIR` | `./.cache/yfinance-cache` (relative to cwd) | Cache location |
| `STOCK_TA_CACHE_DISABLE` | unset | `1` to bypass and use plain `yfinance` |

At `INFO` log level you'll see a line like
`ta_core: yfinance_cache enabled at /path/to/project/.cache/yfinance-cache`
on the first analysis of each run, confirming the cache is active.

### Logging

All modules log to stderr via stdlib `logging`. Level is controlled by
`STOCK_TA_LOG_LEVEL` in `.env` (default `INFO`; also accepts `DEBUG`,
`WARNING`, `ERROR`). The log format is fixed.

**Note on recency:** plain chat completions are limited to the model's
training cutoff. For genuinely recent news, point `OPENAI_BASE_URL` at a
provider/model with web browsing (e.g. Perplexity's `sonar` models, or
an OpenRouter model with `:online`).

## What it computes

- **Trend:** EMA20/50/200, SMA50, MACD (line/signal/histogram), golden/death cross
- **Momentum:** RSI(14), Stochastic %K/%D
- **Volatility:** Bollinger Bands, ATR(14)
- **Volume:** 20-day volume ratio, OBV trend
- **Levels:** Pivot, R1, S1 over a 20-bar window

### Scoring

Eight signals score ±1, plus up to +2 bonus:

| Signal | +1 | –1 |
|---|---|---|
| Price vs EMA200 | above | below |
| Golden cross | EMA50 > EMA200 | EMA50 < EMA200 |
| MACD vs signal | above | below |
| MACD histogram | positive | negative |
| RSI(14) | 40–70 | >70 or <40 |
| Stochastic | K > D | K < D |
| BB% | 0.2–0.8 | >0.8 or <0.2 |
| OBV trend | rising | falling |

Bonus: +1 oversold bounce (RSI<35 and price>EMA50); +1 volume surge
(>1.5× avg and MACD histogram positive).

Labels: `STRONG BUY` ≥5 · `BUY` 2–4 · `HOLD` –1 to 1 · `SELL` –4 to –2 · `STRONG SELL` ≤–5.

See `references/indicators.md` for the interpretation guide.

## HTTP API

A minimal Bottle server exposes the same capability over HTTP for
cross-language consumers:

```bash
python server.py --host 127.0.0.1 --port 8000
# or, after pip install:
stock-ta-server --port 8000
```

### `GET|POST /analyze`

Runs TA. Parameters come from a JSON body or URL query string (body wins
if both are present).

| Param | Required | Notes |
|---|---|---|
| `ticker` | yes | e.g. `AAPL` |
| `period` | no | default `6mo` |
| `interval` | no | default `1d` |
| `format` | no | `true` → `text/plain` report; default `false` → JSON |

```bash
curl 'http://localhost:8000/analyze?ticker=AAPL'
curl 'http://localhost:8000/analyze?ticker=AAPL&format=true'
curl -X POST http://localhost:8000/analyze \
     -H 'Content-Type: application/json' \
     -d '{"ticker":"AAPL","period":"1y"}'
```

Responses: `200` on success · `400` missing/invalid input · `404` unknown ticker.

### `POST /format`

Renders a previously-captured `/analyze` JSON result as a text report.
Accepts a JSON body only; returns `text/plain`.

```bash
curl -X POST http://localhost:8000/format \
     -H 'Content-Type: application/json' \
     --data-binary @result.json
```

Responses: `200` text report · `415` body not JSON · `422` JSON shape invalid.

### `GET /health`

Returns `{"status":"ok"}`.

## Files

- `analyze.py` — CLI entry point
- `server.py` — Bottle HTTP API
- `ta_core.py` — indicator computation and scoring
- `report.py` — text report renderer
- `ai_research.py` — OpenAI-compatible client for company research
- `discord_post.py` — webhook sender (handles the 2000-char limit)

## Disclaimer

TA is probabilistic, not predictive. AI output may be incomplete or out
of date. None of this is financial advice.
