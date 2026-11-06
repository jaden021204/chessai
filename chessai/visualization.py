import cv2
import numpy as np

from chessai import config

pieces = [
    "rr",
    "rn",
    "rb",
    "ra",
    "rk",
    "rc",
    "rp",
    "br",
    "bn",
    "bb",
    "ba",
    "bk",
    "bc",
    "bp",
]

ref_board_image = cv2.imread(config.REFERENCE_BOARD_IMAGE_PATH)
ref_piece_images = {}
for p in pieces:
    image = cv2.imread(f"data/pieces/{p}.png", cv2.IMREAD_UNCHANGED)
    size = tuple(max(1, int(dimension * config.VISUALIZATION_PIECE_SCALE + 0.5))
                 for dimension in (image.shape[1], image.shape[0]))
    ref_piece_images[p] = cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)


def overlay(background, overlay, x, y):
    background_width = background.shape[1]
    background_height = background.shape[0]

    if x >= background_width or y >= background_height:
        return background

    h, w = overlay.shape[0], overlay.shape[1]

    if x + w > background_width:
        w = background_width - x
        overlay = overlay[:, :w]

    if y + h > background_height:
        h = background_height - y
        overlay = overlay[:h]

    if overlay.shape[2] < 4:
        overlay = np.concatenate(
            [
                overlay,
                np.ones((overlay.shape[0], overlay.shape[1], 1), dtype=overlay.dtype)
                * 255,
            ],
            axis=2,
        )

    overlay_image = overlay[..., :3]
    mask = overlay[..., 3:] / 255.0

    background[y : y + h, x : x + w] = (1.0 - mask) * background[
        y : y + h, x : x + w
    ] + mask * overlay_image

    return background


def draw_board_canvas(board, hint_move=None):
    piece_height, piece_width = next(iter(ref_piece_images.values())).shape[:2]
    xs = [x + config.VISUALIZATION_OFFSET_X for x in config.VISUALIZATION_COLUMN_X]
    ys = [y + config.VISUALIZATION_OFFSET_Y for y in config.VISUALIZATION_ROW_Y]
    left = max(0, piece_width // 2 - min(xs))
    top = max(0, piece_height // 2 - min(ys))
    right = max(0, max(xs) - piece_width // 2 + piece_width - ref_board_image.shape[1])
    bottom = max(0, max(ys) - piece_height // 2 + piece_height - ref_board_image.shape[0])
    border_color = tuple(int(value) for value in ref_board_image[-1, ref_board_image.shape[1] // 2])
    draw = cv2.copyMakeBorder(
        ref_board_image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=border_color
    )
    for i in range(10):
        for j in range(9):
            if board[i][j]:
                image = ref_piece_images[board[i][j]]
                x = xs[j] + left - image.shape[1] // 2
                y = ys[i] + top - image.shape[0] // 2
                draw = overlay(draw, image, x, y)

    if hint_move:
        # Draw a hint move on the board
        from_x = xs[ord(hint_move[0]) - ord("a")] + left
        from_y = ys[9 - int(hint_move[1])] + top
        to_x = xs[ord(hint_move[2]) - ord("a")] + left
        to_y = ys[9 - int(hint_move[3])] + top
        draw = cv2.arrowedLine(
            draw,
            (from_x, from_y),
            (to_x, to_y),
            (255, 0, 0),
            10,
            tipLength=20.0/np.sqrt((to_x-from_x)**2+(to_y-from_y)**2),
        )
        draw = cv2.circle(draw, (to_x, to_y), 10, (0, 255, 0), -1)

    return draw
