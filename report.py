"""Text report renderer for the dict returned by ta_core.analyze()."""


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

    is_tw = ticker.endswith(".TW") or ticker.endswith(".TWO")
    curr  = "NT$" if is_tw else "$"
    price_str = f"{curr}{p['current']:,.2f}"
    change_str = f"{p['change_1d_pct']:+.2f}%" if p['change_1d_pct'] is not None else "N/A"

    label_emoji = {"STRONG BUY": "🟢🟢", "BUY": "🟢", "HOLD": "🟡", "SELL": "🔴", "STRONG SELL": "🔴🔴"}.get(label, "⚪")

    lines = []
    lines.append(f"📊 {name} ({ticker}) — Technical Analysis")
    lines.append(f"Date: {date} · Period: {r['period']} · Interval: {r['interval']} · Bars: {r['bars']}")
    lines.append("")
    lines.append(f"Price: {price_str}  ({change_str})")
    lines.append(f"Recommendation: {label_emoji} {label}  (Score: {score:+d}/{mx})")
    lines.append("")

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

    lines.append("━━ Volume ━━")
    if vol["ratio"] is not None:
        vol_note = "above average ✅" if vol["ratio"] > 1.2 else "below average" if vol["ratio"] < 0.8 else "average"
        lines.append(f"  Volume: {vol['last']:,} ({vol['ratio']:.2f}× 20d avg — {vol_note})")
    lines.append(f"  OBV trend: {vol['obv_trend']}")
    lines.append("")

    lines.append("━━ Key Levels ━━")
    lines.append(f"  Resistance (R1): {curr}{lv['R1']:,.2f}  ·  Period High: {curr}{p['high_period']:,.2f}")
    lines.append(f"  Pivot: {curr}{lv['pivot']:,.2f}")
    lines.append(f"  Support (S1): {curr}{lv['S1']:,.2f}  ·  Period Low: {curr}{p['low_period']:,.2f}")
    lines.append("")

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
