import re
from datetime import datetime, date

def parse_indian_passport_lines(raw_text):
    fields = {}
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    
    # 1. Document Number
    pass_m = re.search(r'\b([A-Z][0-9]{7})\b', raw_text.upper())
    if pass_m:
        fields['passport_number'] = pass_m.group(1)
        fields['document_number'] = pass_m.group(1)

    # 2. Line by line scanning
    for i, line in enumerate(lines):
        u = line.upper()
        # Given Name
        if re.search(r'GIVEN\s*NAME|दिया\s*गया\s*नाम', u, re.IGNORECASE):
            if i + 1 < len(lines):
                val = lines[i+1].strip()
                if not re.search(r'NATIONALITY|SURNAME|BIRTH|SEX|PLACE', val, re.IGNORECASE):
                    clean_val = re.sub(r'[^A-Z\s]', '', val.upper()).strip()
                    if clean_val and len(clean_val) >= 2:
                        fields['given_names'] = clean_val
        
        # Surname
        if re.search(r'SURNAME|उपनाम', u, re.IGNORECASE) and not re.search(r'GIVEN', u, re.IGNORECASE):
            if i + 1 < len(lines):
                val = lines[i+1].strip()
                if not re.search(r'GIVEN|NATIONALITY|BIRTH|SEX|PLACE', val, re.IGNORECASE):
                    clean_val = re.sub(r'[^A-Z\s]', '', val.upper()).strip()
                    if clean_val and len(clean_val) >= 2:
                        fields['surname'] = clean_val

        # Place of Birth
        if re.search(r'PLACE\s*OF\s*BIRTH|BIRTH\s*PLACE|जन्म\s*स्थान', u, re.IGNORECASE):
            if i + 1 < len(lines):
                val = lines[i+1].strip()
                clean_pob = re.sub(r'[^A-Z\s,]', '', val.upper()).strip()
                if clean_pob:
                    fields['place_of_birth'] = clean_pob

        # Place of Issue
        if re.search(r'PLACE\s*OF\s*ISSUE|जारी\s*करने|ISSUING', u, re.IGNORECASE):
            if i + 1 < len(lines):
                val = lines[i+1].strip()
                clean_poi = re.sub(r'[^A-Z\s,]', '', val.upper()).strip()
                clean_poi = clean_poi.replace('LUCKWOW', 'LUCKNOW')
                if clean_poi:
                    fields['place_of_issue'] = clean_poi

    # 3. Full Name
    if 'given_names' in fields and 'surname' in fields:
        fields['full_name'] = f"{fields['given_names']} {fields['surname']}"
    elif 'given_names' in fields:
        fields['full_name'] = fields['given_names']
    elif 'surname' in fields:
        fields['full_name'] = fields['surname']

    # 4. Nationality
    if re.search(r'INDIAN|REPUBLIC OF INDIA|IND\b|भारतीय', raw_text.upper()):
        fields['nationality'] = 'INDIAN'
        fields['country_code'] = 'IND'

    # 5. Sex / Gender
    if re.search(r'\bM\b|\bMALE\b|पुरुष', raw_text.upper()):
        fields['sex'] = 'M'
        fields['gender'] = 'MALE'
    elif re.search(r'\bF\b|\bFEMALE\b|महिला', raw_text.upper()):
        fields['sex'] = 'F'
        fields['gender'] = 'FEMALE'

    # 6. Dates
    dates = []
    for m in re.finditer(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})', raw_text):
        d, m_v, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dates.append(date(y, m_v, d))
        except Exception:
            pass
    
    dates = sorted(dates)
    if dates:
        fields['dob'] = dates[0]
        if len(dates) >= 2:
            fields['expiry_date'] = dates[-1]
        if len(dates) >= 3:
            fields['issue_date'] = dates[1]

    return fields

raw_sample = '''Or INDIA
erg / Type
P4954189
eaara / Surname
fea wen ara / Given Name(s)
RINKOO
eicdieran / Nationality re ' ) ot
widia / INDIAN M 01/01/1996
Siar eerra/ Place of Birth
FAIZABAD, UTTAR PRADESH
rh eA wr eer / Place of Issue 4. |
|  Luckwow
fetes /Date of issue
fer
12/10/2026
'''

res = parse_indian_passport_lines(raw_sample)
for k, v in res.items():
    print(f'  {k}: {v}')
