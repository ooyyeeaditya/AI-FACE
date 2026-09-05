import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

font_path = '/System/Library/Fonts/Menlo.ttc'
font = ImageFont.truetype(font_path, 52)
CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"

def make_centered_glyph(c):
    im = Image.new("L", (58, 80), 0)
    d = ImageDraw.Draw(im)
    bbox = font.getbbox(c)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    ox = (58 - bw) // 2 - bbox[0]
    oy = (80 - bh) // 2 - bbox[1]
    d.text((ox, oy), c, font=font, fill=255)
    return np.asarray(im, dtype=np.float32) / 255.0

GLYPHS = {c: make_centered_glyph(c) for c in CHARS}

l1_bin = cv2.imread('/Users/aaryamanrana/Documents/Facesih /scratch/l1_bin.png', cv2.IMREAD_GRAYSCALE)
l2_bin = cv2.imread('/Users/aaryamanrana/Documents/Facesih /scratch/l2_bin.png', cv2.IMREAD_GRAYSCALE)

def decode_centered(bin_img):
    h, w = bin_img.shape
    char_w = w / 44.0
    chars = []
    for i in range(44):
        cx0 = int(i * char_w)
        cx1 = int((i + 1) * char_w)
        patch = bin_img[:, cx0:cx1]
        
        # Center patch
        pts = np.where(patch > 50)
        if len(pts[0]) < 10:
            chars.append("<")
            continue
            
        py0, py1 = pts[0].min(), pts[0].max()
        px0, px1 = pts[1].min(), pts[1].max()
        c_crop = patch[py0:py1+1, px0:px1+1]
        
        c_im = Image.fromarray(c_crop)
        im_canvas = Image.new("L", (58, 80), 0)
        cw, ch = c_im.size
        # Resize preserving aspect ratio
        scale = min(46.0 / max(1, cw), 65.0 / max(1, ch))
        c_res = c_im.resize((max(1, int(cw * scale)), max(1, int(ch * scale))), Image.BILINEAR)
        rw, rh = c_res.size
        im_canvas.paste(c_res, ((58 - rw) // 2, (80 - rh) // 2))
        
        arr = np.asarray(im_canvas, dtype=np.float32) / 255.0
        
        best_c = "<"
        best_score = -1.0
        for c, g in GLYPHS.items():
            score = float(np.sum(arr * g) / (np.linalg.norm(arr) * np.linalg.norm(g) + 1e-6))
            if score > best_score:
                best_score = score
                best_c = c
        chars.append(best_c)
    return "".join(chars)

print("Decoded L1:", decode_centered(l1_bin))
print("Decoded L2:", decode_centered(l2_bin))
