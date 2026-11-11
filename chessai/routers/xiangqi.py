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
_operation = None


def begin_operation():
    global _operation
    if _operation is not None:
        raise HTTPException(status_code=409, detail="Another game operation is in progress.")
    _operation = object()
    return _operation


def finish_operation(operation):
    global _operation
    if _operation is operation:
        _operation = None


def tick_game():
    game = global_data.game_state
    if game is not None:
        game.tick_clock()
    return game


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


def commit_move_if_unchanged(board, game, updated):
    with global_data.board_lock:
        if global_data.board_array is None or not np.array_equal(board, global_data.board_array):
            raise HTTPException(status_code=409, detail="The board changed during analysis; try again.")
        if not updated.inherit_clock_after_move(game):
            return game
        global_data.game_state = updated
        return updated


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
    time_control: Literal["5", "5+5", "10", "10+5"] | None = None


class DismissWarningRequest(BaseModel):
    warning_id: str


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
        "warning_id": game.warning_id,
        "winner": game.winner,
        "finish_reason": game.finish_reason,
        "clock": game.clock.snapshot() if game.clock else None,
        "busy": _operation is not None,
        "moves": game.moves,
        "board": (detected if detected is not None else game.board).tolist(),
        "accepted_board": game.board.tolist(),
    }


@router.post("/dismiss_warning")
def dismiss_warning(data: DismissWarningRequest):
    with global_data.game_lock:
        game = global_data.game_state
        if game is None:
            raise HTTPException(status_code=409, detail="Game not started.")
        game.dismiss_warning(data.warning_id)
        return snapshot(game)


@router.get("/current_game")
def current_game():
    with global_data.game_lock:
        return snapshot(tick_game())


@router.post("/new_game")
def new_game(data: NewGameRequest):
    board = detected_board()
    if data.position == "starting" and not np.array_equal(board, starting_board_for(data.next_player)):
        raise HTTPException(status_code=422, detail="Set up the physical starting board first, with your opponent's pieces at the top of the detected board.")
    game = AnalyzerGame(data.next_player, data.difficulty, board, data.time_control)
    with global_data.game_lock:
        operation = begin_operation()
    try:
        engine_call(game.prepare, global_data.chess_engine, DIFFICULTY_DEPTHS[data.difficulty])
        with global_data.game_lock:
            game.start_clock()
            commit_if_unchanged(board, game)
            return snapshot(game)
    finally:
        with global_data.game_lock:
            finish_operation(operation)


@router.post("/play")
def play():
    with global_data.game_lock:
        game = tick_game()
        if game is None:
            raise HTTPException(status_code=409, detail="Game not started.")
        board = detected_board()
        operation = begin_operation()
        updated = deepcopy(game)
    try:
        engine_call(updated.end_turn, global_data.chess_engine, board, DIFFICULTY_DEPTHS[game.difficulty])
        with global_data.game_lock:
            game.tick_clock()
            if game.winner:
                return snapshot(game, board)
            return snapshot(commit_move_if_unchanged(board, game, updated), board)
    finally:
        with global_data.game_lock:
            finish_operation(operation)


@router.get("/get_hint")
def get_hint():
    with global_data.game_lock:
        game = tick_game()
        if game is None:
            raise HTTPException(status_code=409, detail="Game not started.")
        if game.winner or game.next_player != game.player:
            raise HTTPException(status_code=409, detail="Hints are available on your turn.")
        board = detected_board()
        operation = begin_operation()
    try:
        try:
            move = global_data.chess_engine.get_best_move(
                game._canonical(board), game.player, depth=DIFFICULTY_DEPTHS[game.difficulty]
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except EngineError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        with global_data.game_lock:
            game.tick_clock()
            if game.winner:
                raise HTTPException(status_code=409, detail="The game has ended.")
            ensure_unchanged(board)
            game.hint_move = game.physical_move(move) if move else None
            return {"best_move": game.hint_move, "difficulty": game.difficulty,
                    "depth": DIFFICULTY_DEPTHS[game.difficulty]}
    finally:
        with global_data.game_lock:
            finish_operation(operation)


@router.get("/game_snapshot")
def game_snapshot():
    with global_data.game_lock:
        game = tick_game()
        if game is None:
            return snapshot(None)
        board = detected_board()
        if _operation is not None or game.winner:
            return snapshot(game, board)
        if game.expected is None or not np.array_equal(board, game.expected):
            engine_call(game.observe, global_data.chess_engine, board)
            return snapshot(game, board)
        operation = begin_operation()
        updated = deepcopy(game)
    try:
        engine_call(updated.observe, global_data.chess_engine, board)
        with global_data.game_lock:
            game.tick_clock()
            if game.winner:
                return snapshot(game, board)
            return snapshot(commit_move_if_unchanged(board, game, updated), board)
    finally:
        with global_data.game_lock:
            finish_operation(operation)
