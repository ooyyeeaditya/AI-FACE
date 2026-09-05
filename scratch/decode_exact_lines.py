import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Build OCR-B standard templates
CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
def build_templates():
    for f in ['/System/Library/Fonts/Menlo.ttc', '/System/Library/Fonts/Courier.dfont', '/Library/Fonts/Courier New.ttf']:
        try:
            font = ImageFont.truetype(f, 40)
            break
        except Exception:
            font = ImageFont.load_default()
    templates = {}
    for c in CHARS:
        img = Image.new("L", (36, 54), 255)
        d = ImageDraw.Draw(img)
        d.text((4, 2), c, font=font, fill=0)
        arr = np.asarray(img, dtype=np.float32)
        arr = (arr - arr.mean()) / (arr.std() + 1e-4)
        templates[c] = arr
    return templates

TEMPLATES = build_templates()

arr = cv2.imread('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_7a940e47_Screenshot_2026-09-04_at_6.47.01_PM.png', cv2.IMREAD_GRAYSCALE)

# Crop Line 1 and Line 2
l1_patch = arr[1470:1570, 94:2660]
l2_patch = arr[1600:1700, 94:2660]

for name, line_img in [("Line 1", l1_patch), ("Line 2", l2_patch)]:
    h, w = line_img.shape
    char_w = w / 44.0
    
    # Preprocess line image
    line_norm = cv2.normalize(line_img, None, 0, 255, cv2.NORM_MINMAX)
    
    decoded = []
    for i in range(44):
        cx0 = int(i * char_w)
        cx1 = int((i + 1) * char_w)
        c_patch = line_norm[:, cx0:cx1]
        
        # Center crop character
        c_resized = cv2.resize(c_patch, (36, 54), interpolation=cv2.INTER_AREA).astype(np.float32)
        c_norm = (c_resized - c_resized.mean()) / (c_resized.std() + 1e-4)
        
        best_c = "<"
        best_score = -1.0
        for c, t_arr in TEMPLATES.items():
            score = float(np.dot(c_norm.flatten(), t_arr.flatten()) / len(t_arr.flatten()))
            if score > best_score:
                best_score = score
                best_c = c
        decoded.append(best_c)
    print(f"{name} Decoded: {''.join(decoded)}")
