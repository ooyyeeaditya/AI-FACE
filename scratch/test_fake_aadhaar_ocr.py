import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import re

doc_path = '/Users/aaryamanrana/.gemini/antigravity/brain/9e2edf8e-ec35-43e9-b768-88c30dac82e9/.user_uploaded/media_1788542056286.png'
img = Image.open(doc_path)
w, h = img.size
arr = cv2.imread(doc_path, cv2.IMREAD_GRAYSCALE)

# 1. Number strip at bottom: y: 0.68*h to 0.83*h
num_patch = arr[int(h * 0.68):int(h * 0.84), int(w * 0.20):int(w * 0.85)]
cv2.imwrite('/Users/aaryamanrana/Documents/Facesih /scratch/aadhaar_num_patch.png', num_patch)

# Upscale and threshold
num_up = cv2.resize(num_patch, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_LANCZOS4)
_, num_bin = cv2.threshold(num_up, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
cv2.imwrite('/Users/aaryamanrana/Documents/Facesih /scratch/aadhaar_num_bin.png', num_bin)

# Let's decode digits using digit template matcher
font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 48)
DIGITS = "0123456789"
DIGIT_TEMPLATES = {}
for d in DIGITS:
    im = Image.new("L", (36, 52), 0)
    dr = ImageDraw.Draw(im)
    bbox = font.getbbox(d)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    dr.text(((36 - bw)//2 - bbox[0], (52 - bh)//2 - bbox[1]), d, font=font, fill=255)
    DIGIT_TEMPLATES[d] = np.asarray(im, dtype=np.float32) / 255.0

# Find digit contours
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
morph = cv2.morphologyEx(num_bin, cv2.MORPH_CLOSE, kernel)
contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

digit_boxes = []
for c in contours:
    x, y, bw, bh = cv2.boundingRect(c)
    if 15 < bh < (num_up.shape[0] * 0.95) and 8 < bw < (num_up.shape[1] * 0.25):
        digit_boxes.append((x, y, bw, bh))

digit_boxes.sort(key=lambda b: b[0])
print(f"Found {len(digit_boxes)} digit bounding boxes in Aadhaar number strip")

extracted_digits = []
for (bx, by, bw, bh) in digit_boxes:
    patch = num_bin[by:by+bh, bx:bx+bw]
    p_resized = cv2.resize(patch, (36, 52), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    best_d = "?"
    best_score = -1.0
    for d, t in DIGIT_TEMPLATES.items():
        score = float(np.sum(p_resized * t) / (np.linalg.norm(p_resized) * np.linalg.norm(t) + 1e-6))
        if score > best_score:
            best_score = score
            best_d = d
    extracted_digits.append(best_d)

print("Decoded Aadhaar Digits:", "".join(extracted_digits))
