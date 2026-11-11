import unittest

from chessai.game.clock import GameClock


class GameClockTests(unittest.TestCase):
    def test_increments_switch_and_timeout(self):
        clock = GameClock("5+5")
        clock.start("r", now=100)
        self.assertIsNone(clock.tick(now=110))
        self.assertEqual(clock.remaining["r"], 290)
        self.assertIsNone(clock.complete_move(now=112))
        self.assertEqual(clock.remaining["r"], 293)
        self.assertEqual(clock.active, "b")
        self.assertEqual(clock.tick(now=412), "b")
        self.assertEqual(clock.remaining["b"], 0)
        self.assertIsNone(clock.active)
        self.assertIsNone(clock.tick(now=500))

    def test_all_requested_controls(self):
        for control, seconds, increment in (
            ("5", 300, 0), ("5+5", 300, 5),
            ("10", 600, 0), ("10+5", 600, 5),
        ):
            with self.subTest(control=control):
                clock = GameClock(control)
                self.assertEqual(clock.remaining, {"r": seconds, "b": seconds})
                self.assertEqual(clock.increment, increment)


if __name__ == "__main__":
    unittest.main()
