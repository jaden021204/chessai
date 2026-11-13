import io

from fastapi import APIRouter, HTTPException, Response
from starlette.responses import StreamingResponse

from chessai import global_data, profiling
from chessai.utils import encode_image, original_frame_stream
from chessai.config import DEFAULT_VISUALIZATION_FRAME


router = APIRouter(
    prefix="/api/vision",
    tags=["Vision APIs"],
)

@router.get("/profile_board")
def profile_board():
    if profiling.profiler is None:
        raise HTTPException(status_code=404, detail="Profiling is not enabled.")
    with global_data.board_lock:
        if global_data.board_array is None or global_data.board_capture_profile is None:
            raise HTTPException(status_code=409, detail="No profiled board is available yet.")
        return {
            "board": global_data.board_array.tolist(),
            "capture_id": global_data.board_capture_profile["capture_id"],
            "capture_start_ns": global_data.board_capture_profile["capture_start_ns"],
        }


@router.get("/original_frame", response_class=Response)
async def original_frame():
    return StreamingResponse(original_frame_stream(), media_type="multipart/x-mixed-replace;boundary=frame")


def jpeg_snapshot(frame_name):
    with global_data.frame_lock:
        frame = getattr(global_data, frame_name)
        if frame is None:
            frame = DEFAULT_VISUALIZATION_FRAME
        return Response(content=encode_image(frame), media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})


@router.get("/original_snapshot", response_class=Response)
async def original_snapshot():
    return jpeg_snapshot("original_frame")


@router.get("/debug_aligned_frame", response_class=Response)
async def debug_aligned_frame():
    return jpeg_snapshot("debug_aligned_frame")


@router.get("/debug_markers_frame", response_class=Response)
async def debug_markers_frame():
    return jpeg_snapshot("debug_markers_frame")


@router.get("/debug_frame", response_class=Response)
async def debug_frame():
    with global_data.frame_lock:
        frame = None
        if global_data.debug_frame is None:
            frame = DEFAULT_VISUALIZATION_FRAME
        else:
            frame = global_data.debug_frame
        encoded_frame = encode_image(frame)
        return Response(
            content=encoded_frame,
            media_type="image/jpg",
        )

@router.get("/visualization_frame", response_class=Response)
async def visualization_frame():
    with global_data.frame_lock:
        frame = None
        if global_data.visualization_frame is None:
            frame = DEFAULT_VISUALIZATION_FRAME
        else:
            frame = global_data.visualization_frame
        encoded_frame = encode_image(frame)
        return Response(
            content=encoded_frame,
            media_type="image/jpg",
        )
