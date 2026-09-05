import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
from PIL import Image
import cv2
import numpy as np
from core.face.face_engine import compare_face_biometrics, detect_face_region

doc_p = '/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_7a940e47_Screenshot_2026-09-04_at_6.47.01_PM.png'
live_p = '/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_live_1439ccc9_IMG_0445.jpeg'

img_doc = Image.open(doc_p)
img_live = Image.open(live_p)
dw, dh = img_doc.size

# Main portrait on Indian Passport is on the LEFT (x: 0.05*w to 0.38*w, y: 0.20*h to 0.72*h)
left_box = (int(dw * 0.05), int(dh * 0.20), int(dw * 0.35), int(dh * 0.72))
doc_portrait = img_doc.crop(left_box)
doc_portrait.save('/Users/aaryamanrana/Documents/Facesih /scratch/aaryaman_passport_portrait.jpg')

# Compare with live photo IMG_0445.jpeg
from core.face.face_engine import _extract_face_feature_vector

_, live_crop = detect_face_region(img_live, is_document=False)
live_crop.save('/Users/aaryamanrana/Documents/Facesih /scratch/aaryaman_live_crop.jpg')

feat_doc = _extract_face_feature_vector(doc_portrait)
feat_live = _extract_face_feature_vector(live_crop)

sim = float(np.dot(feat_doc, feat_live))
print("Biometric Similarity between Left Passport Portrait & IMG_0445.jpeg:", sim)
