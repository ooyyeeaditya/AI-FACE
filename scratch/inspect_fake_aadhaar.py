import cv2
import numpy as np
from PIL import Image
import re

doc_path = '/Users/aaryamanrana/.gemini/antigravity/brain/9e2edf8e-ec35-43e9-b768-88c30dac82e9/.user_uploaded/media_1788542056286.png'
img = Image.open(doc_path)
w, h = img.size
arr = cv2.imread(doc_path)

# Let's check QR code
qr = cv2.QRCodeDetector()
val, pts, _ = qr.detectAndDecode(arr)
print("QR Code Content:", repr(val))

# Let's inspect the number zone at the bottom: (x: 0.15*w to 0.85*w, y: 0.65*h to 0.82*h)
num_crop = img.crop((int(w * 0.15), int(h * 0.65), int(w * 0.85), int(h * 0.82))).convert("L")
num_crop.save('/Users/aaryamanrana/Documents/Facesih /scratch/fake_aadhaar_num.png')

# Let's check the text fields zone: (x: 0.25*w to 0.70*w, y: 0.25*h to 0.65*h)
text_crop = img.crop((int(w * 0.25), int(h * 0.25), int(w * 0.70), int(h * 0.65))).convert("L")
text_crop.save('/Users/aaryamanrana/Documents/Facesih /scratch/fake_aadhaar_text.png')

print("Image size:", img.size)
