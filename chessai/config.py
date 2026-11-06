import cv2

REFERENCE_ARUCO_IMAGE_PATH = "data/board_with_aruco.png"
REFERENCE_BOARD_IMAGE_PATH = "data/board.png"

# Camera capture resolution is a request; the camera may choose another size.
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 960
PIECE_DETECTION_CONFIDENCE = 0.35

# Visualization coordinates are in pixels on data/board.png, not the camera image.
VISUALIZATION_PIECE_SCALE = 1.5
VISUALIZATION_OFFSET_X = 0
VISUALIZATION_OFFSET_Y = 0
VISUALIZATION_COLUMN_X = [57, 167, 277, 387, 497, 607, 717, 827, 937]
VISUALIZATION_ROW_Y = [49, 164, 278, 392, 505, 621, 735, 849, 963, 1076]

CELL_CENTER_POSITIONS = [
    [[180, 72], [290, 72], [400, 72], [510, 72], [620, 72], [730, 72], [840, 72], [950, 72], [1060, 72]],
    [[180, 188], [290, 188], [400, 188], [510, 188], [620, 188], [730, 188], [840, 188], [950, 188], [1060, 188]],
    [[180, 304], [290, 304], [400, 304], [510, 304], [620, 304], [730, 304], [840, 304], [950, 304], [1060, 304]],
    [[180, 420], [290, 420], [400, 420], [510, 420], [620, 420], [730, 420], [840, 420], [950, 420], [1060, 420]],
    [[180, 536], [290, 536], [400, 536], [510, 536], [620, 536], [730, 536], [840, 536], [950, 536], [1060, 536]],
    [[180, 648], [290, 648], [400, 648], [510, 648], [620, 648], [730, 648], [840, 648], [950, 648], [1060, 648]],
    [[180, 764], [290, 764], [400, 764], [510, 764], [620, 764], [730, 764], [840, 764], [950, 764], [1060, 764]],
    [[180, 876], [290, 876], [400, 876], [510, 876], [620, 876], [730, 876], [840, 876], [950, 876], [1060, 876]],
    [[180, 992], [290, 992], [400, 992], [510, 992], [620, 992], [730, 992], [840, 992], [950, 992], [1060, 992]],
    [[180, 1100], [290, 1100], [400, 1100], [510, 1100], [620, 1100], [730, 1100], [840, 1100], [950, 1100], [1060, 1100]],
]
CELL_PADDED_WIDTH = 50
half_padded = int(CELL_PADDED_WIDTH / 2)
CELL_RECTANGLES = []
for row in CELL_CENTER_POSITIONS:
    for p in row:
        CELL_RECTANGLES.append(
            [
                p[0] - half_padded, p[1] - half_padded, p[0] + half_padded, p[1] + half_padded,
            ]
        )


PIECE_DETECTION_MODEL_PATH = "data/my_model_ncnn_model"
PIECE_DETECTION_CLASS_NAMES = [
    "B_A",
    "B_C",
    "B_E",
    "B_H",
    "B_K",
    "B_P",
    "B_R",
    "R_A",
    "R_C",
    "R_E",
    "R_H",
    "R_K",
    "R_P",
    "R_R",
]

DEFAULT_VISUALIZATION_FRAME = cv2.imread(
    "data/default_visualization_frame.jpeg"
)
