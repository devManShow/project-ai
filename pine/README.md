# Daily Sweep & FVG (TradingView, Pine Script v6)

| File | What it is |
|---|---|
| `daily_sweep_fvg.pine` | The indicator: signals, PDH/PDL, FVG boxes, TP/SL lines, alerts, and a dashboard showing results in R (multiples of the risk taken). |
| `daily_sweep_fvg_strategy.pine` | The same signal logic as a `strategy()`, so TradingView's **Strategy Tester** can backtest it in money terms, after commission and slippage. |

## The rules

1. **Daily bias.** Compare the last two completed daily bars. A higher high plus a higher low means longs only. A lower high plus a lower low means shorts only. Any other day means no trades (set *Daily Bias Filter = Off* to trade both directions).
2. **Sweep.** During the NY session on the 5m chart, price must break the lowest low (for longs) or highest high (for shorts) of the previous *Sweep Lookback* bars.
3. **Fair value gap.** A displacement candle must leave a 3-candle gap in the trade's direction that is at least *Min FVG Size × ATR*.
4. **Entry.** The first later bar that trades back into the gap is the entry, at that bar's close, if all of these hold:
   * the bar holds the gap
   * the bar is inside the *Entry Window*
   * the target pays at least *Min Reward:Risk*
   * the *Max Trades per Day* limit hasn't been reached

   The setup is cancelled if price breaks the sweep extreme first, or if *FVG Expiry* bars pass without a retest.
5. **Exit.**
   * The stop goes beyond the sweep extreme, plus a small ATR buffer.
   * The target is PDH/PDL or a fixed multiple of the risk.
   * With *Close Open Trade at Session End* on, any trade still open is closed at the session's last bar.

Everything runs on closed bars, so a signal never appears and then vanishes. The 1h and 4h charts only show PDH/PDL and the bias background.

## Installing

1. Open the file and copy **all** of it. The indicator is about 400 lines; the last lines are the `alert(...)` call.
2. In TradingView open Pine Editor → *Open* → *New blank indicator* (use *New blank strategy* for the strategy file). Select all of the template text, then paste over it.
3. Click **Add to chart** and use a **5 minute** chart.

If the editor shows *"The script must have at least one output function call" (CE10213)*, part of the paste is missing. Compare the line count in the editor with the file.

## Testing whether it makes money

No settings can guarantee profit. Test it like this:

1. Add `daily_sweep_fvg_strategy.pine` to a 5m chart of the market you trade.
2. In *Properties*, set **commission and slippage to match your broker**. For futures, also set *Max Leverage* to `0` and use *Fixed Quantity* contracts.
3. In *Strategy Tester*, start with **net profit, profit factor, max drawdown, and the number of trades**. Win rate alone means little: a 40% win rate at 2R per win makes money, while a 70% win rate at 0.3R per win loses.
4. **Avoid curve fitting.** Tune the inputs on the older half of the history only. Then check, without changing anything, that the newer half still makes money. If it only works on the data it was tuned on, it doesn't work.
5. Fewer than about 100 trades is too few to tell skill from luck.

## Inputs worth testing first

| Input | Default | Why it matters |
|---|---|---|
| Min Reward:Risk | 1.5 | Stops the system taking trades where the stop is far away and the target is close. |
| Entry Window | 09:30–12:00 | Afternoon entries rarely reach PDH/PDL before the close. |
| Take Profit | PDH / PDL | Try *Fixed R* at 1.5–3R. PDH/PDL is often far away. |
| FVG Expiry | 12 bars | A gap that's an hour old is a weaker setup. |
| Daily Bias Filter | Daily HH/HL | This allows trades only on strong trend days. *Off* gives far more trades. |
