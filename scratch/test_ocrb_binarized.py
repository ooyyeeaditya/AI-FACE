import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

arr = cv2.imread('/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_7a940e47_Screenshot_2026-09-04_at_6.47.01_PM.png', cv2.IMREAD_GRAYSCALE)

# Line 1: y: 1465 to 1565, x: 100 to 2640
# Line 2: y: 1595 to 1695, x: 100 to 2640
l1_img = arr[1465:1565, 100:2640]
l2_img = arr[1595:1695, 100:2640]

# Adaptive binarize
l1_bin = cv2.adaptiveThreshold(l1_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
l2_bin = cv2.adaptiveThreshold(l2_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)

cv2.imwrite('/Users/aaryamanrana/Documents/Facesih /scratch/l1_bin.png', l1_bin)
cv2.imwrite('/Users/aaryamanrana/Documents/Facesih /scratch/l2_bin.png', l2_bin)

# Let's inspect character density per column
proj1 = np.sum(l1_bin, axis=0)
proj2 = np.sum(l2_bin, axis=0)
print("Line 1 total width:", l1_img.shape[1], "Char width:", l1_img.shape[1] / 44.0)
print("Line 2 total width:", l2_img.shape[1], "Char width:", l2_img.shape[1] / 44.0)
