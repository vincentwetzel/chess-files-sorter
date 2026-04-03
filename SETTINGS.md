# Settings Reference

This document describes all configurable parameters for the Chess Tournament Sorter.

## Configuration File (`config.ini`)

The script reads settings from a `config.ini` file located in the project root. Create one by copying `config.example.ini` and editing the values:

```ini
[Paths]
TESS_PATH = C:\Program Files\Tesseract-OCR\tesseract.exe
SOURCE_DIR = J:\CHESS
TO_SORT_DIR = J:\CHESS\_TO_SORT
```

| Key | Required | Default | Description |
|-----|----------|---------|-------------|
| `TESS_PATH` | Yes | *(none)* | Absolute path to the `tesseract.exe` binary. The script will exit with an error if this path is invalid. |
| `SOURCE_DIR` | Yes | *(none)* | Root directory containing subdirectories of chess video files to be sorted. |
| `TO_SORT_DIR` | Yes | *(none)* | Staging directory where newly downloaded videos are placed. Files here are sorted using **filename-based extraction** (not OCR) into a `YYYY - MM` year/month folder structure. |

If `config.ini` is missing or malformed, the script will print an error message and terminate.

## Hardcoded Constants (`main.py`)

The following constants are defined at the top of `main.py` and can be adjusted if needed:

| Constant | Default | Description |
|----------|---------|-------------|
| `EXTENSIONS` | `('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm')` | Tuple of video file extensions the script will process. |
| `INTERVAL_SECONDS` | `60` | How often (in seconds) to sample a frame from each video for OCR. A lower value means more frames checked but slower processing; a higher value is faster but may miss the tournament header. |
| `ROI_TOP_RATIO` | `0.0` | The top edge of the Region of Interest (ROI) as a ratio of frame height. `0.0` means start from the very top of the frame. |
| `ROI_HEIGHT_RATIO` | `0.14` | The height of the ROI as a ratio of frame height. `0.14` captures the top 14% of the frame, where broadcast headers typically appear. |
| `ROI_WIDTH_RATIO` | `0.23` | The width of the ROI as a ratio of frame width. `0.23` captures the left 23% of the frame, targeting left-aligned tournament text. |
| `LINE_ANCHOR_RATIO` | `0.28` | The left-edge threshold within the ROI (as a ratio of ROI width). Only OCR lines starting to the left of this boundary are kept, filtering out commentary or sidebar text. |

## OCR Engine Configuration

The Tesseract OCR engine is invoked with the following fixed configuration:

- **OEM (OCR Engine Mode):** `3` — Uses both the legacy Tesseract engine and the LSTM neural network mode.
- **PSM (Page Segmentation Mode):** `11` — Sparse text mode. Looks for text scattered across the image without assuming any specific layout.

These values are passed directly to `pytesseract.image_to_data()` in `process_frame()`.

## Filename-Based Extraction (for `_TO_SORT` files)

Files in the `TO_SORT_DIR` staging directory are processed using **filename parsing** instead of OCR. This is faster and more reliable for newly downloaded YouTube videos.

### Expected Filename Pattern

```
PREFIX -- Players -- Tournament Name R3 [Channel Name][MM-DD-YYYY][VideoID].mp4
```

**Example:**
```
GOTD -- Praggnanandhaa vs Javokhir Sindarov -- FIDE Candidates Tournament 2026 R3
 [agadmator's Chess Channel][03-31-2026][4KxRXcpOtJE].mp4
```

### Extraction Rules

| Component | Regex / Logic | Extracted Value |
|-----------|--------------|-----------------|
| **Date** | `\[(\d{2})-(\d{2})-(\d{4})\]` | `2026 - 03` (year-month folder name) |
| **Tournament** | Text between last `--` and first `[`, with round numbers stripped | `FIDE Candidates Tournament 2026` |
| **Round stripping** | `\s+[Rr]ound?\s*\d+\s*$` and `\s+[Rr]\d+\s*$` | Removes `R3`, `Round 4`, etc. |

The extracted tournament name is then passed through `sanitize_tournament_text()` to remove Windows-illegal characters.

### Resulting Folder Structure

```
SOURCE_DIR/
├── 2026 - 03 [35]/
│   └── FIDE Candidates Tournament 2026 [4]/
│       └── GOTD -- Praggnanandhaa vs Sindarov ....mp4
```

## External Dependencies

| Tool / Library | Purpose | Installation |
|----------------|---------|-------------|
| **Tesseract-OCR** | OCR text recognition engine. | Install from [GitHub releases](https://github.com/tesseract-ocr/tesseract/releases) and set `TESS_PATH` in `config.ini`. |
| **OpenCV (`cv2`)** | Video frame extraction, image preprocessing (grayscale, thresholding, dilation). | `pip install opencv-python` |
| **pytesseract** | Python wrapper for Tesseract OCR. | `pip install pytesseract` |
| **numpy** | Image array manipulation for preprocessing. | `pip install numpy` |
| **ffprobe** (part of FFmpeg) | Video codec detection in Phase 3. | Install FFmpeg and ensure `ffprobe` is on your system `PATH`. |

## Script Execution

### Direct Python Execution
```bash
python main.py
```

### Windows Batch Script
Run `run_chess_sorter_py.bat` to execute with default settings, or pass a custom source directory as the first argument:
```cmd
run_chess_sorter_py.bat
run_chess_sorter_py.bat "D:\My\Chess\Videos"
```

## Test Configuration

Two test runners are available:

| File | Description |
|------|-------------|
| `run_ocr_test.py` | Quick validation script. Processes all `.png` images in `tests/assets/` and compares OCR output against the filename (minus extension). Exits immediately after displaying results. |
| `tests/test_ocr.py` | Full `unittest`-based test suite. Uses `unittest.TestCase` and the `analyze_image()` function. Run with `python -m unittest tests/test_ocr.py`. |

Test images should be named exactly as the expected tournament name, e.g., `Candidates 2024.png` should produce the OCR output `Candidates 2024`.
