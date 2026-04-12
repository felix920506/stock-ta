# Technical Indicator Reference

Use this when interpreting `analyze_stock.py` JSON output or explaining signals to the user.

## Trend Indicators

| Field | Bullish | Bearish | Notes |
|-------|---------|---------|-------|
| price_vs_ema20/50/200 | above | below | Price above all three = strong uptrend |
| ema20_vs_ema50 | above | below | Short-term momentum direction |
| golden_cross | ema50 > ema200 | ema50 < ema200 | Long-term structural signal |
| macd_bullish | true | false | MACD line > signal line |
| macd_hist | positive & rising | negative & falling | Momentum acceleration |

## Momentum (RSI)

| Range | Interpretation |
|-------|---------------|
| > 70 | Overbought — potential sell/trim |
| 60–70 | Bullish momentum |
| 40–60 | Neutral |
| 30–40 | Bearish momentum |
| < 30 | Oversold — potential buy opportunity |

**Note:** In strong trends, RSI can stay overbought/oversold for extended periods. Don't use RSI in isolation.

## Stochastic Oscillator

- %K > %D = bullish crossover
- > 80: overbought; < 20: oversold
- Divergence from price = potential reversal

## Bollinger Bands

| bb_pct_band | Interpretation |
|-------------|---------------|
| > 1.0 | Price above upper band — overbought / breakout |
| 0.8–1.0 | Approaching upper band — watch for reversal |
| 0.4–0.6 | Middle — consolidation |
| 0–0.2 | Approaching lower band — watch for bounce |
| < 0 | Price below lower band — oversold |

ATR % of price helps judge volatility: >3% = high volatility stock.

## Volume

- **ratio > 1.5**: Above-average volume — confirms price moves
- **ratio < 0.7**: Low volume — treat price moves with skepticism
- **OBV rising + price rising**: Healthy accumulation
- **OBV falling + price rising**: Distribution — potential red flag (divergence)

## Support / Resistance (Pivot Points)

- **R1**: First resistance level
- **S1**: First support level
- **Pivot**: Equilibrium price; trading above = bullish bias

## Composite Scoring Logic

Assign +1 (bullish) or -1 (bearish) per signal, then sum:

| Score | Recommendation |
|-------|---------------|
| +5 to +8 | **STRONG BUY** |
| +2 to +4 | **BUY** |
| -1 to +1 | **HOLD** |
| -2 to -4 | **SELL** |
| -5 to -8 | **STRONG SELL** |

Signals to score:
1. price_vs_ema200 (+1 above / -1 below)
2. golden_cross (+1 true / -1 false)
3. macd_bullish (+1 / -1)
4. macd_hist sign (+1 positive / -1 negative)
5. RSI zone (+1 if 40–70 / -1 if >75 or <25 / 0 neutral)
6. stoch crossover (+1 K>D / -1 K<D)
7. bb_pct_band (+1 if 0.2–0.8 trending up / -1 if >1 reversing)
8. volume obv_trend (+1 rising / -1 falling)

Always supplement the score with narrative explanation. Note any divergences or conflicting signals.

## Disclaimers to Include in Output

- TA is probabilistic, not predictive.
- Past patterns do not guarantee future results.
- This is not financial advice.
- Consider fundamental analysis and macro context alongside TA.
