import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import re

CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"

def build_ocrb_templates():
    font = ImageFont.load_default()
    for f_path in ["/System/Library/Fonts/Courier.dfont", "/Library/Fonts/Courier New.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]:
        try:
            font = ImageFont.truetype(f_path, 32)
            break
        except Exception:
            pass
            
    templates = {}
    for c in CHARS:
        img = Image.new("L", (28, 40), 255)
        d = ImageDraw.Draw(img)
        d.text((4, 2), c, font=font, fill=0)
        arr = np.asarray(img, dtype=np.float32)
        arr = (arr - arr.mean()) / (arr.std() + 1e-4)
        templates[c] = arr
    return templates

TEMPLATES = build_ocrb_templates()

def decode_mrz_crop(mrz_crop: Image.Image) -> list:
    arr = np.asarray(mrz_crop.convert("L"), dtype=np.uint8)
    _, thresh = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    proj_y = np.sum(thresh, axis=1)
    line_bounds = []
    in_line = False
    start_y = 0
    
    thresh_val = np.mean(proj_y) * 0.3
    for y, val in enumerate(proj_y):
        if val > thresh_val and not in_line:
            in_line = True
            start_y = y
        elif val <= thresh_val and in_line:
            in_line = False
            if (y - start_y) >= 12:
                line_bounds.append((start_y, y))
                
    if in_line and (len(proj_y) - start_y) >= 12:
        line_bounds.append((start_y, len(proj_y)))
        
    print(f"Found {len(line_bounds)} lines")
    decoded_lines = []
    
    for (ly0, ly1) in line_bounds:
        line_img = thresh[ly0:ly1, :]
        proj_x = np.sum(line_img, axis=0)
        char_bounds = []
        in_char = False
        start_x = 0
        x_thresh = np.mean(proj_x) * 0.1
        
        for x, val in enumerate(proj_x):
            if val > x_thresh and not in_char:
                in_char = True
                start_x = x
            elif val <= x_thresh and in_char:
                in_char = False
                if (x - start_x) >= 4:
                    char_bounds.append((start_x, x))
                    
        line_chars = []
        for (cx0, cx1) in char_bounds:
            char_patch = arr[ly0:ly1, cx0:cx1]
            char_resized = cv2.resize(char_patch, (28, 40), interpolation=cv2.INTER_AREA).astype(np.float32)
            char_norm = (char_resized - char_resized.mean()) / (char_resized.std() + 1e-4)
            
            best_c = "<"
            best_score = -1.0
            for c, t_arr in TEMPLATES.items():
                score = float(np.dot(char_norm.flatten(), t_arr.flatten()) / (len(t_arr.flatten())))
                if score > best_score:
                    best_score = score
                    best_c = c
            line_chars.append(best_c)
            
        decoded_lines.append("".join(line_chars))
        
    return decoded_lines

img = Image.open("/Users/aaryamanrana/Documents/Facesih /output/specimen_indian_passport_genuine.png")
w, h = img.size
mrz_crop = img.crop((30, int(h * 0.78), w - 30, h - 30))
res = decode_mrz_crop(mrz_crop)
print("Decoded MRZ from image pixels:", res)
