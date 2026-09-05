import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
from PIL import Image
from core.ocr.ocr_engine import GLOBAL_OCR_ENGINE
from run_pipeline import screen_document_pipeline

doc_p = '/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_doc_7a940e47_Screenshot_2026-09-04_at_6.47.01_PM.png'
live_p = '/Users/aaryamanrana/Documents/Facesih /output/uploads/upload_live_1439ccc9_IMG_0445.jpeg'

# Screen pipeline
report = screen_document_pipeline(doc_p, live_p, doc_type_hint='passport')
print("Risk Score:", report.risk_score, "Verdict:", report.verdict)
print("Decision:", report.decision_text)
print("Reasons:", report.reasons)
print("MRZ Lines:", report.ocr_result.mrz_lines if report.ocr_result else None)
print("VIZ Fields:", report.ocr_result.viz_fields if report.ocr_result else None)
print("Database Match:", report.database_result.record_found if report.database_result else None, "Status:", report.database_result.status_in_db if report.database_result else None)
print("Face Matched:", report.face_result.matched if report.face_result else None, "Similarity:", report.face_result.similarity_score if report.face_result else None)
