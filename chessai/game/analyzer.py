import time

import numpy as np

from chessai.game.board_moves import (
    PIECE_NAMES, START_BOARD, apply_move, canonical_board, coords, find_move, flip_move,
)


class AnalyzerGame:
    def __init__(self, player, difficulty, board):
        self.player = player
        self.difficulty = difficulty
        self.board = board.copy()
        self.next_player = "r"
        self.moves = []
        self.hint_move = None
        self.expected = None
        self.warning = None
        self.winner = None
        self._wrong_board = None
        self._wrong_since = None

    def _canonical(self, board):
        return canonical_board(board, self.player)

    def engine_move(self, move):
        return flip_move(move) if self.player == "r" else move

    def physical_move(self, move):
        return flip_move(move) if self.player == "r" else move

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
            self._wrong_board = None
            self._wrong_since = None
            if not legal:
                self.winner = "b" if self.player == "r" else "r"
        elif np.array_equal(detected, self.board):
            self._wrong_board = None
            self._wrong_since = None
            self.warning = None
        else:
            now = time.monotonic() if now is None else now
            if self._wrong_board is None or not np.array_equal(self._wrong_board, detected):
                self._wrong_board = detected.copy()
                self._wrong_since = now
                self.warning = None
            elif now - self._wrong_since >= 2:
                origin, _ = coords(self.hint_move)
                self.warning = f"Please place the {PIECE_NAMES[self.board[origin][1]]} at the correct location."


def starting_board_for(player):
    return np.rot90(START_BOARD, 2).copy() if player == "r" else START_BOARD.copy()
