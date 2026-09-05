import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
import re

# Build OCR-B standard templates
CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"

def build_ocrb_templates():
    for f in ['/System/Library/Fonts/Menlo.ttc', '/System/Library/Fonts/Courier.dfont', '/Library/Fonts/Courier New.ttf']:
        try:
            font = ImageFont.truetype(f, 32)
            break
        except Exception:
            pass
    templates = {}
    for c in CHARS:
        img = Image.new("L", (28, 42), 255)
        d = ImageDraw.Draw(img)
        d.text((3, 2), c, font=font, fill=0)
        arr = np.asarray(img, dtype=np.float32)
        arr = (arr - arr.mean()) / (arr.std() + 1e-4)
        templates[c] = arr
    return templates

TEMPLATES = build_ocrb_templates()

def universal_decode_mrz(img: Image.Image) -> list:
    w, h = img.size
    # Super-resolution upscale if image is small
    target_w = 1200
    if w < target_w:
        scale = target_w / float(w)
        img_up = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    else:
        img_up = img
        
    uw, uh = img_up.size
    # Bottom 32%
    crop = img_up.crop((0, int(uh * 0.68), uw, uh)).convert("L")
    arr = np.asarray(crop, dtype=np.uint8)
    
    # Adaptive threshold & Otsu
    norm = cv2.normalize(arr, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    _, otsu = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Horizontal projection
    proj_y = np.sum(otsu, axis=1)
    mean_y = np.mean(proj_y)
    labeled, num_lines = ndimage.label(proj_y > mean_y * 0.8)
    
    line_strips = []
    for idx in range(1, num_lines + 1):
        rows = np.where(labeled == idx)[0]
        if len(rows) >= 8:
            line_strips.append((rows.min(), rows.max()))
            
    # Sort from top to bottom
    line_strips.sort(key=lambda item: item[0])
    print(f"Detected {len(line_strips)} line strips in MRZ zone")
    
    lines = []
    # If 2 lines found (TD3/TD2)
    for (y0, y1) in line_strips[-2:]:
        # Pad line bounds
        pad_y = max(2, int((y1 - y0) * 0.15))
        ly0 = max(0, y0 - pad_y)
        ly1 = min(arr.shape[0], y1 + pad_y)
        line_patch = arr[ly0:ly1, :]
        line_bin = otsu[ly0:ly1, :]
        
        proj_x = np.sum(line_bin, axis=0)
        cols = np.where(proj_x > (line_bin.shape[0] * 255 * 0.05))[0]
        if len(cols) == 0:
            continue
        x0, x1 = cols.min(), cols.max()
        line_w = x1 - x0
        num_chars = 44  # TD3
        char_w = line_w / float(num_chars)
        
        chars = []
        for i in range(num_chars):
            cx0 = int(x0 + i * char_w)
            cx1 = int(x0 + (i + 1) * char_w)
            c_patch = line_patch[:, max(0, cx0):min(line_patch.shape[1], cx1)]
            if c_patch.size == 0 or c_patch.shape[0] < 4 or c_patch.shape[1] < 2:
                chars.append("<")
                continue
            c_resized = cv2.resize(c_patch, (28, 42), interpolation=cv2.INTER_AREA).astype(np.float32)
            c_norm = (c_resized - c_resized.mean()) / (c_resized.std() + 1e-4)
            
            best_c = "<"
            best_score = -1.0
            for c, t_arr in TEMPLATES.items():
                score = float(np.dot(c_norm.flatten(), t_arr.flatten()) / len(t_arr.flatten()))
                if score > best_score:
                    best_score = score
                    best_c = c
            chars.append(best_c)
        lines.append("".join(chars))
    return lines

# Test on Pass1.jpg
img1 = Image.open('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_b97ab383_Pass1.jpg')
res1 = universal_decode_mrz(img1)
print("Decoded Pass1.jpg lines:", res1)
