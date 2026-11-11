import time
import uuid

import numpy as np

from chessai.game.board_moves import (
    PIECE_NAMES, START_BOARD, apply_move, canonical_board, coords, find_move, flip_move,
)
from chessai.game.clock import GameClock


class AnalyzerGame:
    def __init__(self, player, difficulty, board, time_control=None):
        self.player = player
        self.difficulty = difficulty
        self.board = board.copy()
        self.next_player = "r"
        self.moves = []
        self.hint_move = None
        self.expected = None
        self.warning = None
        self.warning_id = None
        self._warning_after = 0
        self.winner = None
        self.finish_reason = None
        self.clock = GameClock(time_control) if time_control else None
        self._wrong_board = None
        self._wrong_since = None

    def start_clock(self):
        if self.clock and not self.winner:
            self.clock.start(self.next_player)

    def tick_clock(self):
        if self.clock and not self.winner:
            expired = self.clock.tick()
            if expired:
                self.winner = "b" if expired == "r" else "r"
                self.finish_reason = "timeout"
                self.expected = None
                self.hint_move = None
                self.warning = None
                self.warning_id = None

    def inherit_clock_after_move(self, previous):
        self.clock = previous.clock
        if self.clock:
            expired = self.clock.complete_move()
            if expired:
                previous.tick_clock()
                previous.winner = "b" if expired == "r" else "r"
                previous.finish_reason = "timeout"
                previous.expected = None
                previous.hint_move = None
                previous.warning = None
                previous.warning_id = None
                return False
            if self.winner:
                self.clock.stop()
        return True

    def _canonical(self, board):
        return canonical_board(board, self.player)

    def engine_move(self, move):
        return flip_move(move) if self.player == "b" else move

    def physical_move(self, move):
        return flip_move(move) if self.player == "b" else move

    def legal_moves(self, engine, board, side):
        return engine.legal_moves(self._canonical(board), side)

    def computer_suggestion(self, engine, board, side, legal, depth):
        move = engine.get_best_move(self._canonical(board), side, depth=depth)
        if move not in legal:
            raise ValueError("Pikafish returned a move outside its legal move list.")
        return self.physical_move(move)

    def prepare(self, engine, depth):
        legal = self.legal_moves(engine, self.board, self.next_player)
        if not legal:
            self.winner = "b"
        elif self.player == "b":
            self.hint_move = self.computer_suggestion(engine, self.board, "r", legal, depth)
            self.expected = apply_move(self.board, self.hint_move)

    def end_turn(self, engine, detected, depth):
        if self.winner:
            raise ValueError("The game has ended.")
        if self.next_player != self.player:
            raise ValueError("Wait for the computer's move.")
        move = find_move(self.board, detected, self.player)
        legal = self.legal_moves(engine, self.board, self.player)
        if self.engine_move(move) not in legal:
            origin, _ = coords(move)
            raise ValueError(f"Illegal move for the {PIECE_NAMES[self.board[origin][1]]}.")
        next_player = "b" if self.player == "r" else "r"
        opposing_moves = self.legal_moves(engine, detected, next_player)
        suggestion = None
        if opposing_moves:
            suggestion = self.computer_suggestion(engine, detected, next_player, opposing_moves, depth)
        self.board = detected.copy()
        self.moves.append(move)
        self.next_player = next_player
        self.hint_move = suggestion
        if suggestion:
            self.expected = apply_move(self.board, suggestion)
        else:
            self.winner = self.player

    def observe(self, engine, detected, now=None):
        if self.next_player == self.player or self.expected is None or self.winner:
            return
        if np.array_equal(detected, self.expected):
            legal = self.legal_moves(engine, detected, self.player)
            self.board = self.expected.copy()
            self.moves.append(self.hint_move)
            self.next_player = self.player
            self.expected = None
            self.hint_move = None
            self.warning = None
            self.warning_id = None
            self._wrong_board = None
            self._wrong_since = None
            if not legal:
                self.winner = "b" if self.player == "r" else "r"
        elif np.array_equal(detected, self.board):
            self._wrong_board = None
            self._wrong_since = None
            self.warning = None
            self.warning_id = None
        else:
            now = time.monotonic() if now is None else now
            if self._wrong_board is None or not np.array_equal(self._wrong_board, detected):
                self._wrong_board = detected.copy()
                self._wrong_since = now
                self.warning = None
                self.warning_id = None
            elif now - self._wrong_since >= 2 and now >= self._warning_after and self.warning is None:
                origin, _ = coords(self.hint_move)
                self.warning = f"Please place the {PIECE_NAMES[self.board[origin][1]]} at the correct location."
                self.warning_id = uuid.uuid4().hex

    def dismiss_warning(self, warning_id, now=None):
        if self.warning_id != warning_id or self.warning is None:
            return False
        self.warning = None
        self.warning_id = None
        self._warning_after = (time.monotonic() if now is None else now) + 5
        return True


def starting_board_for(player):
    return np.rot90(START_BOARD, 2).copy() if player == "b" else START_BOARD.copy()
