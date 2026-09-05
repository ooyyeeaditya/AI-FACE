from pathlib import Path

p = Path("/Users/aaryamanrana/Documents/Facesih /run_pipeline.py")
content = p.read_text()

content = content.replace(
    '''    # 2. Module 2: Rule, Date, Syntax & Cross-Field Validation
    rule_res = validate_document_rules(
        doc_type=ocr_res.doc_type,
        doc_number=doc_num,
        dob=dob,
        issue_date=issue_date,
        expiry_date=expiry_date,
        country_code=country_code,
        nationality=nationality,
        gender=gender,
        stay_duration_days=stay_days,
    )''',
    '''    # 2. Module 2: Rule, Date, Syntax, Placeholder & Cross-Field Validation
    raw_dob = ocr_res.get_field("raw_dob_str") or ocr_res.get_field("dob_str")
    rule_res = validate_document_rules(
        doc_type=ocr_res.doc_type,
        doc_number=doc_num,
        dob=dob,
        issue_date=issue_date,
        expiry_date=expiry_date,
        country_code=country_code,
        nationality=nationality,
        gender=gender,
        stay_duration_days=stay_days,
        holder_name=holder_name,
        raw_dob_str=raw_dob,
    )'''
)

p.write_text(content)
print("Updated run_pipeline.py successfully!")
