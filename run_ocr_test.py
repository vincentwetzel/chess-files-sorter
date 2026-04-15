import os
import unittest

from ocr import analyze_image

class TestOCRSuite(unittest.TestCase):
    def test_all_assets(self):
        assets_dir = 'tests/assets'
        if not os.path.exists(assets_dir):
            self.skipTest(f"Assets directory '{assets_dir}' not found.")

        failures = []
        
        for img_name in os.listdir(assets_dir):
            if not img_name.endswith('.png'): continue
            img_path = os.path.join(assets_dir, img_name)

            expected = os.path.splitext(img_name)[0]
            result = analyze_image(img_path)
            
            if result == expected:
                print(f"PASSED: {img_name}")
            else:
                msg = f"FAILED: {img_name} - Expected: '{expected}', Got: '{result}'"
                print(msg)
                failures.append(msg)

        if failures:
            self.fail(f"OCR mismatches found ({len(failures)}):\n" + "\n".join(failures))

if __name__ == '__main__':
    print("Running Combined OCR Test Suite...\n")
    unittest.main(verbosity=0)
