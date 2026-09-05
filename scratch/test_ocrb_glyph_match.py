import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Render standard monospace glyphs
font_path = '/System/Library/Fonts/Menlo.ttc'
font = ImageFont.truetype(font_path, 60)

CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
GLYPHS = {}
for c in CHARS:
    im = Image.new("L", (58, 80), 0)
    d = ImageDraw.Draw(im)
    d.text((12, 5), c, font=font, fill=255)
    GLYPHS[c] = np.asarray(im, dtype=np.float32) / 255.0

l1_bin = cv2.imread('/Users/aaryamanrana/Documents/Facesih /scratch/l1_bin.png', cv2.IMREAD_GRAYSCALE)
l2_bin = cv2.imread('/Users/aaryamanrana/Documents/Facesih /scratch/l2_bin.png', cv2.IMREAD_GRAYSCALE)

def decode_line_binary(bin_img):
    h, w = bin_img.shape
    char_w = w / 44.0
    chars = []
    for i in range(44):
        cx0 = int(i * char_w)
        cx1 = int((i + 1) * char_w)
        patch = bin_img[:, cx0:cx1]
        p_resized = cv2.resize(patch, (58, 80), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        
        best_c = "<"
        best_score = -1.0
        for c, g in GLYPHS.items():
            # Normalized cross correlation
            score = float(np.sum(p_resized * g) / (np.linalg.norm(p_resized) * np.linalg.norm(g) + 1e-6))
            if score > best_score:
                best_score = score
                best_c = c
        chars.append(best_c)
    return "".join(chars)

print("Decoded Line 1:", decode_line_binary(l1_bin))
print("Decoded Line 2:", decode_line_binary(l2_bin))
