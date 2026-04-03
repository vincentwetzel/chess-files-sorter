# Architecture

This document describes the internal architecture of the Chess Tournament Sorter.

## System Overview

The Chess Tournament Sorter is a single-file Python application (`main.py`) that automates the categorization of chess tournament videos. It works by extracting frames from videos, running OCR on the broadcast overlay region, identifying the tournament name through majority voting, and then physically moving files into organized directories.

The system operates in **four sequential phases**:

```
┌──────────────────────────────────────────────────────────────────┐
│  Phase 0: Sort _TO_SORT  │  Phase 1: Sort Videos               │
│  (filename-based)        │  (OCR analyze & move)               │
├──────────────────────────────────────────────────────────────────┤
│  Phase 2: Update Folder  │  Phase 3: Scan Codecs               │
│  Counts (rename w/ [N])  │  Phase 4: Count & Log Files          │
└──────────────────────────────────────────────────────────────────┘
```

## Processing Pipeline

### Frame Extraction → Preprocessing → OCR → Analysis → File Operations

```
Video File
    │
    ▼
┌─────────────────────┐
│  Frame Extraction   │  cv2.VideoCapture seeks frames at INTERVAL_SECONDS
│  (cv2.VideoCapture) │  Extracts frames at calculated positions
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  ROI & Preprocess   │  Crop to top 14% height × left 23% width
│  (cv2 + numpy)      │  Grayscale → Threshold → Dilate → Invert
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  OCR Engine          │  pytesseract with --oem 3 --psm 11
│  (pytesseract)      │  Outputs text + bounding box coordinates
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Text Analyzer      │  Left-anchor filtering, line stitching,
│  (clean_ocr_results)│  sanitization for folder-safe names
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Majority Voting     │  Counter.most_common(1) selects the
│  (analyze_video)    │  most frequently detected tournament name
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  File Management     │  Move video → Tournament folder
│  (os + shutil)      │  Rename folders with [count] suffix
└─────────────────────┘
```

## Module Breakdown

### 1. Configuration & Initialization

**Location:** Top-level `main.py` (lines 1–33)

- Loads `config.ini` using `configparser`.
- Sets `pytesseract.pytesseract.tesseract_cmd` to the user-provided Tesseract path.
- Defines global constants for ROI ratios, intervals, and file extensions.
- Exits early with a clear message if configuration is missing or invalid.

### 2. Frame Extraction Agent (`cv2.VideoCapture`)

**Functions:** `analyze_video()`

- Opens video files and reads `FPS` and `total_frames` metadata.
- Calculates video duration and seeks to every `INTERVAL_SECONDS` timestamp.
- Extracts individual frames via `cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)`.
- Passes each frame to `process_frame()` for analysis.
- Collects all OCR results and uses `collections.Counter` to determine the most common tournament name (majority vote).

### 3. ROI & Preprocessing Agent (`cv2` + `numpy`)

**Functions:** `process_frame()`

- **Cropping:** Extracts the top 14% height × left 23% width of the frame. This region is where chess broadcast overlays typically display the tournament name.
- **Grayscale Conversion:** `cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)`
- **Upscaling:** Resizes the image by 2× using bicubic interpolation to improve OCR accuracy on small text.
- **Thresholding:** Applies Otsu's binary thresholding to separate text from background.
- **Dilation:** Morphological dilation with a 2×2 kernel thickens thin characters so they are not discarded as noise.
- **Inversion:** `cv2.bitwise_not()` inverts the image to produce dark text on a light background, which Tesseract handles best.

### 4. OCR Engine (`pytesseract`)

**Functions:** `process_frame()`

- Invokes Tesseract with `--oem 3 --psm 11` (sparse text, combined engine modes).
- Uses `output_type=pytesseract.Output.DICT` to receive structured output including text, bounding boxes, and layout metadata (block number, paragraph number, line number).
- Scales bounding box coordinates back down by the `scale_factor` to match the original ROI dimensions.

### 5. Text Analyzer & Cleaner (`clean_ocr_results`, `sanitize_tournament_text`)

**Functions:** `clean_ocr_results()`, `sanitize_tournament_text()`

- **Line Reconstruction:** Groups OCR output by `(block_num, par_num, line_num)` to reconstruct full text lines from individual word detections.
- **Spatial Sorting:** Orders lines top-to-bottom, then left-to-right based on their bounding box coordinates.
- **Left-Anchor Filtering:** Discards any line whose left edge is beyond `LINE_ANCHOR_RATIO × ROI_width`, removing sidebar commentary and unrelated text.
- **Sanitization:** Strips Windows-illegal characters (`* : < > ? | / \`) and collapses consecutive whitespace. Replaces forward slashes with hyphens so the output is a valid folder name.

### 5b. Filename-Based Tournament Extractor (`extract_tournament_and_date_from_filename`)

**Functions:** `extract_tournament_and_date_from_filename()`, `find_year_month_folder()`, `sort_to_sort_directory()`

- **Purpose:** Processes files in the `TO_SORT_DIR` staging directory without using OCR. Instead, it parses the YouTube-style filename to extract tournament name and upload date.
- **Filename Pattern:** `PREFIX -- Players -- Tournament Name R3 [Channel][MM-DD-YYYY][VideoID].ext`
- **Date Extraction:** Uses regex `\[(\d{2})-(\d{2})-(\d{4})\]` to find the `[MM-DD-YYYY]` bracket and produces a `YYYY - MM` year/month string.
- **Tournament Extraction:** Takes the text between the last `--` separator and the first `[` bracket, then strips trailing round numbers (`R3`, `Round 3`, etc.) using regex.
- **Sanitization:** Passes the result through `sanitize_tournament_text()` to produce a folder-safe name.
- **Year/Month Folder Matching:** `find_year_month_folder()` scans `SOURCE_DIR` for folders matching the `YYYY - MM` pattern (with optional `[N]` suffix) and returns the existing folder path if found.
- **Sorting Logic:** `sort_to_sort_directory()` creates the `YYYY - MM` folder if needed, then creates or finds the tournament subfolder inside it, and moves the file there.

### 6. Image Analysis Helper (`analyze_image`)

**Functions:** `analyze_image()`

- Accepts a single image file path (e.g., a screenshot).
- Loads the image with `cv2.imread()` and passes it through `process_frame()`.
- Used by the test suite (`tests/test_ocr.py`, `run_ocr_test.py`) for quick OCR validation without processing a full video.

### 7. File Management Agent (`os` + `shutil`)

**Functions:** `move_video()`, `update_folder_video_counts()`, `process_directory()`

- **process_directory():** Iterates over all subdirectories of `SOURCE_DIR`, skipping hidden folders (`_` or `.` prefix). For each video file, calls `analyze_video()` and then `move_video()` if a tournament name is found.
- **move_video():** Checks for an existing tournament folder (case-insensitive match, accounting for the `[N]` suffix). Creates a new directory if none exists. Moves the video file using `shutil.move()`.
- **update_folder_video_counts():** Walks through all tournament folders at depth 2 and parent subdirectories at depth 1. Counts `.mp4`, `.mkv`, etc. files inside each. Renames the directory to append `[count]` if the current suffix is missing or inaccurate. Also counts loose video files in parent directories and updates their names accordingly.

### 8. Codec Scanner (`get_video_codec`, `report_codecs`)

**Functions:** `get_video_codec()`, `report_codecs()`

- **Phase 3** of the main pipeline.
- Uses `ffprobe` (part of FFmpeg) to extract the `codec_name` from each video's first video stream.
- Groups files by codec and prints a report of all non-H.264 videos.
- Returns counts of H.264 vs. non-H.264 files for the final report.

### 9. File Counter & Logger (`count_and_log_files`)

**Functions:** `count_and_log_files()`

- **Phase 4** of the main pipeline.
- Recursively walks `SOURCE_DIR` and counts all files except `.py` scripts and the log file itself.
- Appends a timestamped entry to `file_count_log.txt` in the source directory.

## Data Flow

```
TO_SORT_DIR/
├── GOTD -- Praggnanandhaa vs Sindarov -- FIDE Candidates Tournament 2026 R3
│    [agadmator's Chess Channel][03-31-2026][4KxRXcpOtJE].mp4
│    → extract_tournament_and_date_from_filename()
│    → tournament: "FIDE Candidates Tournament 2026"
│    → year_month: "2026 - 03"
│
SOURCE_DIR/
├── _TO_SORT/
│   └── (files get processed in Phase 0)
│
│ After Phase 0:
├── 2026 - 03 [35]/
│   ├── FIDE Candidates Tournament 2026/
│   │   └── GOTD -- Praggnanandhaa vs Sindarov ....mp4
│   └── Prague International Chess Festival 2026/
│       └── ...
│
├── subdir_A/
│   ├── video1.mp4 ──▶ analyze_video() ──▶ "Candidates 2024"
│   ├── video2.mkv ──▶ analyze_video() ──▶ "Candidates 2024"
│   └── video3.mp4 ──▶ analyze_video() ──▶ "Tata Steel 2025"
│
│ After Phase 1:
│ ├── Candidates 2024/
│ │   ├── video1.mp4
│ │   └── video2.mkv
│ └── Tata Steel 2025/
│     └── video3.mp4
│
│ After Phase 2:
│ ├── 2026 - 03 [38]/          (count updated)
│ │   ├── FIDE Candidates Tournament 2026 [1]
│ │   └── Prague International Chess Festival 2026 [15]
│ ├── subdir_A [2]/
│ │   ├── Candidates 2024 [2]/
│ │   │   ├── video1.mp4
│ │   │   └── video2.mkv
│ │   └── Tata Steel 2025 [1]/
│ │       └── video3.mp4
│
│ After Phase 3:
│   (codec scan output printed to console)
│
│ After Phase 4:
│   file_count_log.txt updated with total file count
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Filename-based extraction for _TO_SORT** | Downloaded YouTube videos follow a consistent naming convention with tournament name, date, and channel info embedded in brackets. Parsing filenames is faster and more reliable than OCR for these files, and avoids re-processing videos that already have known metadata. |
| **Year/month folder structure** | Organizing tournaments under `YYYY - MM` folders (e.g., `2026 - 03 [35]`) provides chronological grouping that scales well over time. The `[N]` suffix gives an at-a-glance count of total videos in that month. |
| **Majority voting across sampled frames** | A single frame may miss the header (e.g., during transitions). Sampling at intervals and picking the most common result provides robustness without analyzing every frame. |
| **Dilation preprocessing** | Thin fonts and small digits (e.g., years like `2024`) can be lost during thresholding. Dilation artificially thickens strokes so Tesseract treats them as text rather than noise. |
| **Left-anchor filtering** | Broadcast overlays often include commentary, player names, and clock timers in the same general region. Restricting to text that begins near the left edge of the ROI filters out this noise. |
| **Project rule: no word-level heuristics** | The tournament name must be determined purely by spatial region selection and layout interpretation. Word-by-word allowlists, denylists, and keyword matching are explicitly prohibited to keep the system generalizable across different tournaments and broadcast styles. |
| **Upscaling by 2×** | Tesseract performs better on larger text. The 2× bicubic upscale before thresholding significantly improves recognition of small overlay text. Coordinates are scaled back down afterward to maintain correct spatial filtering. |
