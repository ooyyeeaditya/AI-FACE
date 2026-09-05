import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
from PIL import Image, ImageDraw
import numpy as np
from core.face.face_engine import compare_face_biometrics
from generators.specimen_generator import generate_passport_specimen

def draw_portrait(size=(320, 400), skin_tone=(215, 175, 140), hair_color=(40, 30, 25), shirt_color=(50, 70, 100), bg_color=(230, 235, 240)):
    img = Image.new("RGB", size, bg_color)
    d = ImageDraw.Draw(img)
    cx = size[0] // 2
    d.ellipse([cx - int(size[0]*0.45), int(size[1]*0.6), cx + int(size[0]*0.45), int(size[1]*1.3)], fill=shirt_color)
    d.rectangle([cx - int(size[0]*0.1), int(size[1]*0.55), cx + int(size[0]*0.1), int(size[1]*0.7)], fill=skin_tone)
    d.ellipse([cx - int(size[0]*0.25), int(size[1]*0.12), cx + int(size[0]*0.25), int(size[1]*0.6)], fill=skin_tone)
    d.arc([cx - int(size[0]*0.27), int(size[1]*0.08), cx + int(size[0]*0.27), int(size[1]*0.55)], 180, 360, fill=hair_color, width=int(size[1]*0.08))
    eye_y = int(size[1] * 0.32)
    d.ellipse([cx - int(size[0]*0.14), eye_y, cx - int(size[0]*0.06), eye_y + 8], fill=(30, 30, 30))
    d.ellipse([cx + int(size[0]*0.06), eye_y, cx + int(size[0]*0.14), eye_y + 8], fill=(30, 30, 30))
    mouth_y = int(size[1] * 0.48)
    d.line([(cx - int(size[0]*0.1), mouth_y), (cx + int(size[0]*0.1), mouth_y)], fill=(160, 70, 70), width=3)
    return img

doc_img, _ = generate_passport_specimen(seed=123)
match_img = draw_portrait(size=(320, 400), skin_tone=(215, 175, 140), hair_color=(40, 30, 25), shirt_color=(40, 60, 95), bg_color=(230, 235, 240))
mismatch_img = draw_portrait(size=(320, 400), skin_tone=(100, 60, 40), hair_color=(240, 210, 60), shirt_color=(220, 80, 20), bg_color=(70, 80, 95))

res_match = compare_face_biometrics(doc_img, match_img, similarity_threshold=0.82)
res_mismatch = compare_face_biometrics(doc_img, mismatch_img, similarity_threshold=0.82)

print("Match Score:", res_match.similarity_score, "Matched:", res_match.matched)
print("Mismatch Score:", res_mismatch.similarity_score, "Matched:", res_mismatch.matched)
