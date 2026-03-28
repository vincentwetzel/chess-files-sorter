import cv2
import pytesseract
import os
import shutil
import re
import numpy as np
from collections import Counter, defaultdict
import configparser
import sys
import subprocess
import json
from datetime import datetime

# --- CONFIGURATION ---
config = configparser.ConfigParser()
if not config.read('config.ini'):
    print("Error: config.ini file not found! Please create one based on config.example.ini.")
    sys.exit(1)

try:
    TESS_PATH = config.get('Paths', 'TESS_PATH')
    SOURCE_DIR = config.get('Paths', 'SOURCE_DIR')
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    print(f"Error reading config.ini: {e}")
    sys.exit(1)

pytesseract.pytesseract.tesseract_cmd = TESS_PATH

EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm')
INTERVAL_SECONDS = 60
ROI_TOP_RATIO = 0.0
ROI_HEIGHT_RATIO = 0.14
ROI_WIDTH_RATIO = 0.23
LINE_ANCHOR_RATIO = 0.28


def sanitize_tournament_text(text):
    text = text.replace('“', '').replace('”', '').replace('"', '')
    text = text.replace('/', '-').replace('\\', '-')
    text = re.sub(r'[*:<>\?|]', '', text)
    return " ".join(text.split()).strip(". , : ; -")


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
    scale_factor = 2
    scaled = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((2, 2), np.uint8)
    thickened = cv2.dilate(thresh, kernel, iterations=1)
    inverted = cv2.bitwise_not(thickened)

    data = pytesseract.image_to_data(inverted, config='--oem 3 --psm 11', output_type=pytesseract.Output.DICT)

    if 'left' in data:
        for i in range(len(data['left'])):
            data['left'][i] = int(data['left'][i] / scale_factor)
            data['top'][i] = int(data['top'][i] / scale_factor)
            data['width'][i] = int(data['width'][i] / scale_factor)
            data['height'][i] = int(data['height'][i] / scale_factor)

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

def move_video(file_path, subdir_path, tournament, matches, checks):
    """
    Handles the physical file moving logic.
    """
    file = os.path.basename(file_path)
    
    existing_dir = None
    if os.path.exists(subdir_path):
        for d in os.listdir(subdir_path):
            d_path = os.path.join(subdir_path, d)
            if not os.path.isdir(d_path): continue
                
            match = re.search(r'\s*\[(\d+)\]$', d)
            base_name = d[:match.start()].strip() if match else d.strip()
            
            if base_name.lower() == tournament.lower():
                existing_dir = d_path
                break
                
    if existing_dir:
        target_dir = existing_dir
    else:
        target_dir = os.path.join(subdir_path, tournament)
        os.makedirs(target_dir)
    
    print(f"  [SORT] {file} -> {os.path.basename(target_dir)} ({matches}/{checks})")
    shutil.move(file_path, os.path.join(target_dir, file))

def process_directory(source_dir):
    """
    Traverses the directory, analyzes videos, and moves them.
    """
    print("\n--- Phase 1: Sorting Videos ---")
    subdirs = [d for d in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, d))]
    sorted_count, skipped_count = 0, 0
    
    for subdir in subdirs:
        if subdir.startswith(('_', '.')): continue
        
        subdir_path = os.path.join(source_dir, subdir)
        video_files = [f for f in os.listdir(subdir_path) if f.lower().endswith(EXTENSIONS)]
        
        for file in video_files:
            file_path = os.path.join(subdir_path, file)
            tournament, m, c = analyze_video(file_path)
            
            if tournament:
                move_video(file_path, subdir_path, tournament, m, c)
                sorted_count += 1
            else:
                print(f"  [SKIP] {file} (Header incomplete)")
                skipped_count += 1
                
    return sorted_count, skipped_count

def update_folder_video_counts(source_dir):
    """
    Analyzes tournament subdirectories (depth 2) and their parent subdirectories (depth 1) 
    and appends/updates the video count in square brackets at the end of their name.
    """
    print(f"\n--- Phase 2: Updating Folder Video Counts ---")
    subdirs = [d for d in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, d))]
    renamed_count = 0
    
    for subdir in subdirs:
        if subdir.startswith(('_', '.')): continue
        subdir_path = os.path.join(source_dir, subdir)
        
        try:
            tournament_folders = [d for d in os.listdir(subdir_path) if os.path.isdir(os.path.join(subdir_path, d))]
        except Exception:
            continue
            
        subdir_total_videos = 0
            
        for t_folder in tournament_folders:
            t_folder_path = os.path.join(subdir_path, t_folder)
            
            try:
                videos = [f for f in os.listdir(t_folder_path) if os.path.isfile(os.path.join(t_folder_path, f)) and f.lower().endswith(EXTENSIONS)]
            except Exception:
                continue
                
            video_count = len(videos)
            subdir_total_videos += video_count
            
            match = re.search(r'\s*\[(\d+)\]$', t_folder)
            if match:
                current_count = int(match.group(1))
                if current_count == video_count:
                    continue
                base_name = t_folder[:match.start()].strip()
            else:
                base_name = t_folder.strip()
                
            new_name = f"{base_name} [{video_count}]"
            new_path = os.path.join(subdir_path, new_name)
            
            if t_folder != new_name:
                try:
                    os.rename(t_folder_path, new_path)
                    print(f"  [RENAME] '{t_folder}' -> '{new_name}'")
                    renamed_count += 1
                except Exception as e:
                    print(f"  [ERROR] Failed to rename '{t_folder}': {e}")
                    
        # Also count any loose videos directly in the parent subdir
        try:
            loose_videos = [f for f in os.listdir(subdir_path) if os.path.isfile(os.path.join(subdir_path, f)) and f.lower().endswith(EXTENSIONS)]
            subdir_total_videos += len(loose_videos)
        except Exception:
            pass
            
        match = re.search(r'\s*\[(\d+)\]$', subdir)
        if match:
            current_count = int(match.group(1))
            if current_count == subdir_total_videos:
                continue
            base_name = subdir[:match.start()].strip()
        else:
            base_name = subdir.strip()
            
        new_subdir_name = f"{base_name} [{subdir_total_videos}]"
        new_subdir_path = os.path.join(source_dir, new_subdir_name)
        
        if subdir != new_subdir_name:
            try:
                os.rename(subdir_path, new_subdir_path)
                print(f"  [RENAME] '{subdir}' -> '{new_subdir_name}'")
                renamed_count += 1
            except Exception as e:
                print(f"  [ERROR] Failed to rename '{subdir}': {e}")
                    
    return renamed_count

def get_video_codec(file_path):
    """Uses ffprobe to extract the video codec name."""
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', 
        '-show_entries', 'stream=codec_name', '-of', 'json', file_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return data['streams'][0]['codec_name'] if data.get('streams') else 'no_video_stream'
    except Exception:
        return 'error_reading_file'

def report_codecs(source_dir):
    """Scans the directory and groups files by codec."""
    results = defaultdict(list)
    h264_count = 0
    non_h264_count = 0
    print(f"\n--- Phase 3: Codec Scanning ({source_dir}) ---")
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(EXTENSIONS):
                full_path = os.path.join(root, file)
                codec = get_video_codec(full_path)
                results[codec].append(full_path)
                if codec == 'h264':
                    h264_count += 1
                else:
                    non_h264_count += 1

    print("\n--- Files Grouped by Codec (Non-H264) ---")
    other_codecs = sorted([c for c in results.keys() if c != 'h264'])
    for codec in other_codecs:
        print(f"\nCODEC: {codec.upper()}")
        for f in results[codec]:
            print(f"  - {f}")
    return h264_count, non_h264_count

def count_and_log_files(source_dir):
    """Counts all non-script files and logs the total."""
    print(f"\n--- Phase 4: File Counting ({source_dir}) ---")
    log_filename = "file_count_log.txt"
    log_path = os.path.join(source_dir, log_filename)
    total_files = 0

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if not file.endswith('.py') and file != log_filename:
                total_files += 1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] Total files: {total_files}\n"

    try:
        with open(log_path, "a") as f:
            f.write(log_entry)
        print(f"Successfully logged {total_files} files to {log_filename} at {timestamp}")
    except Exception as e:
        print(f"Error writing to log: {e}")
        
    return total_files

def main():
    if not os.path.exists(TESS_PATH):
        print("Tesseract path error."); input(); return

    print(f"{'='*80}\nCHESS TOURNAMENT SORTER (THICK-TEXT MODE)\n{'='*80}")

    try:
        sorted_count, skipped_count = process_directory(SOURCE_DIR)
        renamed_count = update_folder_video_counts(SOURCE_DIR)
        h264_count, non_h264_count = report_codecs(SOURCE_DIR)
        total_files = count_and_log_files(SOURCE_DIR)
        
        print(f"\n{'='*80}")
        print("FINAL REPORT")
        print(f"{'='*80}")
        print(f"Videos Sorted:  {sorted_count}")
        print(f"Videos Skipped: {skipped_count}")
        print(f"Folders Renamed: {renamed_count}")
        print(f"H264 Videos Scanned: {h264_count}")
        print(f"Non-H264 Videos Scanned: {non_h264_count}")
        print(f"Total Files in Directory: {total_files}")
        print(f"{'='*80}")
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")

    # Pauses at the end as requested
    input("\nTask complete. Press Enter to exit...")

if __name__ == "__main__":
    main()
