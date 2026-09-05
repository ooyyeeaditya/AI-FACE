"""
core.database.db_manager
------------------------
SQLite Backend Persistence & National Border Registry.
Stores and queries:
  1. Central Passport Issuance Registry (MEA / ICAO National Database)
  2. Bureau of Immigration (BOI) Visa Registry
  3. UIDAI Aadhaar Central Identity Repository (CIDR)
  4. Indian BOI Lookout Circulars (LOC) & CBI Watchlists
  5. INTERPOL Stolen and Lost Travel Documents (SLTD)
  6. 1:N Facial Biometric Crossing Gallery
  7. Digital Screening Audit Logs
"""

import sqlite3
from pathlib import Path
import json
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
import hashlib

import os
import tempfile

def _get_writable_db_path() -> Path:
    if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        return Path(tempfile.gettempdir()) / "border_control.db"
    default_p = Path(__file__).resolve().parent.parent.parent / "border_control.db"
    try:
        # Test if directory is writable
        parent = default_p.parent
        if not os.access(str(parent), os.W_OK):
            return Path(tempfile.gettempdir()) / "border_control.db"
        return default_p
    except Exception:
        return Path(tempfile.gettempdir()) / "border_control.db"

DB_PATH = _get_writable_db_path()


def get_db_connection() -> sqlite3.Connection:
    global DB_PATH
    try:
        conn = sqlite3.connect(str(DB_PATH))
    except (sqlite3.OperationalError, PermissionError):
        DB_PATH = Path(tempfile.gettempdir()) / "border_control.db"
        conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Create all required tables and seed baseline government intelligence records."""
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Issued Passports (National Database - Ministry of External Affairs)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS issued_passports (
            passport_number TEXT PRIMARY KEY,
            country_code TEXT NOT NULL,
            surname TEXT NOT NULL,
            given_names TEXT NOT NULL,
            full_name TEXT NOT NULL,
            dob TEXT NOT NULL,
            gender TEXT NOT NULL,
            nationality TEXT NOT NULL,
            place_of_birth TEXT,
            place_of_issue TEXT,
            issue_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            file_number TEXT,
            digital_signature_hash TEXT,
            status TEXT DEFAULT 'ACTIVE' -- 'ACTIVE', 'EXPIRED', 'REVOKED', 'REPORTED_LOST'
        )
    """)

    # 2. Issued Visas (Bureau of Immigration)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS issued_visas (
            visa_number TEXT PRIMARY KEY,
            passport_number TEXT NOT NULL,
            surname TEXT NOT NULL,
            given_names TEXT NOT NULL,
            visa_type TEXT NOT NULL,
            stay_duration_days INTEGER NOT NULL,
            entries TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            status TEXT DEFAULT 'VALID'
        )
    """)

    # 3. Aadhaar CIDR (UIDAI)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS aadhaar_cidr (
            aadhaar_number TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            dob TEXT NOT NULL,
            gender TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE' -- 'ACTIVE', 'SUSPENDED', 'DEACTIVATED'
        )
    """)

    # 4. Bureau of Immigration (BOI) Lookout Circulars (LOC)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS boi_lookout_circulars (
            loc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_number TEXT,
            name TEXT,
            dob TEXT,
            reason TEXT NOT NULL,
            originating_agency TEXT NOT NULL,
            date_flagged TEXT NOT NULL,
            severity TEXT DEFAULT 'CRITICAL'
        )
    """)

    # 5. INTERPOL Stolen and Lost Travel Documents (SLTD)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS interpol_sltd (
            doc_number TEXT PRIMARY KEY,
            country_code TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            holder_name TEXT,
            loss_location TEXT,
            date_reported TEXT NOT NULL,
            red_notice_details TEXT
        )
    """)

    # 6. 1:N Facial Biometric Crossing Gallery
    cur.execute("""
        CREATE TABLE IF NOT EXISTS traveler_biometric_gallery (
            traveler_id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_number TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            holder_name TEXT NOT NULL,
            nationality TEXT NOT NULL,
            embedding_json TEXT NOT NULL,
            first_seen_timestamp TEXT NOT NULL,
            last_seen_timestamp TEXT NOT NULL,
            crossing_count INTEGER DEFAULT 1
        )
    """)

    # 7. Screening Audit Logs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS screening_audit_logs (
            scan_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            doc_number TEXT,
            holder_name TEXT,
            risk_score INTEGER NOT NULL,
            verdict TEXT NOT NULL,
            decision_text TEXT NOT NULL,
            reasons_json TEXT,
            audit_json TEXT
        )
    """)

    conn.commit()

    # Seed baseline records if empty
    cur.execute("SELECT COUNT(*) FROM issued_passports")
    if cur.fetchone()[0] == 0:
        _seed_baseline_records(conn)

    conn.close()


def _compute_mock_digital_signature(passport_no: str, surname: str, given_names: str, dob: str, exp: str) -> str:
    payload = f"ICAO_PKD_MEA_INDIA:{passport_no}:{surname}:{given_names}:{dob}:{exp}:GOVERNMENT_OF_INDIA_CSCA_ROOT"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _seed_baseline_records(conn: sqlite3.Connection):
    cur = conn.cursor()

    # Seed Genuine Passports
    passports = [
        (
            "Z1234567", "IND", "RANA", "AARYAMAN", "AARYAMAN RANA", "1998-03-14", "M", "INDIAN",
            "NEW DELHI", "DELHI", "2023-06-10", "2033-06-09", "DL1061234567823",
            _compute_mock_digital_signature("Z1234567", "RANA", "AARYAMAN", "1998-03-14", "2033-06-09"), "ACTIVE"
        ),
        (
            "M4589214", "IND", "SHARMA", "PRIYA", "PRIYA SHARMA", "1995-07-22", "F", "INDIAN",
            "MUMBAI", "MUMBAI", "2021-04-15", "2031-04-14", "MH2049876543210",
            _compute_mock_digital_signature("M4589214", "SHARMA", "PRIYA", "1995-07-22", "2031-04-14"), "ACTIVE"
        ),
        (
            "Z7654321", "IND", "GUPTA", "RAVI", "RAVI GUPTA", "1985-05-20", "M", "INDIAN",
            "CHANDIGARH", "CHANDIGARH", "2013-01-15", "2023-01-14", "CH3012345678901",
            _compute_mock_digital_signature("Z7654321", "GUPTA", "RAVI", "1985-05-20", "2023-01-14"), "EXPIRED"
        ),
        (
            "Z9876543", "IND", "SINGH", "VIKRAM", "VIKRAM SINGH", "1980-05-12", "M", "INDIAN",
            "NEW DELHI", "DELHI", "2022-03-10", "2032-03-09", "DL1087654321098",
            _compute_mock_digital_signature("Z9876543", "SINGH", "VIKRAM", "1980-05-12", "2032-03-09"), "REVOKED"
        ),
    ]
    cur.executemany("""
        INSERT OR REPLACE INTO issued_passports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, passports)

    # Seed Visas
    visas = [
        ("V1234567", "Z5566778", "MILLER", "DAVID", "TOURIST (T) - e-VISA", 90, "MULTIPLE", "2026-01-10", "2027-01-10", "VALID"),
        ("V8877665", "P3456789", "SMITH", "SARAH", "BUSINESS (B) - VISA", 180, "MULTIPLE", "2025-08-01", "2026-08-01", "VALID"),
    ]
    cur.executemany("""
        INSERT OR REPLACE INTO issued_visas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, visas)

    # Seed Aadhaar CIDR
    aadhaar_records = [
        ("543210987652", "AARYAMAN RANA", "1998-03-14", "MALE", "ACTIVE"),
        ("987654321016", "PRIYA SHARMA", "1995-07-22", "FEMALE", "ACTIVE"),
        ("234567890124", "RAHUL SHARMA", "1991-07-14", "MALE", "DEACTIVATED"),
    ]
    cur.executemany("""
        INSERT OR REPLACE INTO aadhaar_cidr VALUES (?, ?, ?, ?, ?)
    """, aadhaar_records)

    # Seed Lookout Circulars (LOC)
    loc_records = [
        ("Z9876543", "VIKRAM SINGH", "1980-05-12", "BOI / CBI Lookout Circular: Financial fugitive and counterfeit document trafficking", "BOI-DELHI / CBI", "2024-01-10", "CRITICAL"),
        ("M4589214", "ROHIT VERMA", "1984-10-25", "Regional Passport Office Mumbai: Revoked passport due to fraudulent duplicate issuance", "MEA-RPO-MUMBAI", "2023-11-04", "HIGH"),
    ]
    cur.executemany("""
        INSERT OR REPLACE INTO boi_lookout_circulars (doc_number, name, dob, reason, originating_agency, date_flagged, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, loc_records)

    # Seed INTERPOL SLTD
    interpol_records = [
        ("Z9876543", "IND", "PASSPORT", "VIKRAM SINGH", "Reported lost/stolen at Zurich Airport", "2024-01-15", "INTERPOL Red Notice Ref #A-2024/9871"),
        ("V5544332", "IND", "VISA", "ALEXANDER VORONOV", "Intercept Order - Sanctions List", "2023-09-12", "UN Travel Ban & Border Intercept Alert"),
    ]
    cur.executemany("""
        INSERT OR REPLACE INTO interpol_sltd VALUES (?, ?, ?, ?, ?, ?, ?)
    """, interpol_records)

    conn.commit()


# Initialize database automatically on module import
init_database()
