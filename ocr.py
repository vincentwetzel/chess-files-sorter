import cv2
import pytesseract
import re
import numpy as np
from collections import Counter
from config import (
    TESS_PATH, ROI_TOP_RATIO, ROI_HEIGHT_RATIO,
    ROI_WIDTH_RATIO, LINE_ANCHOR_RATIO, INTERVAL_SECONDS
)

pytesseract.pytesseract.tesseract_cmd = TESS_PATH

def sanitize_tournament_text(text):
    text = text.replace('"', '').replace('"', '').replace('"', '')
    text = text.replace("/", "-").replace("\\", "-")
    text = re.sub(r'[*:<>\?|]', '', text)
    text = " ".join(text.split()).strip(". , : ; -")
    text = re.sub(r'\b[Il1]{2,3}\b', 'III', text)
    return text

def clean_ocr_results(ocr_data, left_limit):
    """
    Reconstructs the header from left-anchored OCR lines inside the ROI.
    """
    if 'text' not in ocr_data:
        return ""

    lines = {}
    for i in range(len(ocr_data['text'])):
        text = ocr_data['text'][i].strip()
        if not text:
            continue

        line_key = (
            ocr_data['block_num'][i],
            ocr_data['par_num'][i],
            ocr_data['line_num'][i],
        )
        line = lines.setdefault(line_key, {'left': [], 'top': [], 'parts': []})
        line['left'].append(ocr_data['left'][i])
        line['top'].append(ocr_data['top'][i])
        line['parts'].append(text)

    if not lines:
        return ""

    ordered_lines = sorted(
        (
            {
                'left': min(line['left']),
                'top': min(line['top']),
                'text': " ".join(line['parts']),
            }
            for line in lines.values()
        ),
        key=lambda line: (line['top'], line['left'])
    )

    final_parts = []
    for line in ordered_lines:
        if line['left'] <= left_limit:
            cleaned_line = sanitize_tournament_text(line['text'])
            if cleaned_line:
                final_parts.append(cleaned_line)

    return sanitize_tournament_text(" ".join(final_parts))

def process_frame(frame):
    h, w, _ = frame.shape

    top = int(h * ROI_TOP_RATIO)
    bottom = int(h * (ROI_TOP_RATIO + ROI_HEIGHT_RATIO))
    right = int(w * ROI_WIDTH_RATIO)
    roi = frame[top:bottom, 0:right]
    left_limit = int(roi.shape[1] * LINE_ANCHOR_RATIO)

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Keep the OCR input high-contrast and thicken thin glyphs so Tesseract
    # is less likely to drop narrow characters such as a leading digit.
    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)

    kernel = np.ones((2, 2), np.uint8)
    processed = cv2.dilate(binary, kernel, iterations=1)
    data = pytesseract.image_to_data(processed, config='--oem 3 --psm 11', output_type=pytesseract.Output.DICT)

    return clean_ocr_results(data, left_limit=left_limit)

def analyze_image(image_path):
    """
    Analyzes a single image (screenshot) to detect the tournament name.
    Useful for testing.
    """
    frame = cv2.imread(image_path)
    if frame is None:
        return None
    return process_frame(frame)

def analyze_video(video_path):
    """
    Extracts frames from a video and determines the most common tournament name.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, 0, 0

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or total_frames <= 0:
        cap.release()
        return None, 0, 0
        
    duration_seconds = int(total_frames / fps)
    checks = 0
    raw_readings = []

    for sec in range(INTERVAL_SECONDS, duration_seconds, INTERVAL_SECONDS):
        frame_id = int(sec * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ret, frame = cap.read()
        if not ret: continue
            
        checks += 1
        cleaned = process_frame(frame)
        
        if cleaned:
            raw_readings.append(cleaned)

    cap.release()
    if not raw_readings: return None, 0, checks

    data_counter = Counter(raw_readings)
    common = data_counter.most_common(1)
    
    if not common: return None, 0, checks
    return common[0][0], common[0][1], checks
