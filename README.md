# ChessAI - Chinese Chess Game Analyzer

ChessAI is a groundbreaking tool that brings together computer vision, chess algorithms, and advanced analytics to revolutionize the Chinese Chess analytics landscape. With ChessAI, you don't need expensive electronic boards to analyze your games. Simply use your regular board, set up a camera to capture the position, and let ChessAI do the rest.

- Main source code: `chesssai`.
- Deep Learning / Data Preparation: `dnn_models/data_preparation` - Currenly only support for Chinese Chess (XiangQi), [contact me](https://aicurious.io/contact) for the license and the source code of the data preparation tool.
- Deep Learning / Training: `dnn_models/training`.

![ChessAI](https://github.com/vietanhdev/chessai/raw/main/docs/images/screenshot.png)

## Roadmap

- [x] Chess position detection.
- [x] Chess engine integration.
- [x] Move suggestion.
- [ ] Deep learning model for chess board detection (No need to use ARUCO markers).

## Raspberry Pi and Android setup

For the current Raspberry Pi 5 installation and usage instructions, see
[docs/RASPBERRY_PI_SETUP.md](docs/RASPBERRY_PI_SETUP.md). The Android preview
and its optional remote controller are documented in
[android_app/README.md](android_app/README.md).

The running application uses the supplied Ultralytics YOLO26s model exported
to NCNN and the [Pikafish](https://github.com/official-pikafish/Pikafish)
Xiangqi engine. Install Pikafish separately and use the path to your actual
binary. Keep the ARUCO markers visible to align the physical board.

## Run the app

```bash
ENGINE_PATH="/full/path/to/pikafish" python -m chessai.app --run_app
```

Replace `ENGINE_PATH` with the path to the chess engine executable file.

## Data preparation & Training

This project uses computer vision and deep learning to detect chess pieces and chess board position.

**AI flow for chess position detection:**

![AI flow for chess position detection](https://raw.githubusercontent.com/vietanhdev/chessai/main/docs/images/ai_flow.png)

- Go to [dnn_models](./dnn_models) folder and follow the instructions in the `README.md` file to prepare the data and train the model.
- **NOTE:** Only training source code and pretrained models are included in this repository. The data preparation scripts and the training datset are not included. [Contact me](https://aicurious.io/contact) for the license and the data.

## References

- This project was initially built for [Hackster's OpenCV AI Competition 2023](https://www.hackster.io/contests/opencv-ai-competition-2023). Hackster Project: [ChessAI - Chinese Chess Game Analyzer](https://www.hackster.io/vietanhdev/chessai-chinese-chess-game-analyzer-4be768).
- Current piece detector: [Ultralytics YOLO26s](https://docs.ultralytics.com/models/yolo26/), exported to [ncnn](https://github.com/Tencent/ncnn). Check the supplied model metadata for its license.
- Current chess engine: [Pikafish](https://github.com/official-pikafish/Pikafish).
- UI components: [shadcn-ui](https://github.com/shadcn-ui/ui) - License: MIT.
- The original project also used YOLOX and godogpaw. Legacy code and references
  retain those names where they describe those original components; they are
  not the active detector or engine. See [docs/PROJECT_REFERENCES.md](docs/PROJECT_REFERENCES.md).
# YOLO26s-RaspPI5-XiangQi
# YOLO26s-RaspPI5-XiangQi
