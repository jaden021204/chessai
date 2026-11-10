import os
import tempfile
import unittest
from unittest.mock import patch

from chessai.game.pikafish_engine import EngineError, PikafishEngine


START_BOARD = [
    ["br", "bn", "bb", "ba", "bk", "ba", "bb", "bn", "br"],
    [""] * 9,
    ["", "bc", "", "", "", "", "", "bc", ""],
    ["bp", "", "bp", "", "bp", "", "bp", "", "bp"],
    [""] * 9,
    [""] * 9,
    ["rp", "", "rp", "", "rp", "", "rp", "", "rp"],
    ["", "rc", "", "", "", "", "", "rc", ""],
    [""] * 9,
    ["rr", "rn", "rb", "ra", "rk", "ra", "rb", "rn", "rr"],
]
FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR"


class PikafishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.log = os.path.join(self.temp.name, "commands")
        script = os.path.abspath("tests/fake_pikafish.py")
        self.engine = PikafishEngine(script, startup_timeout=2, search_timeout=5)
        self.env = patch.dict(os.environ, {"FAKE_ENGINE_LOG": self.log})
        self.env.start()
        self.addCleanup(self.env.stop)

    def commands(self):
        with open(self.log, encoding="utf-8") as log:
            return log.read().splitlines()

    def test_exact_fen_and_all_depth_commands(self):
        self.assertEqual(self.engine.board_array_to_fen(START_BOARD, "r"), FEN + " w")
        self.assertEqual(self.engine.board_array_to_fen(START_BOARD, "b"), FEN + " b")
        for depth in (2, 4, 6, 8):
            self.assertEqual(self.engine.get_best_move(START_BOARD, "r", depth=depth), "b2e2")
        commands = self.commands()
        self.assertEqual(commands.count("position fen " + FEN + " w"), 4)
        for depth in (2, 4, 6, 8):
            self.assertIn(f"go depth {depth}", commands)
        self.assertFalse(self.engine.is_healthy())

    def test_engine_error_is_reported_and_next_attempt_restarts(self):
        with patch.dict(os.environ, {"FAKE_ENGINE_ERROR": "1"}):
            with self.assertRaisesRegex(EngineError, "CRITICAL ERROR"):
                self.engine.get_best_move(START_BOARD, "r")
        self.assertEqual(self.engine.get_best_move(START_BOARD, "r"), "b2e2")
        self.assertFalse(self.engine.is_healthy())

    def test_search_timeout_terminates_process(self):
        self.engine.search_timeout = 0.1
        with patch.dict(os.environ, {"FAKE_ENGINE_TIMEOUT": "1"}):
            with self.assertRaisesRegex(EngineError, "timed out"):
                self.engine.get_best_move(START_BOARD, "r")
        self.assertFalse(self.engine.is_healthy())

    def test_invalid_board_is_rejected_before_launch(self):
        with self.assertRaisesRegex(ValueError, "number of rk"):
            self.engine.get_best_move([[""] * 9 for _ in range(10)], "r")
        self.assertFalse(os.path.exists(self.log))


if __name__ == "__main__":
    unittest.main()
