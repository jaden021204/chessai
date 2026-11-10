import re

import numpy as np


START_BOARD = np.array([
    ["br", "bn", "bb", "ba", "bk", "ba", "bb", "bn", "br"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "bc", "", "", "", "", "", "bc", ""],
    ["bp", "", "bp", "", "bp", "", "bp", "", "bp"],
    ["", "", "", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "", "", ""],
    ["rp", "", "rp", "", "rp", "", "rp", "", "rp"],
    ["", "rc", "", "", "", "", "", "rc", ""],
    ["", "", "", "", "", "", "", "", ""],
    ["rr", "rn", "rb", "ra", "rk", "ra", "rb", "rn", "rr"],
], dtype=object)

PIECE_NAMES = {
    "k": "king", "a": "advisor", "b": "elephant", "n": "horse",
    "r": "rook", "c": "cannon", "p": "pawn",
}


def canonical_board(board, player):
    return np.rot90(board, 2).copy() if player == "b" else board.copy()


def flip_move(move):
    if not re.fullmatch(r"[a-i][0-9][a-i][0-9]", move):
        raise ValueError(f"Invalid XiangQi move: {move}")
    return "".join(
        chr(ord("i") - (ord(move[i]) - ord("a"))) + str(9 - int(move[i + 1]))
        for i in (0, 2)
    )


def coords(move):
    if not re.fullmatch(r"[a-i][0-9][a-i][0-9]", move):
        raise ValueError(f"Invalid XiangQi move: {move}")
    return ((9 - int(move[1]), ord(move[0]) - ord("a")),
            (9 - int(move[3]), ord(move[2]) - ord("a")))


def apply_move(board, move):
    origin, target = coords(move)
    result = board.copy()
    result[target] = result[origin]
    result[origin] = ""
    return result


def find_move(before, after, player):
    changes = np.argwhere(before != after)
    if not len(changes):
        raise ValueError("No piece moved. Make a move before ending your turn.")
    if len(changes) == 1:
        location = tuple(changes[0])
        piece = before[location] or after[location]
        raise ValueError(f"The {PIECE_NAMES[piece[1]]} is not in a complete move. Restore or finish the move.")
    if len(changes) != 2:
        raise ValueError("More than one piece changed. Restore the board and try again.")
    origin = next((tuple(p) for p in changes if before[tuple(p)] and not after[tuple(p)]), None)
    target = next((tuple(p) for p in changes if after[tuple(p)] and after[tuple(p)] != before[tuple(p)]), None)
    if origin is None or target is None:
        raise ValueError("Could not identify one complete move. Restore the board and try again.")
    piece = before[origin]
    if piece[0] != player:
        raise ValueError(f"The {PIECE_NAMES[piece[1]]} belongs to the other side.")
    if after[target] != piece or (before[target] and before[target][0] == player):
        raise ValueError(f"Invalid move for the {PIECE_NAMES[piece[1]]}.")
    square = lambda pos: chr(ord("a") + pos[1]) + str(9 - pos[0])
    return square(origin) + square(target)
