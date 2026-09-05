import cv2
import numpy as np

arr = cv2.imread('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_7a940e47_Screenshot_2026-09-04_at_6.47.01_PM.png', cv2.IMREAD_GRAYSCALE)
h, w = arr.shape
print("Full Image Shape:", (h, w))

# The MRZ is in the bottom 25% of the passport:
bottom_y0 = int(h * 0.78)
mrz_strip = arr[bottom_y0:, :]

# Let's binarize
blur = cv2.GaussianBlur(mrz_strip, (3, 3), 0)
thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10)

# Save visualization of binarized MRZ strip
cv2.imwrite('/Users/aaryamanrana/Documents/Facesih /scratch/binarized_mrz.png', thresh)

# Morphological horizontal dilation to connect character clusters into 2 distinct lines
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (45, 3))
dilated = cv2.dilate(thresh, kernel, iterations=2)
cv2.imwrite('/Users/aaryamanrana/Documents/Facesih /scratch/dilated_mrz.png', dilated)

# Find contours of the 2 lines
contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
boxes = []
for c in contours:
    x, y, bw, bh = cv2.boundingRect(c)
    if bw > (w * 0.40) and bh > 15: # Valid long MRZ line
        boxes.append((x, y, bw, bh))

boxes.sort(key=lambda b: b[1]) # Sort top to bottom
print(f"Found {len(boxes)} MRZ line bounding boxes:")
for i, (bx, by, bw, bh) in enumerate(boxes):
    print(f"Line {i+1}: x={bx}, y={bottom_y0 + by}, w={bw}, h={bh}")
