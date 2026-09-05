import cv2
import numpy as np
from PIL import Image
from core.validation.mrz_validator import auto_validate_mrz
from core.validation.database_comparator import verify_against_national_database

# Test parsing the MRZ of Pass1.jpg
mrz_line1 = "P<INDTHAPLIYAL<<GARIMA<<<<<<<<<<<<<<<<<<<<<<<"
mrz_line2 = "SP003369<2IND9407015F34090281065269546124<78"

val_res = auto_validate_mrz([mrz_line1, mrz_line2])
print("MRZ Validation All OK:", val_res.all_ok)
print("MRZ Failures:", val_res.failures)
print("MRZ Parsed Fields:", val_res.parsed_fields)

db_res = verify_against_national_database("passport", val_res.parsed_fields.get("document_number"), val_res.parsed_fields)
print("\nDatabase Lookup:")
print("Record Found:", db_res.record_found)
print("Status in DB:", db_res.status_in_db)
print("DB Record:", db_res.db_record)
print("Discrepancies:", db_res.discrepancies)
