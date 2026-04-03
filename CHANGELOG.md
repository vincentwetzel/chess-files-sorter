# Changelog

All notable changes to the Chess Tournament Sorter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `config.ini`-based configuration for `TESS_PATH`, `SOURCE_DIR`, and `TO_SORT_DIR` (replacing hardcoded paths in `main.py`).
- `config.example.ini` as a template for new installations.
- Phase 0: `_TO_SORT` directory processing — filename-based tournament extraction for newly downloaded YouTube videos. Files are sorted into `YYYY - MM / Tournament Name` folder structure.
- `extract_tournament_and_date_from_filename()` — parses YouTube-style filenames to extract tournament name and upload date.
- `find_year_month_folder()` — locates existing year/month folders (e.g., `2026 - 03 [35]`) to avoid duplicates.
- `sort_to_sort_directory()` — processes the `TO_SORT_DIR` staging directory, creating year/month and tournament folders as needed.
- Phase 4: File counting and logging — recursively counts all non-script files in `SOURCE_DIR` and appends a timestamped entry to `file_count_log.txt`.

### Changed
- Moved `TESS_PATH` and `SOURCE_DIR` from inline constants to `config.ini`, with proper error handling for missing or malformed configuration.
- `ROI_HEIGHT_RATIO` changed from `0.16` to `0.14` to tighten the crop region on broadcast headers.
- `ROI_WIDTH_RATIO` changed from `0.35` to `0.23` to focus more precisely on the left-aligned tournament header.
- `INTERVAL_SECONDS` changed from `30` to `60` for faster video processing.
- Image preprocessing pipeline now upscales frames by 2× (bicubic interpolation) before thresholding, then scales bounding box coordinates back down. This significantly improves OCR accuracy on small text.
- `process_frame()` now inverts the thresholded image (`cv2.bitwise_not`) to produce dark text on a light background, which Tesseract handles best.
- Batch script (`run_chess_sorter_py.bat`) now accepts an optional first argument to override `SOURCE_DIR` from the command line.

### Fixed
- Smart quote handling: `sanitize_tournament_text()` now strips Unicode curly quotes (`"`) and standard double quotes (`"`).
- Tournament name trailing punctuation: leading/trailing periods, commas, colons, semicolons, hyphens, and spaces are now trimmed from the final result.
- Folder renaming logic now correctly handles parent subdirectories (depth 1) as well as tournament folders (depth 2), updating both with accurate video counts including loose files.

### Removed
- Hardcoded default `SOURCE_DIR` path from `main.py`; the value must now be provided in `config.ini`.

---

## [Initial Release]

### Added
- Core video sorting pipeline: frame extraction → ROI crop → grayscale → threshold → dilate → OCR → text cleaning → majority voting → file move.
- Tesseract OCR integration with `--oem 3 --psm 11` (sparse text mode).
- Left-anchor filtering to reject commentary/sidebar text outside the tournament header region.
- `shutil.move`-based file sorting into tournament-named subdirectories.
- Automatic folder renaming with `[N]` suffix reflecting the number of videos inside.
- H.264 codec scanning via `ffprobe` (Phase 3).
- Windows batch launcher (`run_chess_sorter_py.bat`).
- OCR test suite (`run_ocr_test.py` and `tests/test_ocr.py`) with `tests/assets/` for validation images.
- `run_ocr_test.py` as a quick validation runner that compares OCR output against image filenames.
- `AGENTS.md` documenting the internal agent-based processing pipeline.
- `README.md` with setup instructions and usage guide.
