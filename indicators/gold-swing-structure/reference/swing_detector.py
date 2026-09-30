"""Reference implementation of the Gold Swing Structure indicator.

This is a line-for-line port of ``gold_swing_structure.pine`` so the logic can
be tested and tuned offline on bar data exported from TradingView
(chart menu -> "Export chart data..." gives a CSV with time/open/high/low/close).

The detector is strictly causal: the decision on bar ``i`` only reads bars
``0..i``. A swing is *drawn* back on the bar where the extreme happened, but it
only *exists* from ``confirm_index`` onwards -- that delay is the price paid for
not showing fake swings.

Usage:
    python swing_detector.py XAUUSD_1m.csv [--rev-mult 6] [--atr-len 100]
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass, field


@dataclass
class Params:
    atr_len: int = 100          # ATR length used as the volatility unit
    rev_mult: float = 6.0       # reversal needed to confirm a swing, in ATRs
    min_rev: float = 0.0        # absolute floor for the reversal (price units, e.g. $3 on gold)
    confirm_on_close: bool = True   # measure the reversal with closes (True) or wicks (False)


@dataclass
class Swing:
    kind: str                   # "H" or "L"
    index: int                  # bar of the extreme (where the label is drawn)
    price: float
    confirm_index: int          # first bar on which the swing was known (no repaint after this)
    threshold: float            # reversal size that was required, in price
    label: str = ""             # HH / LH / HL / LL ("H" / "L" for the first of each kind)


@dataclass
class Result:
    swings: list[Swing] = field(default_factory=list)
    leg_dir: list[int] = field(default_factory=list)      # +1 up-leg, -1 down-leg, 0 undecided
    trend: list[int] = field(default_factory=list)        # structure trend: +1 up, -1 down, 0 unknown
    threshold: list[float] = field(default_factory=list)


def rma_atr(high, low, close, length):
    """ta.atr(length): Wilder's RMA of true range, seeded with an SMA like Pine."""
    out, tr_sum, atr = [], 0.0, math.nan
    for i in range(len(high)):
        tr = high[i] - low[i] if i == 0 else max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        if i < length:
            tr_sum += tr
            atr = tr_sum / length if i == length - 1 else math.nan
        else:
            atr = (atr * (length - 1) + tr) / length
        out.append(atr)
    return out


def detect(high, low, close, p: Params = Params()) -> Result:
    n = len(high)
    atr = rma_atr(high, low, close, p.atr_len)
    res = Result()

    direction = 0                       # 0 until the first swing is confirmed
    ext, ext_i = math.nan, -1           # extreme of the current leg
    hi, hi_i, lo, lo_i = math.nan, -1, math.nan, -1   # only used while direction == 0
    last_h = last_l = math.nan          # last confirmed swing prices
    trend = 0

    def add_swing(kind, idx, price, i, thr):
        nonlocal last_h, last_l
        if kind == "H":
            label = "" if math.isnan(last_h) else ("HH" if price > last_h else "LH")
            last_h = price
        else:
            label = "" if math.isnan(last_l) else ("HL" if price > last_l else "LL")
            last_l = price
        res.swings.append(Swing(kind, idx, price, i, thr, label))

    def lowest_since(start, i):
        # lowest low in (start, i], the oldest bar on ties; the current bar if the range is empty
        best, best_i = low[i], i
        for k in range(i - 1, start, -1):
            if low[k] <= best:
                best, best_i = low[k], k
        return best, best_i

    def highest_since(start, i):
        best, best_i = high[i], i
        for k in range(i - 1, start, -1):
            if high[k] >= best:
                best, best_i = high[k], k
        return best, best_i

    for i in range(n):
        thr = math.nan if math.isnan(atr[i]) else max(p.rev_mult * atr[i], p.min_rev)
        dn_src = close[i] if p.confirm_on_close else low[i]
        up_src = close[i] if p.confirm_on_close else high[i]

        if not math.isnan(thr):
            if direction == 0:
                if math.isnan(hi) or high[i] > hi:
                    hi, hi_i = high[i], i
                if math.isnan(lo) or low[i] < lo:
                    lo, lo_i = low[i], i
                if hi - dn_src >= thr:
                    add_swing("H", hi_i, hi, i, thr)
                    direction = -1
                    ext, ext_i = lowest_since(hi_i, i)
                elif up_src - lo >= thr:
                    add_swing("L", lo_i, lo, i, thr)
                    direction = 1
                    ext, ext_i = highest_since(lo_i, i)
            elif direction == 1:
                if high[i] > ext:
                    ext, ext_i = high[i], i
                if ext - dn_src >= thr:
                    add_swing("H", ext_i, ext, i, thr)
                    direction = -1
                    ext, ext_i = lowest_since(ext_i, i)
            else:
                if low[i] < ext:
                    ext, ext_i = low[i], i
                if up_src - ext >= thr:
                    add_swing("L", ext_i, ext, i, thr)
                    direction = 1
                    ext, ext_i = highest_since(ext_i, i)

        # structure trend: flips only when a close breaks the last confirmed swing
        if not math.isnan(last_h) and close[i] > last_h:
            trend = 1
        elif not math.isnan(last_l) and close[i] < last_l:
            trend = -1

        res.leg_dir.append(direction)
        res.trend.append(trend)
        res.threshold.append(thr)
    return res


def read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    key = {k.lower(): k for k in rows[0]}
    col = lambda name: [float(r[key[name]]) for r in rows]
    t = [r[key["time"]] for r in rows] if "time" in key else list(range(len(rows)))
    return t, col("high"), col("low"), col("close")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--atr-len", type=int, default=Params.atr_len)
    ap.add_argument("--rev-mult", type=float, default=Params.rev_mult)
    ap.add_argument("--min-rev", type=float, default=Params.min_rev)
    ap.add_argument("--wick", action="store_true", help="confirm with wicks instead of closes")
    a = ap.parse_args()
    t, h, l, c = read_csv(a.csv)
    p = Params(a.atr_len, a.rev_mult, a.min_rev, not a.wick)
    res = detect(h, l, c, p)
    print(f"{'time':<22}{'swing':<7}{'price':>12}{'confirmed at':>24}{'lag(bars)':>11}")
    for s in res.swings:
        print(f"{str(t[s.index]):<22}{(s.label or s.kind):<7}{s.price:>12.3f}{str(t[s.confirm_index]):>24}{s.confirm_index - s.index:>11}")
    lags = [s.confirm_index - s.index for s in res.swings]
    if lags:
        print(f"\n{len(res.swings)} swings, median confirmation lag {sorted(lags)[len(lags) // 2]} bars")


if __name__ == "__main__":
    main()
