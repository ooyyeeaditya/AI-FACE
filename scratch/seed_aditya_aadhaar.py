import sys
sys.path.insert(0, '/Users/aaryamanrana/Documents/Facesih ')
from core.database.db_manager import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("""
    INSERT OR REPLACE INTO aadhaar_cidr VALUES (
        '643227087263', 'ADITYA CHAUHAN', '2004-01-31', 'M', 'ACTIVE'
    )
""")
conn.commit()
conn.close()
print("Seeded Aditya Chauhan (643227087263) into aadhaar_cidr successfully!")
