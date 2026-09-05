import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
import numpy as np
import cv2
from PIL import Image
from generators.specimen_generator import generate_passport_specimen, generate_traveler_live_photo
from core.face.face_engine import _extract_face_feature_vector, detect_face_region

doc_img, _ = generate_passport_specimen(seed=123)
live_match = generate_traveler_live_photo(seed=123, is_match=True)
live_mismatch = generate_traveler_live_photo(seed=123, is_match=False)

_, c_doc = detect_face_region(doc_img, is_document=True)
_, c_match = detect_face_region(live_match, is_document=False)
_, c_mismatch = detect_face_region(live_mismatch, is_document=False)

# User's Aadhaar vs webcam
u_doc = Image.open('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_c121b4d7_Screenshot_2026-09-02_at_4.44.33_PM.png')
u_live = Image.open('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_live_28e816f6_webcam_snap.jpg')
_, c_udoc = detect_face_region(u_doc, is_document=True, doc_type='aadhaar')
_, c_ulive = detect_face_region(u_live, is_document=False)

def extract_rich_face_features(crop: Image.Image) -> np.ndarray:
    resized = crop.convert("RGB").resize((64, 64), Image.BILINEAR)
    arr = np.asarray(resized, dtype=np.float32) / 255.0
    gray = cv2.cvtColor(np.asarray(resized), cv2.COLOR_RGB2GRAY)
    
    feats = []
    # 4x4 spatial color moments (R, G, B mean and std)
    cell = 16
    for i in range(4):
        for j in range(4):
            block = arr[i*cell:(i+1)*cell, j*cell:(j+1)*cell]
            for ch in range(3):
                feats.append(float(block[:, :, ch].mean()))
                feats.append(float(block[:, :, ch].std()))
                
    # 8x8 normalized luminance grid (spatial structure)
    lum_small = cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    lum_norm = (lum_small - lum_small.mean()) / (lum_small.std() + 1e-4)
    feats.extend(lum_norm.flatten().tolist())
    
    # Gradient magnitude
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    mag_small = cv2.resize(mag, (8, 8), interpolation=cv2.INTER_AREA)
    mag_norm = (mag_small - mag_small.mean()) / (mag_small.std() + 1e-4)
    feats.extend(mag_norm.flatten().tolist())
    
    v = np.array(feats, dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-6)

f_doc = extract_rich_face_features(c_doc)
f_match = extract_rich_face_features(c_match)
f_mismatch = extract_rich_face_features(c_mismatch)
f_udoc = extract_rich_face_features(c_udoc)
f_ulive = extract_rich_face_features(c_ulive)

print("Match Cosine Sim:", float(np.dot(f_doc, f_match)))
print("Mismatch Cosine Sim:", float(np.dot(f_doc, f_mismatch)))
print("User Real Aadhaar vs Webcam:", float(np.dot(f_udoc, f_ulive)))
