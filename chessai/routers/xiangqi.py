from copy import deepcopy
from typing import Literal

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chessai import global_data
from chessai.game.analyzer import AnalyzerGame, starting_board_for
from chessai.game.pikafish_engine import EngineError

DIFFICULTY_DEPTHS = {"easy": 2, "medium": 4, "hard": 6, "expert": 8}
router = APIRouter(prefix="/api/xiangqi", tags=["XiangQi APIs"])


def detected_board():
    with global_data.board_lock:
        if global_data.board_array is None:
            raise HTTPException(status_code=409, detail="No board has been detected yet.")
        return global_data.board_array.copy()


def ensure_unchanged(board):
    with global_data.board_lock:
        if global_data.board_array is None or not np.array_equal(board, global_data.board_array):
            raise HTTPException(status_code=409, detail="The board changed during analysis; try again.")


def commit_if_unchanged(board, game):
    with global_data.board_lock:
        if global_data.board_array is None or not np.array_equal(board, global_data.board_array):
            raise HTTPException(status_code=409, detail="The board changed during analysis; try again.")
        global_data.game_state = game


def engine_call(function, *args):
    try:
        return function(*args)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EngineError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


class NewGameRequest(BaseModel):
    next_player: Literal["r", "b"]
    difficulty: Literal["easy", "medium", "hard", "expert"] = "medium"
    mode: Literal["analyzer"] = "analyzer"
    position: Literal["current", "starting"] = "current"


def snapshot(game, detected=None):
    if game is None:
        return {"is_playing": False, "next_player": None, "difficulty": None}
    return {
        "is_playing": True,
        "next_player": game.next_player,
        "player": game.player,
        "difficulty": game.difficulty,
        "mode": "analyzer",
        "best_move": game.hint_move,
        "waiting_for_computer_move": game.expected is not None,
        "warning": game.warning,
        "winner": game.winner,
        "moves": game.moves,
        "board": (detected if detected is not None else game.board).tolist(),
        "accepted_board": game.board.tolist(),
    }


@router.get("/current_game")
def current_game():
    with global_data.game_lock:
        return snapshot(global_data.game_state)


@router.post("/new_game")
def new_game(data: NewGameRequest):
    board = detected_board()
    if data.position == "starting" and not np.array_equal(board, starting_board_for(data.next_player)):
        raise HTTPException(status_code=422, detail="Set up the physical starting board first, with your pieces at the top.")
    game = AnalyzerGame(data.next_player, data.difficulty, board)
    with global_data.game_lock:
        engine_call(game.prepare, global_data.chess_engine, DIFFICULTY_DEPTHS[data.difficulty])
        commit_if_unchanged(board, game)
    return snapshot(game)


@router.post("/play")
def play():
    with global_data.game_lock:
        game = global_data.game_state
        if game is None:
            raise HTTPException(status_code=409, detail="Game not started.")
        board = detected_board()
        updated = deepcopy(game)
        engine_call(updated.end_turn, global_data.chess_engine, board, DIFFICULTY_DEPTHS[game.difficulty])
        commit_if_unchanged(board, updated)
        return snapshot(updated, board)


@router.get("/get_hint")
def get_hint():
    with global_data.game_lock:
        game = global_data.game_state
        if game is None:
            raise HTTPException(status_code=409, detail="Game not started.")
        if game.winner or game.next_player != game.player:
            raise HTTPException(status_code=409, detail="Hints are available on your turn.")
        board = detected_board()
        try:
            move = global_data.chess_engine.get_best_move(
                game._canonical(board), game.player, depth=DIFFICULTY_DEPTHS[game.difficulty]
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except EngineError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        ensure_unchanged(board)
        game.hint_move = game.physical_move(move) if move else None
        return {"best_move": game.hint_move, "difficulty": game.difficulty,
                "depth": DIFFICULTY_DEPTHS[game.difficulty]}


@router.get("/game_snapshot")
def game_snapshot():
    with global_data.game_lock:
        game = global_data.game_state
        if game is None:
            return snapshot(None)
        board = detected_board()
        updated = deepcopy(game)
        engine_call(updated.observe, global_data.chess_engine, board)
        commit_if_unchanged(board, updated)
        return snapshot(updated, board)
