import datetime as dt
import unittest

from monitor import MARKETS, build_metrics, find_signals, format_message


class MonitorTests(unittest.TestCase):
    def test_drawdown_crosses_first_and_second_stage(self):
        rows = [(dt.date(2025, 1, 1) + dt.timedelta(days=i), 100.0) for i in range(252)]
        rows += [
            (dt.date(2025, 10, 1), 95.0),
            (dt.date(2025, 10, 2), 89.0),
            (dt.date(2025, 10, 3), 84.0),
        ]
        metrics = build_metrics(rows)
        self.assertEqual(find_signals(metrics[:-1]), [("第一档", 3000)])
        self.assertEqual(find_signals(metrics), [("第二档", 5000)])

    def test_new_high_allows_next_cycle(self):
        rows = [(dt.date(2025, 1, 1) + dt.timedelta(days=i), 100.0) for i in range(252)]
        rows += [
            (dt.date(2025, 10, 1), 89.0),
            (dt.date(2025, 10, 2), 105.0),
            (dt.date(2025, 10, 3), 94.0),
        ]
        metrics = build_metrics(rows)
        self.assertEqual(find_signals(metrics), [("第一档", 3000)])

    def test_sp500_message_is_distinguishable(self):
        current = build_metrics(
            [(dt.date(2025, 1, 1) + dt.timedelta(days=i), 100.0) for i in range(255)]
        )[-1]
        self.assertIsNotNone(current)
        message = format_message(current, [("第一档", 3000)], MARKETS["sp500"])
        self.assertIn("SP500 标普500加仓提醒", message)


if __name__ == "__main__":
    unittest.main()
