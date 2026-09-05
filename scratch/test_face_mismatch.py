import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
from PIL import Image, ImageDraw
import numpy as np
from core.face.face_engine import compare_face_biometrics, _extract_face_feature_vector
from generators.specimen_generator import generate_passport_specimen, generate_traveler_live_photo

doc_img, _ = generate_passport_specimen(seed=123)
live_match = generate_traveler_live_photo(seed=123, is_match=True)

# Generate distinct mismatch
img_mismatch = Image.new("RGB", (320, 400), (40, 45, 55))
d = ImageDraw.Draw(img_mismatch)
# Dark skin, blonde hair, orange jacket
cx = 160
d.ellipse([cx - 140, 240, cx + 140, 520], fill=(220, 100, 20))
d.rectangle([cx - 30, 220, cx + 30, 280], fill=(110, 70, 45))
d.ellipse([cx - 80, 50, cx + 80, 240], fill=(110, 70, 45))
d.arc([cx - 85, 35, cx + 85, 220], 180, 360, fill=(240, 210, 60), width=32)
d.ellipse([cx - 45, 130, cx - 20, 155], fill=(10, 10, 10))
d.ellipse([cx + 20, 130, cx + 45, 155], fill=(10, 10, 10))
d.line([(cx - 30, 190), (cx + 30, 190)], fill=(120, 30, 30), width=4)

res_match = compare_face_biometrics(doc_img, live_match, similarity_threshold=0.82)
res_mismatch = compare_face_biometrics(doc_img, img_mismatch, similarity_threshold=0.82)

print("Match Score:", res_match.similarity_score, "Matched:", res_match.matched)
print("Mismatch Score:", res_mismatch.similarity_score, "Matched:", res_mismatch.matched)
