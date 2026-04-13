"""
Stock Technical Analysis — core library.

Pure TA logic: fetches OHLCV via yfinance, computes indicators, and
scores signals. Report rendering lives in report.py.
"""

import json
import logging
import sys
from datetime import datetime

log = logging.getLogger(__name__)

try:
    import yfinance as yf
    import pandas as pd
    from ta.trend import MACD, EMAIndicator, SMAIndicator
    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.volatility import BollingerBands, AverageTrueRange
    from ta.volume import OnBalanceVolumeIndicator
except ImportError as e:
    print(json.dumps({"error": f"Missing dependency: {e}. Run: pip install -r requirements.txt"}))
    sys.exit(1)



def last(series, n=1):
    """Get last N non-null values from a Series."""
    vals = series.dropna()
    if len(vals) == 0:
        return None
    return round(float(vals.iloc[-n]), 4) if n == 1 else [round(float(v), 4) for v in vals.iloc[-n:]]


def analyze(ticker: str, period: str = "6mo", interval: str = "1d") -> dict:
    """Fetch data, compute indicators, score, and return a complete result dict."""
    log.info("analyze ticker=%s period=%s interval=%s", ticker, period, interval)
    tk = yf.Ticker(ticker)
    df = tk.history(period=period, interval=interval)
    log.debug("fetched %d bars for %s", len(df), ticker)

    if df.empty:
        log.warning("no data for ticker=%s", ticker)
        return {"error": f"No data returned for ticker '{ticker}'. Check if the symbol is valid."}

    company_name = None
    try:
        info = tk.info
        company_name = info.get("shortName") or info.get("longName")
    except Exception as e:
        log.debug("info lookup failed for %s: %s", ticker, e)

    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    volume = df["Volume"]

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

    if rsi_v and rsi_v < 35 and e50 and price_now > e50:
        score += 1
        signals_bull.append(f"Oversold bounce setup: RSI {rsi_v:.1f} with price above EMA50")

    if vol_ratio and vol_ratio > 1.5 and macd_h and macd_h > 0:
        score += 1
        signals_bull.append(f"Volume surge {vol_ratio}× avg with positive MACD — conviction move")

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

    recent = df.tail(20)
    pivot  = round((recent["High"].max() + recent["Low"].min() + float(close.iloc[-1])) / 3, 4)
    r1     = round(2 * pivot - recent["Low"].min(), 4)
    s1     = round(2 * pivot - recent["High"].max(), 4)

    log.info("result ticker=%s score=%+d label=%s", ticker.upper(), score, label)

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
