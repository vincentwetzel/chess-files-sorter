# Chess Tournament Sorter

A Python utility that automatically categorizes and sorts chess tournament video files by extracting the tournament name directly from the video frames using OCR (Optical Character Recognition).

## Overview

The script scans a designated source directory for video files (`.mp4`, `.mkv`, `.avi`, `.mov`, `.flv`), extracts frames at regular intervals, and uses Tesseract OCR to read the text in the top-left corner (typically where the tournament name and year are displayed during a broadcast). Once a tournament name is confidently identified across multiple frames, the video is automatically moved into a newly created or existing folder with that tournament's name.

## Requirements

- **Python 3.x**
- **Tesseract-OCR**: Must be installed on your system. By default, the script expects it at `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- **Python Packages**:
  ```bash
  pip install opencv-python pytesseract numpy
  ```
- **Automated validation**: All code changes must pass `run_ocr_test.py` before they are accepted.
- **OCR design rule**: Tournament-name detection must rely only on cropping the correct screen region and interpreting the OCR layout inside that crop. Word-by-word heuristics, token allowlists, token denylists, and other keyword-specific logic are project-prohibited.

## Configuration

You can configure the behavior of the script by modifying the constants at the top of `main.py`:

- `TESS_PATH`: The absolute path to your Tesseract executable.
- `SOURCE_DIR`: The root directory containing the subdirectories with video files to sort (Default: `J:\CHESS`).
- `EXTENSIONS`: A tuple of supported video file extensions.
- `INTERVAL_SECONDS`: How often (in seconds) to sample a frame from the video for OCR (Default: `30`).

## How it Works

1. **Directory Scanning**: The script iterates through the subdirectories of the `SOURCE_DIR`, ignoring hidden folders (starting with `_` or `.`).
2. **Frame Extraction**: For each video, a frame is extracted every `INTERVAL_SECONDS`.
3. **Region of Interest (ROI)**: The frame is cropped to the portion of the top-left overlay where tournament headers usually appear, keeping the OCR focused on the header instead of nearby commentary text.
4. **Pre-processing**:
   - Converts the cropped ROI to grayscale.
   - Applies binary thresholding to isolate text.
   - Uses morphological dilation to thicken characters, helping the OCR engine recognize thin fonts (like year digits) as solid objects rather than noise.
5. **OCR & Text Cleaning**: `pytesseract` extracts the text. The output is interpreted at the line/layout level inside the cropped header region:
   - Only left-anchored OCR lines from the header area are kept.
   - Invalid characters for Windows folders (`*`, `:`, `<`, `>`, `?`, `|`, `/`, `\`) are stripped or replaced.
6. **Majority Voting & Sorting**: The script tallies up the readings from all sampled frames. The most frequently detected tournament name is chosen. The video is then moved to `SOURCE_DIR/subdir/Tournament Name/`.
7. **Folder Renaming**: Analyzes each tournament folder and main subdirectory to append the total count of video files inside them to the folder name in square brackets (e.g., `Tournament Name [2]`). It also verifies and updates existing counts if the number of videos has changed.

## Usage

1. Ensure Tesseract is installed and `TESS_PATH` in `main.py` is accurate.
2. Update the `SOURCE_DIR` variable to point to your chess videos.
3. Run the script:
   ```bash
   python main.py
   ```
4. Check the console output. It will display the sorting progress (`[SORT]`) and denote any skipped files (`[SKIP]`) where a header couldn't be reliably detected.

## Testing

- Run the dedicated verification script whenever you change OCR logic:
  ```bash
  python run_ocr_test.py
  ```
- Treat the test suite as a hard project requirement—new code should not be merged until this script exits with zero.
- Keep OCR changes limited to region selection and layout interpretation so the implementation stays aligned with the project rule above.
