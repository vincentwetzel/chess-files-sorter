import os
import shutil
import re
from config import EXTENSIONS
from ocr import sanitize_tournament_text, analyze_video

def move_video(file_path, subdir_path, tournament, matches, checks):
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

def process_staging_directory(staging_dir, dest_dir):
    if not os.path.exists(staging_dir):
        return 0, 0
        
    print("\n--- Phase 1a: Sorting Staging Directory ---")
    video_files = [f for f in os.listdir(staging_dir) if f.lower().endswith(EXTENSIONS) and os.path.isfile(os.path.join(staging_dir, f))]
    sorted_count, skipped_count = 0, 0
    
    for file in video_files:
        file_path = os.path.join(staging_dir, file)
        tournament, m, c = analyze_video(file_path)
        
        if tournament:
            # Extract YYYY-MM from filename brackets like [2026-04-15] or [04-15-2026]
            date_match = re.search(r'\[(\d{4})-(\d{2})-\d{2}\]', file)
            if date_match:
                year_month = f"{date_match.group(1)} - {date_match.group(2)}"
            else:
                date_match2 = re.search(r'\[(\d{2})-(\d{2})-(\d{4})\]', file)
                if date_match2:
                    year_month = f"{date_match2.group(3)} - {date_match2.group(1)}"
                else:
                    year_month = "Unknown Date"

            year_month_dir = None
            for d in os.listdir(dest_dir):
                d_path = os.path.join(dest_dir, d)
                if os.path.isdir(d_path) and d.startswith(year_month):
                    year_month_dir = d_path
                    break
                    
            if not year_month_dir:
                year_month_dir = os.path.join(dest_dir, year_month)
                os.makedirs(year_month_dir, exist_ok=True)
                
            move_video(file_path, year_month_dir, tournament, m, c)
            sorted_count += 1
        else:
            print(f"  [SKIP] {file} (Header incomplete)")
            skipped_count += 1
            
    return sorted_count, skipped_count

def process_directory(source_dir):
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