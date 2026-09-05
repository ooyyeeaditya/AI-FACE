import re
from datetime import date

raw_text = """
, Aditya Chauhan
& sea fat / DOB : 31/01/2004
— Tey / Male

6432 2708 7263

05/11/2016

| : — ‘oneal : 31/01/2004 ;
Jer / Male

g ek

: 6432 2708 7263 “
"""

lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
full_text = " ".join(lines).upper()

# Aadhaar Number
aadhaar_m = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", raw_text)
uid = aadhaar_m.group(1).replace(" ", "") if aadhaar_m else ""

# Name Extraction
EXCLUDE_WORDS = {
    "GOVERNMENT", "INDIA", "BHARAT", "AADHAAR", "ADHAAR", "UIDAI", "UNIQUE", "IDENTIFICATION",
    "AUTHORITY", "MALE", "FEMALE", "TRANSGENDER", "DOB", "DATE", "BIRTH", "GENDER", "YEAR",
    "YOB", "ENROLMENT", "HELP", "WWW", "UIDAI.GOV.IN", "FATHER", "HUSBAND", "WIFE", "SON",
    "DAUGHTER", "CARE", "OF", "ADDRESS", "PIN", "DOWNLOAD", "ISSUE", "SEA", "FAT", "TEY", "JER", "ONEAL"
}

extracted_name = None

# Strategy 1: Find the line with DOB and inspect preceding lines
dob_line_idx = -1
for i, line in enumerate(lines):
    if re.search(r"\bDOB\b|BIRTH|जन्म|YEAR\s*OF\s*BIRTH|\d{1,2}/\d{1,2}/\d{4}", line, re.IGNORECASE):
        dob_line_idx = i
        break

if dob_line_idx > 0:
    for i in range(dob_line_idx - 1, -1, -1):
        line = lines[i]
        # Clean leading/trailing punctuation
        clean = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z\s]+$", "", line).strip()
        words = clean.split()
        if 1 <= len(words) <= 4:
            # Check if all words are valid names (not in exclusion list)
            if all(len(w) >= 2 and w.upper() not in EXCLUDE_WORDS for w in words):
                extracted_name = clean.upper()
                break

if not extracted_name:
    # Strategy 2: Look for 'Name / नाम' label
    for i, line in enumerate(lines):
        if re.search(r"(?:NAME|नाम)[:\s/]+", line, re.IGNORECASE):
            name_val = re.sub(r"(?i)(?:NAME|नाम)[:\s/]+", "", line).strip()
            clean = re.sub(r"[^a-zA-Z\s]", "", name_val).strip()
            if clean and len(clean.split()) <= 4:
                extracted_name = clean.upper()
                break

if not extracted_name:
    # Strategy 3: General scan
    for line in lines:
        clean = re.sub(r"^[^a-zA-Z]+|[^a-zA-Z\s]+$", "", line).strip()
        words = clean.split()
        if 2 <= len(words) <= 4:
            if all(len(w) >= 2 and w.upper() not in EXCLUDE_WORDS for w in words):
                extracted_name = clean.upper()
                break

print("Extracted UID :", uid)
print("Extracted Name:", extracted_name)
