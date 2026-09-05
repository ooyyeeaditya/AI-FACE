import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
from PIL import Image
import numpy as np

# Seed DP001097 into border_control.db
from core.database.db_manager import get_db_connection, _compute_mock_digital_signature

conn = get_db_connection()
cur = conn.cursor()
cur.execute("""
    INSERT OR REPLACE INTO issued_passports VALUES (
        'DP001097', 'IND', 'RANA', 'AARYAMAN', 'AARYAMAN RANA', '2006-05-17', 'M', 'INDIAN',
        'DELHI, DELHI', 'NEW DELHI', '2025-06-10', '2030-06-09', 'DL1065173112425',
        ?, 'ACTIVE'
    )
""", (_compute_mock_digital_signature('DP001097', 'RANA', 'AARYAMAN', '2006-05-17', '2030-06-09'),))
conn.commit()
conn.close()
print("Seeded DP001097 into border_control.db successfully!")
