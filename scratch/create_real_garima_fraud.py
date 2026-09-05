import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from datetime import date
from pathlib import Path

out_dir = Path('/Users/aaryamanrana/Documents/Facesih /output')
garima_img = Image.open(out_dir / 'real_indian_passport_garima.jpg').convert('RGB')
w, h = garima_img.size

# 1. Tampered DOB version (Patch DOB text from 01/07/1994 to 01/07/1986)
dob_img = garima_img.copy()
draw = ImageDraw.Draw(dob_img)
# Draw patch over DOB area (approx y: 0.40 - 0.46, x: 0.38 - 0.55)
px0, py0, px1, py1 = int(w * 0.38), int(h * 0.40), int(w * 0.52), int(h * 0.46)
draw.rectangle((px0, py0, px1, py1), fill=(245, 245, 248))
draw.text((px0 + 2, py0 + 1), "01/07/1986", fill=(10, 10, 20))
dob_img.save(out_dir / 'real_passport_garima_dob_tampered.jpg')

# 2. Photo spliced version
splice_img = garima_img.copy()
# Draw a cut-line border around photo
fx0, fy0, fx1, fy1 = int(w * 0.05), int(h * 0.25), int(w * 0.32), int(h * 0.65)
s_draw = ImageDraw.Draw(splice_img)
s_draw.rectangle((fx0, fy0, fx1, fy1), outline=(40, 40, 40), width=2)
splice_img.save(out_dir / 'real_passport_garima_photo_spliced.jpg')

print("Created real Garima tampered specimens successfully!")
