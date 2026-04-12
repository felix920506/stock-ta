#!/usr/bin/env python3
"""
Stock Technical Analysis — Standalone Tool
Fetches OHLCV data, computes TA indicators, scores them, and outputs
either structured JSON or a ready-to-send formatted text report.

Usage:
    python3 analyze_stock.py <TICKER> [--period 6mo] [--interval 1d] [--format json|text]

Dependencies: yfinance, pandas, ta
Install:      pip install yfinance pandas ta
"""

import argparse
import json
import sys
from datetime import datetime

try:
    import yfinance as yf
    import pandas as pd
    from ta.trend import MACD, EMAIndicator, SMAIndicator
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.volatility import BollingerBands, AverageTrueRange
    from ta.volume import OnBalanceVolumeIndicator
except ImportError as e:
    print(json.dumps({"error": f"Missing dependency: {e}. Run: pip install yfinance pandas ta"}))
    sys.exit(1)


def last(series, n=1):
    """Get last N non-null values from a Series."""
    vals = series.dropna()
    if len(vals) == 0:
        return None
    return round(float(vals.iloc[-n]), 4) if n == 1 else [round(float(v), 4) for v in vals.iloc[-n:]]


def analyze(ticker: str, period: str = "6mo", interval: str = "1d") -> dict:
    """Fetch data, compute indicators, score, and return a complete result dict."""
    tk = yf.Ticker(ticker)
    df = tk.history(period=period, interval=interval)

    if df.empty:
        return {"error": f"No data returned for ticker '{ticker}'. Check if the symbol is valid."}

    # Resolve company name
    company_name = None
    try:
        info = tk.info
        company_name = info.get("shortName") or info.get("longName")
    except Exception:
        pass

    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    volume = df["Volume"]

    # ── Indicators ─────────────────────────────────────────────────────
    ema20  = EMAIndicator(close=close, window=20).ema_indicator()
    ema50  = EMAIndicator(close=close, window=50).ema_indicator()
    ema200 = EMAIndicator(close=close, window=200).ema_indicator()
    sma50  = SMAIndicator(close=close, window=50).sma_indicator()

    macd_obj  = MACD(close=close)
    macd_line = macd_obj.macd()
    macd_sig  = macd_obj.macd_signal()
    macd_hist = macd_obj.macd_diff()

    rsi    = RSIIndicator(close=close, window=14).rsi()
    stoch  = StochasticOscillator(high=high, low=low, close=close)
    stoch_k = stoch.stoch()
    stoch_d = stoch.stoch_signal()

    bb     = BollingerBands(close=close, window=20, window_dev=2)
    bb_upper = bb.bollinger_hband()
    bb_lower = bb.bollinger_lband()
    bb_mid   = bb.bollinger_mavg()
    bb_pct   = bb.bollinger_pband()
    atr    = AverageTrueRange(high=high, low=low, close=close).average_true_range()

    obv    = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    # ── Extract values ─────────────────────────────────────────────────
    price_now   = last(close)
    price_prev  = last(close, 2)[0] if len(close) >= 2 else price_now
    pct_change  = round((price_now - price_prev) / price_prev * 100, 2) if price_prev else None

    high_period = round(float(high.max()), 4)
    low_period  = round(float(low.min()), 4)

    avg_vol_20 = round(float(volume.rolling(20).mean().iloc[-1]), 0)
    vol_ratio  = round(float(volume.iloc[-1]) / avg_vol_20, 2) if avg_vol_20 else None

    e20  = last(ema20)
    e50  = last(ema50)
    e200 = last(ema200)
    macd_l = last(macd_line)
    macd_s = last(macd_sig)
    macd_h = last(macd_hist)
    rsi_v  = last(rsi)
    sk     = last(stoch_k)
    sd     = last(stoch_d)
    bb_pct_v = last(bb_pct)
    atr_v  = last(atr)
    obv_rising = obv.iloc[-1] > obv.iloc[-5] if len(obv) >= 5 else None
    obv_trend  = "rising" if obv_rising else ("falling" if obv_rising is not None else "unknown")
    golden_cross = e50 is not None and e200 is not None and e50 > e200

    # ── Composite Scoring ──────────────────────────────────────────────
    score = 0
    signals_bull = []
    signals_bear = []
    signals_neutral = []

    def check(cond, bull_msg, bear_msg):
        nonlocal score
        if cond is None:
            signals_neutral.append(bull_msg + " (insufficient data)")
            return
        if cond:
            score += 1
            signals_bull.append(bull_msg)
        else:
            score -= 1
            signals_bear.append(bear_msg)

    check(
        price_now > e200 if e200 else None,
        "Price above EMA200 (long-term uptrend)",
        "Price below EMA200 (long-term downtrend)")
    check(
        golden_cross if e50 is not None and e200 is not None else None,
        "Golden cross: EMA50 > EMA200",
        "Death cross: EMA50 < EMA200")
    check(
        macd_l > macd_s if macd_l is not None and macd_s is not None else None,
        "MACD above signal line",
        "MACD below signal line")
    check(
        macd_h > 0 if macd_h is not None else None,
        "MACD histogram positive (momentum building)",
        "MACD histogram negative (momentum fading)")
    check(
        40 <= rsi_v <= 70 if rsi_v is not None else None,
        f"RSI {rsi_v:.1f} — healthy range (40–70)" if rsi_v else "RSI healthy",
        f"RSI {rsi_v:.1f} — {'overbought (>70)' if rsi_v and rsi_v > 70 else 'oversold (<40)'}" if rsi_v else "RSI extreme")
    check(
        sk > sd if sk is not None and sd is not None else None,
        f"Stochastic K({sk:.0f}) > D({sd:.0f}) — bullish crossover" if sk and sd else "Stoch bullish",
        f"Stochastic K({sk:.0f}) < D({sd:.0f}) — bearish crossover" if sk and sd else "Stoch bearish")
    check(
        0.2 <= bb_pct_v <= 0.8 if bb_pct_v is not None else None,
        f"BB% {bb_pct_v:.2f} — healthy band position" if bb_pct_v is not None else "BB healthy",
        f"BB% {bb_pct_v:.2f} — {'above upper band' if bb_pct_v is not None and bb_pct_v > 0.8 else 'below lower band'}" if bb_pct_v is not None else "BB extreme")
    check(
        obv_rising,
        "OBV rising (volume confirming price)",
        "OBV falling (volume diverging from price)")

    # Bonus signals
    if rsi_v and rsi_v < 35 and e50 and price_now > e50:
        score += 1
        signals_bull.append(f"Oversold bounce setup: RSI {rsi_v:.1f} with price above EMA50")

    if vol_ratio and vol_ratio > 1.5 and macd_h and macd_h > 0:
        score += 1
        signals_bull.append(f"Volume surge {vol_ratio}× avg with positive MACD — conviction move")

    # Label
    if score >= 5:
        label = "STRONG BUY"
    elif score >= 2:
        label = "BUY"
    elif score >= -1:
        label = "HOLD"
    elif score >= -4:
        label = "SELL"
    else:
        label = "STRONG SELL"

    # Support / Resistance
    recent = df.tail(20)
    pivot  = round((recent["High"].max() + recent["Low"].min() + float(close.iloc[-1])) / 3, 4)
    r1     = round(2 * pivot - recent["Low"].min(), 4)
    s1     = round(2 * pivot - recent["High"].max(), 4)

    return {
        "ticker": ticker.upper(),
        "name": company_name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "period": period,
        "interval": interval,
        "bars": len(df),
        "score": score,
        "max_score": 8,
        "label": label,
        "price": {
            "current": price_now,
            "change_1d_pct": pct_change,
            "high_period": high_period,
            "low_period": low_period,
        },
        "trend": {
            "ema20": e20, "ema50": e50, "ema200": e200, "sma50": last(sma50),
            "price_vs_ema20":  "above" if price_now and e20 and price_now > e20 else "below",
            "price_vs_ema50":  "above" if price_now and e50 and price_now > e50 else "below",
            "price_vs_ema200": "above" if price_now and e200 and price_now > e200 else "below",
            "ema20_vs_ema50":  "above" if e20 and e50 and e20 > e50 else "below",
            "golden_cross": golden_cross,
            "macd": macd_l, "macd_signal": macd_s, "macd_hist": macd_h,
            "macd_bullish": macd_l > macd_s if macd_l is not None and macd_s is not None else None,
        },
        "momentum": {
            "rsi14": rsi_v, "stoch_k": sk, "stoch_d": sd,
        },
        "volatility": {
            "bb_upper": last(bb_upper), "bb_mid": last(bb_mid), "bb_lower": last(bb_lower),
            "bb_pct_band": bb_pct_v,
            "atr14": atr_v,
            "atr_pct": round(atr_v / price_now * 100, 2) if atr_v and price_now else None,
        },
        "volume": {
            "last": int(volume.iloc[-1]),
            "avg_20d": int(avg_vol_20),
            "ratio": vol_ratio,
            "obv": last(obv),
            "obv_trend": obv_trend,
        },
        "levels": {"pivot": pivot, "R1": r1, "S1": s1},
        "signals": {
            "bullish": signals_bull,
            "bearish": signals_bear,
            "neutral": signals_neutral,
        },
    }


def format_report(r: dict) -> str:
    """Format the analysis result dict into a human-readable text report."""
    if "error" in r:
        return f"❌ Error: {r['error']}"

    ticker = r["ticker"]
    name   = r.get("name") or ticker
    date   = r["date"]
    p      = r["price"]
    t      = r["trend"]
    m      = r["momentum"]
    v      = r["volatility"]
    vol    = r["volume"]
    lv     = r["levels"]
    sig    = r["signals"]
    score  = r["score"]
    mx     = r["max_score"]
    label  = r["label"]

    # Price formatting — detect currency by ticker suffix
    is_tw = ticker.endswith(".TW") or ticker.endswith(".TWO")
    curr  = "NT$" if is_tw else "$"
    price_str = f"{curr}{p['current']:,.2f}"
    change_str = f"{p['change_1d_pct']:+.2f}%" if p['change_1d_pct'] is not None else "N/A"

    # Label emoji
    label_emoji = {"STRONG BUY": "🟢🟢", "BUY": "🟢", "HOLD": "🟡", "SELL": "🔴", "STRONG SELL": "🔴🔴"}.get(label, "⚪")

    lines = []
    lines.append(f"📊 {name} ({ticker}) — Technical Analysis")
    lines.append(f"Date: {date} · Period: {r['period']} · Interval: {r['interval']} · Bars: {r['bars']}")
    lines.append("")
    lines.append(f"Price: {price_str}  ({change_str})")
    lines.append(f"Recommendation: {label_emoji} {label}  (Score: {score:+d}/{mx})")
    lines.append("")

    # ── Trend ──────────────────────────────────────────────────────────
    lines.append("━━ Trend ━━")
    ema_parts = []
    if t["ema20"]:
        ema_parts.append(f"EMA20: {curr}{t['ema20']:,.2f} ({t['price_vs_ema20']})")
    if t["ema50"]:
        ema_parts.append(f"EMA50: {curr}{t['ema50']:,.2f} ({t['price_vs_ema50']})")
    if t["ema200"]:
        ema_parts.append(f"EMA200: {curr}{t['ema200']:,.2f} ({t['price_vs_ema200']})")
    if ema_parts:
        lines.append("  " + " · ".join(ema_parts))
    cross_type = "Golden cross ✅" if t["golden_cross"] else "Death cross ❌"
    if t["ema50"] and t["ema200"]:
        lines.append(f"  {cross_type} (EMA50 vs EMA200)")
    macd_dir = "bullish ▲" if t.get("macd_bullish") else "bearish ▼"
    if t["macd"] is not None:
        lines.append(f"  MACD: {t['macd']:.4f} / Signal: {t['macd_signal']:.4f} / Hist: {t['macd_hist']:.4f} — {macd_dir}")
    lines.append("")

    # ── Momentum ───────────────────────────────────────────────────────
    lines.append("━━ Momentum ━━")
    if m["rsi14"] is not None:
        rsi_v = m["rsi14"]
        if rsi_v > 70:
            rsi_zone = "OVERBOUGHT ⚠️"
        elif rsi_v > 60:
            rsi_zone = "bullish"
        elif rsi_v >= 40:
            rsi_zone = "neutral"
        elif rsi_v >= 30:
            rsi_zone = "bearish"
        else:
            rsi_zone = "OVERSOLD ⚠️"
        lines.append(f"  RSI(14): {rsi_v:.1f} — {rsi_zone}")
    if m["stoch_k"] is not None and m["stoch_d"] is not None:
        stoch_dir = "bullish (K > D)" if m["stoch_k"] > m["stoch_d"] else "bearish (K < D)"
        lines.append(f"  Stochastic: K={m['stoch_k']:.1f} / D={m['stoch_d']:.1f} — {stoch_dir}")
    lines.append("")

    # ── Volatility ─────────────────────────────────────────────────────
    lines.append("━━ Volatility ━━")
    if v["bb_pct_band"] is not None:
        bb = v["bb_pct_band"]
        if bb > 1.0:
            bb_note = "above upper band — overbought/breakout"
        elif bb > 0.8:
            bb_note = "near upper band — watch for reversal"
        elif bb >= 0.2:
            bb_note = "mid-band — consolidation"
        elif bb >= 0:
            bb_note = "near lower band — watch for bounce"
        else:
            bb_note = "below lower band — oversold"
        lines.append(f"  Bollinger: {bb:.2f} ({bb_note})")
        lines.append(f"  Band: {curr}{v['bb_lower']:,.2f} — {curr}{v['bb_mid']:,.2f} — {curr}{v['bb_upper']:,.2f}")
    if v["atr_pct"] is not None:
        vol_level = "high" if v["atr_pct"] > 3 else "moderate" if v["atr_pct"] > 1.5 else "low"
        lines.append(f"  ATR(14): {curr}{v['atr14']:,.2f} ({v['atr_pct']:.2f}% — {vol_level} volatility)")
    lines.append("")

    # ── Volume ─────────────────────────────────────────────────────────
    lines.append("━━ Volume ━━")
    if vol["ratio"] is not None:
        vol_note = "above average ✅" if vol["ratio"] > 1.2 else "below average" if vol["ratio"] < 0.8 else "average"
        lines.append(f"  Volume: {vol['last']:,} ({vol['ratio']:.2f}× 20d avg — {vol_note})")
    lines.append(f"  OBV trend: {vol['obv_trend']}")
    lines.append("")

    # ── Key Levels ─────────────────────────────────────────────────────
    lines.append("━━ Key Levels ━━")
    lines.append(f"  Resistance (R1): {curr}{lv['R1']:,.2f}  ·  Period High: {curr}{p['high_period']:,.2f}")
    lines.append(f"  Pivot: {curr}{lv['pivot']:,.2f}")
    lines.append(f"  Support (S1): {curr}{lv['S1']:,.2f}  ·  Period Low: {curr}{p['low_period']:,.2f}")
    lines.append("")

    # ── Signals Summary ────────────────────────────────────────────────
    lines.append("━━ Signals ━━")
    for s in sig["bullish"]:
        lines.append(f"  ✅ {s}")
    for s in sig["neutral"]:
        lines.append(f"  ⚠️ {s}")
    for s in sig["bearish"]:
        lines.append(f"  ❌ {s}")
    lines.append("")
    lines.append("⚠️ TA is probabilistic, not predictive. This is not financial advice.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Stock Technical Analysis")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. AAPL, TSLA, 2330.TW)")
    parser.add_argument("--period",   default="6mo", help="Data period: 1mo 3mo 6mo 1y 2y (default: 6mo)")
    parser.add_argument("--interval", default="1d",  help="Bar interval: 1d 1wk 1mo (default: 1d)")
    parser.add_argument("--format",   default="json", choices=["json", "text"],
                        help="Output format: json (structured) or text (formatted report)")
    args = parser.parse_args()

    result = analyze(args.ticker, args.period, args.interval)

    if args.format == "text":
        print(format_report(result))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
