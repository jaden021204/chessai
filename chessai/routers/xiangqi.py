from typing import Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from chessai import global_data
from chessai.game.game_state import GameState, Player
from chessai.game.pikafish_engine import EngineError

DIFFICULTY_DEPTHS = {"easy": 2, "medium": 4, "hard": 6, "expert": 8}

router = APIRouter(
    prefix="/api/xiangqi",
    tags=["XiangQi APIs"],
)

@router.get("/current_game")
async def current_game():
    return {
        "is_playing": global_data.game_state is not None,
        "next_player": global_data.game_state.next_player if global_data.game_state is not None else None,
        "difficulty": global_data.game_state.difficulty if global_data.game_state is not None else None,
    }

class NewGameRequest(BaseModel):
    next_player: Literal["r", "b"]
    difficulty: Literal["easy", "medium", "hard", "expert"] = "medium"

@router.post("/new_game", response_class=Response)
async def new_game(data: NewGameRequest):
    with global_data.board_lock:
        if global_data.board_array is None:
            raise HTTPException(status_code=409, detail="No board has been detected yet.")
        board = global_data.board_array.copy()
    with global_data.game_lock:
        global_data.game_state = GameState(board, data.next_player, data.difficulty)
        global_data.prev_game_state = global_data.game_state
    return Response(
        content="OK",
        media_type="text/plain",
    )

@router.post("/play")
async def play():
    if global_data.game_state is None:
        return {
            "success": False,
            "message": "Game not started",
        }
    if global_data.game_state.is_checkmate():
        return {
            "success": False,
            "message": "Checkmate",
        }
    with global_data.game_lock:
        prev_game_state = global_data.prev_game_state.copy()
        game_state = global_data.game_state.copy()

    # move = Move.from_game_states(prev_game_state, game_state)
    # if move is None:
    #     return {
    #         "success": False,
    #         "message": "Invalid move",
    #     }

    with global_data.game_lock:
        global_data.prev_game_state = game_state
        global_data.board_array = global_data.board_array
        global_data.game_state.hint_move = None
        global_data.game_state.next_player = Player.BLACK if global_data.game_state.next_player == Player.RED else Player.RED

    return {
        "success": True,
        # "move": str(move),
    }

@router.get("/get_hint")
def get_hint():
    with global_data.game_lock:
        game = global_data.game_state
        if game is None:
            raise HTTPException(status_code=409, detail="Game not started.")
        player = game.next_player
        difficulty = game.difficulty
    with global_data.board_lock:
        if global_data.board_array is None:
            raise HTTPException(status_code=409, detail="No board has been detected yet.")
        board = global_data.board_array.copy()
    try:
        best_move = global_data.chess_engine.get_best_move(
            board, player, depth=DIFFICULTY_DEPTHS[difficulty]
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EngineError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    with global_data.board_lock:
        if global_data.board_array is None or not np.array_equal(board, global_data.board_array):
            raise HTTPException(status_code=409, detail="The board changed during analysis; request a new hint.")
        with global_data.game_lock:
            if global_data.game_state is not game or game.next_player != player or game.difficulty != difficulty:
                raise HTTPException(status_code=409, detail="The game changed during analysis; request a new hint.")
            game.hint_move = best_move
    return {"best_move": best_move, "difficulty": difficulty, "depth": DIFFICULTY_DEPTHS[difficulty]}

@router.get("/game_snapshot")
async def game_snapshot():
    if global_data.game_state is None:
        return {
            "is_playing": False,
            "next_player": None,
            "board": None,
            "best_move": None,
        }

    return {
        "is_playing": True,
        "next_player": global_data.game_state.next_player.name.lower() if hasattr(global_data.game_state.next_player, "name") else None,
        "board": global_data.board_array.tolist() if global_data.board_array is not None else None,
        "best_move": getattr(global_data.game_state, "hint_move", None),
    }
