import cv2
import os
import pytesseract

TESS_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = TESS_PATH

from main import process_frame

assets_dir = 'tests/assets'
for img_name in os.listdir(assets_dir):
    if not img_name.endswith('.png'): continue
    img_path = os.path.join(assets_dir, img_name)
    frame = cv2.imread(img_path)

    if frame is not None:
        expected = os.path.splitext(img_name)[0]
        result = process_frame(frame)
        if result == expected:
            print(f"PASSED: {img_name}")
        else:
            print(f"FAILED: {img_name} - Expected: '{expected}', Got: '{result}'")

input("\nTest run complete. Press Enter to exit...")
