import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
import cv2
import numpy as np
from PIL import Image

doc_p = '/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_7a940e47_Screenshot_2026-09-04_at_6.47.01_PM.png'
img = Image.open(doc_p)
w, h = img.size

# Let's inspect the bottom 25% where MRZ is located
mrz_crop = img.crop((0, int(h * 0.75), w, h)).convert("L")
mrz_crop.save('/Users/aaryamanrana/Documents/Facesih /scratch/mrz_crop.png')
print("MRZ crop size:", mrz_crop.size)

# Try pytesseract if available
try:
    import pytesseract
    txt = pytesseract.image_to_string(mrz_crop, config="--psm 6")
    print("Pytesseract raw:", repr(txt))
except Exception as e:
    print("Pytesseract error:", e)
