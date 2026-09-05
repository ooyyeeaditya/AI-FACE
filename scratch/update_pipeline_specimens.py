import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')

from run_pipeline import screen_document_pipeline, OUT_DIR
from datetime import date

# Test screening Garima's real passport
report = screen_document_pipeline(
    OUT_DIR / "real_indian_passport_garima.jpg",
    OUT_DIR / "real_live_photo_garima.jpg",
    doc_type_hint="passport"
)

print("Screening Result for Real Garima Passport:")
print("Risk Score:", report.risk_score, "Verdict:", report.verdict)
print("Decision:", report.decision_text)
print("MRZ:", report.ocr_result.mrz_lines if report.ocr_result else None)
print("VIZ Fields:", report.ocr_result.viz_fields if report.ocr_result else None)
print("Database Match:", report.database_result.record_found if report.database_result else None, "Status:", report.database_result.status_in_db if report.database_result else None)
