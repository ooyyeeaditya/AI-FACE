import cv2
import numpy as np
from PIL import Image

arr = cv2.imread('/Users/aaryamanrana/Documents/Facesih /scratch/mrz_crop.png', cv2.IMREAD_GRAYSCALE)
print("Crop shape:", arr.shape)

# Binarize with adaptive threshold / Otsu
# The text is dark on a light background
blur = cv2.GaussianBlur(arr, (5, 5), 0)
_, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Find horizontal projections
proj_y = np.sum(thresh, axis=1)
# Normalize projection
proj_y = proj_y / proj_y.max()

# Print peaks in proj_y
from scipy.signal import find_peaks
peaks, props = find_peaks(proj_y, height=0.2, distance=30)
print("Detected line peaks at y:", peaks)

# Crop the 2 lines
if len(peaks) >= 2:
    for i, p in enumerate(peaks[-2:]):
        y0 = max(0, p - 35)
        y1 = min(arr.shape[0], p + 35)
        line_img = arr[y0:y1, :]
        line_thresh = thresh[y0:y1, :]
        
        # Horizontal projection of this line to find left and right bounds
        proj_x = np.sum(line_thresh, axis=0)
        proj_x = proj_x / proj_x.max()
        valid_cols = np.where(proj_x > 0.15)[0]
        x0, x1 = valid_cols.min(), valid_cols.max()
        print(f"Line {i+1}: y=({y0}, {y1}), x=({x0}, {x1}), width={x1-x0}")
        
        # Save line crop
        cv2.imwrite(f'/Users/aaryamanrana/Documents/Facesih /scratch/line_{i+1}.png', arr[y0:y1, x0:x1])
