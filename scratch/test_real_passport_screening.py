import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run_pipeline import screen_document_pipeline

doc_file = Path("output/upload_doc_dd04cc10_Screenshot_2026-09-04_235014.png")
if not doc_file.exists():
    for f in Path("output").glob("*Screenshot_2026-09-04_235014*"):
        doc_file = f
        break

print(f"Testing real uploaded passport scan: {doc_file}")
report = screen_document_pipeline(str(doc_file), doc_type_hint="passport")
print("\n" + report.to_summary_text())
print("\nExtracted VIZ Fields:")
for k, v in report.ocr_result.viz_fields.items():
    print(f"  {k:<20}: {v}")
print("\nMRZ Lines:")
for l in report.ocr_result.mrz_lines:
    print(f"  {l}")
