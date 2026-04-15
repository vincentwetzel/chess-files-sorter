import os
import argparse
from config import TESS_PATH, SOURCE_DIR, TO_SORT_DIR
from database import CodecDatabase
from file_sorting import process_directory, process_staging_directory
from file_reporting import update_folder_video_counts, report_codecs, count_and_log_files

def main(no_pause=False):
    if not os.path.exists(TESS_PATH):
        print("Tesseract path error."); input(); return

    print(f"{'='*80}\nCHESS TOURNAMENT SORTER (THICK-TEXT MODE)\n{'='*80}")

    # Initialize codec database
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'codec_cache.db')
    codec_db = CodecDatabase(db_path)

    try:
        staged_sorted, staged_skipped = process_staging_directory(TO_SORT_DIR, SOURCE_DIR)
        sorted_count, skipped_count = process_directory(SOURCE_DIR)
        
        sorted_count += staged_sorted
        skipped_count += staged_skipped
        
        renamed_count = update_folder_video_counts(SOURCE_DIR)
        h264_count, non_h264_count = report_codecs(SOURCE_DIR, codec_db)
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
    finally:
        codec_db.close()

    if not no_pause:
        input("\nTask complete. Press Enter to exit...")
    else:
        print("\nTask complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chess Tournament Sorter")
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="Skip the final pause/input prompt"
    )
    args = parser.parse_args()
    main(no_pause=args.no_pause)
