import configparser
import sys

# --- CONFIGURATION ---
config = configparser.ConfigParser()
if not config.read(['config.ini', 'settings.ini']):
    print("Error: config.ini or settings.ini file not found!")
    sys.exit(1)

try:
    TESS_PATH = config.get('Paths', 'TESS_PATH')
    SOURCE_DIR = config.get('Paths', 'SOURCE_DIR')
    TO_SORT_DIR = config.get('Paths', 'TO_SORT_DIR', fallback=r'J:\CHESS\_TO_SORT')
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    print(f"Error reading configuration: {e}")
    sys.exit(1)

EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm')
INTERVAL_SECONDS = 60
ROI_TOP_RATIO = 0.0
ROI_HEIGHT_RATIO = 0.14
ROI_WIDTH_RATIO = 0.28
LINE_ANCHOR_RATIO = 0.40