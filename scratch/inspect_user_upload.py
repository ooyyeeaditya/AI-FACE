import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_pipeline import screen_document_pipeline

doc_file = Path("output/uploads/upload_doc_845cc9ae_Screenshot_2026-09-05_025647.png")
print(f"File exists: {doc_file.exists()}")

report = screen_document_pipeline(str(doc_file), doc_type_hint="aadhaar")
print("\n" + report.to_summary_text())
print("\nExtracted VIZ:")
for k, v in report.ocr_result.viz_fields.items():
    print(f"  {k}: {v}")
print("\nRaw Text:")
print(report.ocr_result.raw_text)
