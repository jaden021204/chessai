import argparse

import cv2

from chessai.vision.piece_detector import PieceDetector


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the piece detector on an already aligned XiangQi board image."
    )
    parser.add_argument(
        "--image",
        default="test_board.png",
        help="Path to an already aligned board image (default: test_board.png).",
    )
    parser.add_argument(
        "--output",
        help="Optional path to save an image with detected boxes and board cells.",
    )
    args = parser.parse_args()

    image = cv2.imread(args.image)
    if image is None:
        parser.error(f"Could not read image: {args.image}")

    detector = PieceDetector()
    try:
        board = detector.detect(image, visualize=image)
    finally:
        detector.model.close()

    print("Detected 10x9 board:")
    for row in board.tolist():
        print(row)
    print(f"Detected occupied squares: {sum(bool(square) for square in board.flat)}")

    if args.output and not cv2.imwrite(args.output, image):
        raise OSError(f"Could not save visualization to: {args.output}")
    if args.output:
        print(f"Visualization saved to: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
