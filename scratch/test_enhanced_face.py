import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
import numpy as np
import cv2
from PIL import Image
from generators.specimen_generator import generate_passport_specimen, generate_traveler_live_photo

def extract_advanced_face_features(face_crop: Image.Image) -> np.ndarray:
    resized = face_crop.convert("RGB").resize((64, 64), Image.BILINEAR)
    gray = cv2.cvtColor(np.asarray(resized), cv2.COLOR_RGB2GRAY)
    arr = np.asarray(resized, dtype=np.float32) / 255.0
    
    features = []
    
    # 1. 4x4 spatial zone color moments
    cell = 16
    for i in range(4):
        for j in range(4):
            block = arr[i * cell:(i + 1) * cell, j * cell:(j + 1) * cell]
            for c in range(3):
                features.append(float(block[:, :, c].mean()))
                features.append(float(block[:, :, c].std()))
                
    # 2. Local Binary Patterns (LBP) texture
    lbp = np.zeros_like(gray)
    for i in range(1, 63):
        for j in range(1, 63):
            center = gray[i, j]
            code = 0
            code |= (gray[i-1, j-1] >= center) << 7
            code |= (gray[i-1, j] >= center) << 6
            code |= (gray[i-1, j+1] >= center) << 5
            code |= (gray[i, j+1] >= center) << 4
            code |= (gray[i+1, j+1] >= center) << 3
            code |= (gray[i+1, j] >= center) << 2
            code |= (gray[i+1, j-1] >= center) << 1
            code |= (gray[i, j-1] >= center) << 0
            lbp[i, j] = code
            
    # Histogram of LBP across 4 quadrants
    for qi in [0, 32]:
        for qj in [0, 32]:
            q_lbp = lbp[qi:qi+32, qj:qj+32]
            h, _ = np.histogram(q_lbp, bins=32, range=(0, 256))
            features.extend((h / (np.linalg.norm(h) + 1e-6)).tolist())
            
    # 3. Spatial Gradients (Sobel)
    sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(sobelx, sobely)
    mag_norm = cv2.normalize(mag, None, 0, 1, cv2.NORM_MINMAX)
    features.extend(cv2.resize(mag_norm, (8, 8)).flatten().tolist())
    
    vec = np.array(features, dtype=np.float32)
    return vec / (np.linalg.norm(vec) + 1e-6)

doc_img, _ = generate_passport_specimen(seed=101)
live_match = generate_traveler_live_photo(seed=101, is_match=True)
live_impostor = generate_traveler_live_photo(seed=101, is_match=False)

f_doc = extract_advanced_face_features(doc_img.crop((int(doc_img.size[0]*0.78), int(doc_img.size[1]*0.12), int(doc_img.size[0]*0.96), int(doc_img.size[1]*0.42))))
f_match = extract_advanced_face_features(live_match.crop((int(live_match.size[0]*0.15), int(live_match.size[1]*0.10), int(live_match.size[0]*0.85), int(live_match.size[1]*0.90))))
f_impostor = extract_advanced_face_features(live_impostor.crop((int(live_impostor.size[0]*0.15), int(live_impostor.size[1]*0.10), int(live_impostor.size[0]*0.85), int(live_impostor.size[1]*0.90))))

sim_match = float(np.dot(f_doc, f_match))
sim_impostor = float(np.dot(f_doc, f_impostor))

print(f"Genuine match similarity: {sim_match:.3f}")
print(f"Impostor similarity: {sim_impostor:.3f}")

# User's Aadhaar vs webcam
user_doc = Image.open('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_c121b4d7_Screenshot_2026-09-02_at_4.44.33_PM.png')
user_live = Image.open('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_live_28e816f6_webcam_snap.jpg')

f_user_doc = extract_advanced_face_features(user_doc.crop((27, 78, 138, 234)))
f_user_live = extract_advanced_face_features(user_live.crop((96, 48, 544, 432)))
sim_user = float(np.dot(f_user_doc, f_user_live))
print(f"User real Aadhaar vs Webcam similarity: {sim_user:.3f}")
