import cv2
import numpy as np
from PIL import Image

def compute_face_similarity(crop1: Image.Image, crop2: Image.Image) -> float:
    img1 = cv2.cvtColor(np.asarray(crop1.convert("RGB").resize((120, 150))), cv2.COLOR_RGB2BGR)
    img2 = cv2.cvtColor(np.asarray(crop2.convert("RGB").resize((120, 150))), cv2.COLOR_RGB2BGR)
    
    # 1. Color Histogram Correlation (HSV space)
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
    
    hist1 = cv2.calcHist([hsv1], [0, 1], None, [30, 32], [0, 180, 0, 256])
    hist2 = cv2.calcHist([hsv2], [0, 1], None, [30, 32], [0, 180, 0, 256])
    cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    
    hist_sim = float(cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL))
    
    # 2. Structural Grayscale Correlation
    g1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    g1_norm = (g1.astype(np.float32) - g1.mean()) / (g1.std() + 1e-4)
    g2_norm = (g2.astype(np.float32) - g2.mean()) / (g2.std() + 1e-4)
    struct_sim = float(np.mean(g1_norm * g2_norm))
    
    # Combined similarity in [0, 1]
    combined = 0.5 * max(0.0, hist_sim) + 0.5 * max(0.0, struct_sim)
    return round(combined, 3)

import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
from generators.specimen_generator import generate_passport_specimen, generate_traveler_live_photo
from core.face.face_engine import detect_face_region

doc_img, _ = generate_passport_specimen(seed=123)
live_match = generate_traveler_live_photo(seed=123, is_match=True)
live_mismatch = generate_traveler_live_photo(seed=123, is_match=False)

_, c_doc = detect_face_region(doc_img, is_document=True)
_, c_match = detect_face_region(live_match, is_document=False)
_, c_mismatch = detect_face_region(live_mismatch, is_document=False)

u_doc = Image.open('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_c121b4d7_Screenshot_2026-09-02_at_4.44.33_PM.png')
u_live = Image.open('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_live_28e816f6_webcam_snap.jpg')
_, c_udoc = detect_face_region(u_doc, is_document=True, doc_type='aadhaar')
_, c_ulive = detect_face_region(u_live, is_document=False)

print("Synthetic Match Sim:", compute_face_similarity(c_doc, c_match))
print("Synthetic Mismatch Sim:", compute_face_similarity(c_doc, c_mismatch))
print("User Real Aadhaar vs Webcam:", compute_face_similarity(c_udoc, c_ulive))
