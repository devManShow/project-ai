# AhmadZ Scalper Clean (v4)

Pine Script v5 overlay for TradingView: `ahmadz_scalper.pine`. Paste it into the Pine Editor and add it to the chart.

## How a signal is produced

1. **Trigger**: the ATR trailing stop (the ribbon) flips direction on a closed bar. Each trend leg gives one signal.
2. **Hard gates**: the market is not choppy (ADX < min **and** Choppiness > max), price is not inside a tight 20-bar box, the candle closes in the signal's direction, the cooldown has passed, and price is inside the session (if the session filter is on). In Swing mode, the local EMA stack and the HTF bias must also agree.
3. **Score (0–5)**: Local Trend, HTF Bias, Momentum (MACD histogram building), Volume Flow, Location (in discount/premium or after a liquidity sweep, and not chasing). The signal shows only if the score is at least the minimum.
4. **Late confirmation**: if the flip bar fails a gate, the signal can still fire within *N* bars while the leg holds.
5. **Continuation (`C4`)**: inside an established leg, a new signal can fire after a pullback to the fast EMA, once no trade in the same direction is open.

Hover any signal label to see its score breakdown, the regime readings, and the trade levels. Turn on *Show Dimmed Dots* to see rejected flips and the reason each one was rejected.

## Tuning

| Symptom | Change |
|---|---|
| Too many signals in ranges | Raise *Min ADX* / lower *Max Choppiness*, or raise *Signal Sensitivity* to 1.5–2.0 |
| Entries come too late | Lower *Sensitivity*, set *Late Confirmation Window* to 1–2 |
| Missing good reversals | Lower *Minimum Score* to 3, or turn off the HTF bias |
| Stopped out by wicks | Use the *Hybrid* stop, or raise *ATR SL Multiplier* |

The **Closed Trades** row in the HUD reports trade count, win rate, TP1 hit rate, and net R for the history loaded on the chart. Use it to compare settings. It is an approximation: it assumes the SL is hit first when the SL and a target fall on the same bar, and it ignores spread.
