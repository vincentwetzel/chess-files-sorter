import os
import re
import subprocess
import json
from datetime import datetime
from collections import defaultdict
from config import EXTENSIONS

def update_folder_video_counts(source_dir):
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

def report_codecs(source_dir, codec_db):
    codec_db.cleanup(source_dir)

    results = defaultdict(list)
    h264_count = 0
    non_h264_count = 0
    cache_hits = 0
    cache_misses = 0

    print(f"\n--- Phase 3: Codec Scanning ({source_dir}) ---")
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(EXTENSIONS):
                full_path = os.path.join(root, file)

                codec = codec_db.get(full_path)
                if codec is not None:
                    cache_hits += 1
                else:
                    cache_misses += 1
                    codec = get_video_codec(full_path)
                    codec_db.set(full_path, codec)

                results[codec].append(full_path)
                if codec == 'h264':
                    h264_count += 1
                else:
                    non_h264_count += 1

    print(f"  [CACHE] Hits: {cache_hits}, Misses: {cache_misses}")

    print("\n--- Files Grouped by Codec (Non-H264) ---")
    other_codecs = sorted([c for c in results.keys() if c != 'h264'])
    
    report_lines = []
    for codec in other_codecs:
        print(f"\nCODEC: {codec.upper()}")
        report_lines.append(f"CODEC: {codec.upper()}")
        for f in results[codec]:
            # Replace full-width characters to prevent Windows console line-wrap glitches
            display_f = f.replace('＂', '"').replace('｜', '|')
            print(f"  - {display_f}")
            report_lines.append(f"  - {f}")
            
    if other_codecs:
        report_path = os.path.join(source_dir, "non_h264_videos.txt")
        try:
            with open(report_path, "w", encoding="utf-8") as rf:
                rf.write("--- Files Grouped by Codec (Non-H264) ---\n\n")
                rf.write("\n".join(report_lines))
                rf.write("\n")
            print(f"\n  [INFO] Full list saved to {report_path}")
        except Exception as e:
            print(f"\n  [ERROR] Could not save report file: {e}")

    return h264_count, non_h264_count

def count_and_log_files(source_dir):
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