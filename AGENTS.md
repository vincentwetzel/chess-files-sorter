# Agents and Automated Processes

The Chess Tournament Sorter operates as an automated pipeline, where distinct internal "agents" (modules and functions) work together to process videos, extract information, and organize files. Below is a breakdown of the key actors in this system:

## 1. Frame Extraction Agent (`cv2.VideoCapture`)
**Role:** Samples the video files at specified intervals.
**Behavior:**
- Opens video files (e.g., `.mp4`, `.mkv`) and calculates the total duration and FPS.
- Seeks specific timestamps (every `INTERVAL_SECONDS` by default) to extract frames for analysis, ensuring the script doesn't waste resources analyzing every single frame.

## 2. ROI & Pre-processing Agent (`cv2` & `numpy`)
**Role:** Isolates and enhances the relevant portion of the video frame to prepare it for OCR.
**Behavior:**
- **Cropping (ROI):** Focuses solely on the top 16% height and left 35% width of the frame, where chess broadcast headers (Tournament Name, Year) typically appear.
- **Grayscaling & Thresholding:** Converts the cropped region to grayscale and applies binary thresholding to isolate text from background noise.
- **Dilation:** Uses morphological dilation to artificially "thicken" the text characters. This ensures thin fonts (like the digits in a year) are recognized as solid objects by the OCR engine rather than ignored as noise.
- **Project Rule:** Tournament-name detection must be driven only by selecting the correct screen region and interpreting the OCR layout inside that region. Word-by-word allowlists, denylists, keyword heuristics, or other token-specific logic are not allowed.

## 3. OCR Engine (`pytesseract`)
**Role:** Reads the text from the pre-processed image.
**Behavior:**
- Takes the enhanced binary image and runs it through the Tesseract OCR engine.
- Configured with `--oem 3 --psm 11` to look for sparse text in the image.
- Outputs a dictionary containing the detected text along with its physical coordinates (bounding boxes).

## 4. Text Analyzer & Cleaner (`clean_ocr_results`)
**Role:** Filters out garbage OCR data and formats the final tournament name.
**Behavior:**
- **Left-Anchoring Check:** Keeps only OCR lines that begin in the expected left-aligned tournament-header area of the cropped region.
- **Line Stitching:** Groups OCR output into full lines and preserves their top-to-bottom order to reconstruct the displayed header text.
- **Sanitization:** Removes invalid characters (`*:<>\?|/"`) and replaces slashes with hyphens so the output can be safely used as a folder name.

## 5. File Management Agent (`os` & `shutil`)
**Role:** Executes the final physical sorting of the files.
**Behavior:**
- Aggregates all cleaned OCR readings for a given video and determines the most common result (majority vote).
- If a valid tournament name is confidently identified, it creates a new directory for that tournament (if it doesn't already exist).
- Moves the video file from its source directory into the corresponding tournament directory.
- **Folder Renaming:** Scans tournament directories and their parent subdirectories to count the number of video files they contain, renaming the directories to append this total count in square brackets with a leading space (e.g., `Tournament Name [2]`). It actively updates inaccurate counts if the folder contents change.
