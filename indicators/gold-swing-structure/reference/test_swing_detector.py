"""Tests for the swing detector. Run: python -m unittest -v (from this folder)."""

import random
import unittest

from swing_detector import Params, detect

P = Params(atr_len=10, rev_mult=5.0)


def path_to_bars(path, spread=0.5):
    """Turn a close path into bars whose range is `spread` around the move."""
    high, low, close = [], [], []
    prev = path[0]
    for c in path:
        high.append(max(prev, c) + spread)
        low.append(min(prev, c) - spread)
        close.append(c)
        prev = c
    return high, low, close


def leg(a, b, step=1.0):
    n = int(round(abs(b - a) / step))
    return [a + (b - a) * k / n for k in range(1, n + 1)]


def random_walk(n, seed):
    rnd = random.Random(seed)
    high, low, close, c = [], [], [], 2000.0
    for _ in range(n):
        o = c
        c = o + rnd.gauss(0, 1.0) + (rnd.random() < 0.01) * rnd.choice([-1, 1]) * rnd.uniform(5, 15)
        high.append(max(o, c) + abs(rnd.gauss(0, 0.6)))
        low.append(min(o, c) - abs(rnd.gauss(0, 0.6)))
        close.append(c)
    return high, low, close


class SwingDetectorTest(unittest.TestCase):
    def test_finds_the_turning_points_of_a_clean_zigzag(self):
        path = [100.0] * 15 + leg(100, 130) + leg(130, 110) + leg(110, 150) + leg(150, 120) + leg(120, 135)
        high, low, close = path_to_bars(path)
        res = detect(high, low, close, P)
        got = [(s.label or s.kind, round(s.price, 1)) for s in res.swings]
        self.assertEqual(got, [("L", 99.5), ("H", 130.5), ("HL", 109.5), ("HH", 150.5), ("HL", 119.5)])
        for s in res.swings:  # the label sits on the extreme bar itself
            self.assertEqual(s.price, high[s.index] if s.kind == "H" else low[s.index])

    def test_wiggles_smaller_than_the_threshold_are_skipped(self):
        path = [100.0] * 15
        for k in range(40):  # steady climb with 3-point pullbacks, threshold is ~5 x ATR
            path += leg(path[-1], path[-1] + 5) + leg(path[-1] + 5, path[-1] + 2)
        high, low, close = path_to_bars(path)
        res = detect(high, low, close, P)
        self.assertLessEqual(len(res.swings), 1)   # at most the starting low
        self.assertEqual(res.leg_dir[-1], 1)

    def test_wick_spike_does_not_confirm_when_using_closes(self):
        path = [100.0] * 15 + leg(100, 120) + leg(120, 95)
        high, low, close = path_to_bars(path)
        spike = len(high) - 5
        high[spike] += 40   # news wick in the down-leg that closes right back
        on_close = detect(high, low, close, P)
        on_wick = detect(high, low, close, Params(P.atr_len, P.rev_mult, confirm_on_close=False))
        self.assertEqual([s.kind for s in on_close.swings], ["L", "H"])
        # measured on wicks, the spike fakes a low + high pair
        self.assertEqual([s.kind for s in on_wick.swings], ["L", "H", "L", "H"])
        self.assertEqual(on_wick.swings[-1].index, spike)

    def test_reversal_inside_one_bar_confirms_on_that_bar(self):
        path = [100.0] * 15 + leg(100, 130)
        high, low, close = path_to_bars(path)
        high.append(140.0); low.append(100.0); close.append(101.0)   # blow-off bar closing far below its high
        res = detect(high, low, close, P)
        top = res.swings[-1]
        self.assertEqual((top.kind, top.price), ("H", 140.0))
        self.assertEqual(top.index, top.confirm_index)

    def test_swings_alternate_and_sit_on_leg_extremes(self):
        for seed in range(5):
            high, low, close = random_walk(3000, seed)
            res = detect(high, low, close, Params(atr_len=50, rev_mult=6.0))
            sw = res.swings
            self.assertGreater(len(sw), 10)
            for a, b in zip(sw, sw[1:]):
                self.assertNotEqual(a.kind, b.kind)
                self.assertLessEqual(a.index, b.index)   # equal only for an outside bar that is both ends of a leg
                self.assertLessEqual(a.confirm_index, b.confirm_index)
            for prev, s in zip(sw, sw[1:]):
                # the swing is the extreme of everything since the previous swing, up to its confirmation
                # (a later wick may poke past it: with close confirmation that alone is not a reversal)
                seg = range(prev.index + 1, s.confirm_index + 1)
                self.assertTrue(prev.index <= s.index <= s.confirm_index)
                if s.kind == "H":
                    self.assertEqual(s.price, high[s.index])
                    self.assertTrue(all(high[k] <= s.price for k in seg))
                    self.assertLessEqual(close[s.confirm_index], s.price - s.threshold)
                else:
                    self.assertEqual(s.price, low[s.index])
                    self.assertTrue(all(low[k] >= s.price for k in seg))
                    self.assertGreaterEqual(close[s.confirm_index], s.price + s.threshold)

    def test_never_repaints(self):
        high, low, close = random_walk(1500, seed=42)
        full = detect(high, low, close, Params(atr_len=50, rev_mult=6.0))
        for end in range(60, len(high) + 1, 37):
            part = detect(high[:end], low[:end], close[:end], Params(atr_len=50, rev_mult=6.0))
            known = [s for s in full.swings if s.confirm_index < end]
            self.assertEqual(part.swings, known)
            self.assertEqual(part.trend, full.trend[:end])
            self.assertEqual(part.leg_dir, full.leg_dir[:end])

    def test_trend_follows_breaks_of_structure(self):
        path = [100.0] * 15 + leg(100, 130) + leg(130, 110) + leg(110, 140) + leg(140, 100)
        high, low, close = path_to_bars(path)
        res = detect(high, low, close, P)
        first_break_up = next(i for i, c in enumerate(close) if i > 60 and c > 130.5)
        self.assertEqual(res.trend[first_break_up - 1], 0)
        self.assertEqual(res.trend[first_break_up], 1)
        self.assertEqual(res.trend[-1], -1)   # closed below the 109.5 swing low


if __name__ == "__main__":
    unittest.main()
