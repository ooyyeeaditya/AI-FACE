"""
ui.app
------
Indian Border Intelligence & Document Screening Web Dashboard & REST API.
Connects real document uploads and live webcam biometric capture with:
  - Persistent SQLite Backend Database (MEA Passport Registry, UIDAI CIDR, BOI Visas)
  - ICAO PKD & Digital PKI Security Signature Verification
  - Dynamic Multi-Signal Pixel Forensics & 1:1 Biometrics
  - Court-Admissible JSON Digital Audit Trail Export
"""

import os
import sys
from pathlib import Path
import json
import base64
from typing import Dict, Any

# Ensure workspace root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image

from core.database.db_manager import get_db_connection, init_database
from run_pipeline import (
    screen_document_pipeline,
    generate_all_demo_specimens,
    OUT_DIR,
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = OUT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
init_database()

DEMO_SUITE = {}


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "ui" / "templates"),
        static_folder=str(BASE_DIR / "ui" / "static"),
    )
    app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB max

    global DEMO_SUITE
    if not DEMO_SUITE:
        DEMO_SUITE = generate_all_demo_specimens()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/sw.js")
    def service_worker():
        response = send_from_directory(str(BASE_DIR / "ui" / "static"), "sw.js")
        response.headers["Content-Type"] = "application/javascript"
        response.headers["Service-Worker-Allowed"] = "/"
        return response

    @app.route("/manifest.json")
    def manifest():
        return send_from_directory(str(BASE_DIR / "ui" / "static"), "manifest.json", mimetype="application/manifest+json")

    @app.route("/api/specimens", methods=["GET"])
    def list_specimens():
        global DEMO_SUITE
        if not DEMO_SUITE:
            DEMO_SUITE = generate_all_demo_specimens()
        items = []
        for name, (doc_p, live_p, meta) in DEMO_SUITE.items():
            items.append({
                "name": name,
                "doc_type": meta.get("doc_type", "passport"),
                "doc_filename": Path(doc_p).name,
                "live_filename": Path(live_p).name,
            })
        return jsonify({"specimens": items})

    @app.route("/api/upload_and_screen", methods=["POST"])
    def upload_and_screen():
        doc_file = request.files.get("doc_file")
        live_file = request.files.get("live_file")
        doc_type_hint = request.form.get("doc_type", "passport")

        if not doc_file:
            return jsonify({"error": "No document image uploaded"}), 400

        doc_filename = secure_filename(f"upload_doc_{os.urandom(4).hex()}_{doc_file.filename}")
        doc_path = UPLOAD_DIR / doc_filename
        doc_file.save(str(doc_path))

        live_path = None
        live_filename = None
        if live_file and live_file.filename:
            live_filename = secure_filename(f"upload_live_{os.urandom(4).hex()}_{live_file.filename}")
            live_path = UPLOAD_DIR / live_filename
            live_file.save(str(live_path))

        report = screen_document_pipeline(
            str(doc_path),
            str(live_path) if live_path else None,
            doc_type_hint=doc_type_hint,
        )

        return jsonify(_format_report_response(report, doc_filename=f"uploads/{doc_filename}", live_filename=f"uploads/{live_filename}" if live_filename else None))

    @app.route("/api/screen", methods=["POST"])
    def screen_document():
        data = request.json or {}
        doc_filename = data.get("doc_filename")
        live_filename = data.get("live_filename")

        if not doc_filename:
            return jsonify({"error": "No document specified"}), 400

        doc_path = OUT_DIR / doc_filename
        live_path = (OUT_DIR / live_filename) if live_filename else None

        # Lookup demo specimen metadata if applicable
        template_meta = None
        doc_type_hint = None
        for name, (dp, lp, meta) in DEMO_SUITE.items():
            if Path(dp).name == Path(doc_filename).name:
                template_meta = meta
                doc_type_hint = meta.get("doc_type")
                break

        report = screen_document_pipeline(
            str(doc_path),
            str(live_path) if live_path else None,
            doc_type_hint=doc_type_hint,
            template_metadata=template_meta,
        )
        return jsonify(_format_report_response(report, doc_filename=doc_filename, live_filename=live_filename))

    @app.route("/api/db/register", methods=["POST"])
    def register_in_database():
        """Allow registering a real passport/Aadhaar/visa into the backend SQLite database."""
        data = request.json or {}
        doc_type = data.get("doc_type", "passport").lower()
        doc_number = data.get("doc_number", "").strip().upper()
        full_name = data.get("full_name", "").strip().upper()
        dob = data.get("dob", "1998-01-01").strip()
        expiry_date = data.get("expiry_date", "2035-01-01").strip()
        issue_date = data.get("issue_date", "2025-01-01").strip()
        gender = data.get("gender", "M").strip()
        status = data.get("status", "ACTIVE").strip()

        if not doc_number:
            return jsonify({"error": "Document number is required"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        if doc_type == "passport":
            parts = full_name.split()
            surname = parts[-1] if len(parts) > 1 else full_name
            given_names = " ".join(parts[:-1]) if len(parts) > 1 else ""
            cur.execute("""
                INSERT OR REPLACE INTO issued_passports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_number, "IND", surname, given_names, full_name, dob, gender, "INDIAN",
                "NEW DELHI", "DELHI", issue_date, expiry_date, f"DL{doc_number}25",
                "MOCK_CSCA_SIGNATURE_HASH", status
            ))
        elif doc_type in {"aadhaar", "national_id"}:
            cur.execute("""
                INSERT OR REPLACE INTO aadhaar_cidr VALUES (?, ?, ?, ?, ?)
            """, (doc_number.replace(" ", ""), full_name, dob, gender, status))
        elif doc_type == "visa":
            parts = full_name.split()
            cur.execute("""
                INSERT OR REPLACE INTO issued_visas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (doc_number, "Z1234567", parts[-1] if parts else "", " ".join(parts[:-1]), "TOURIST (T) - e-VISA", 90, "MULTIPLE", issue_date, expiry_date, status))

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Document {doc_number} successfully registered in {doc_type.upper()} database!"})

    @app.route("/api/db/query", methods=["GET"])
    def query_database():
        table = request.args.get("table", "issued_passports")
        query_val = request.args.get("q", "")
        conn = get_db_connection()
        cur = conn.cursor()

        if table == "issued_passports":
            cur.execute("SELECT * FROM issued_passports WHERE passport_number LIKE ? OR full_name LIKE ? LIMIT 20", (f"%{query_val}%", f"%{query_val}%"))
        elif table == "aadhaar_cidr":
            cur.execute("SELECT * FROM aadhaar_cidr WHERE aadhaar_number LIKE ? OR full_name LIKE ? LIMIT 20", (f"%{query_val}%", f"%{query_val}%"))
        elif table == "boi_lookout_circulars":
            cur.execute("SELECT * FROM boi_lookout_circulars WHERE doc_number LIKE ? OR name LIKE ? LIMIT 20", (f"%{query_val}%", f"%{query_val}%"))
        else:
            cur.execute("SELECT * FROM issued_passports LIMIT 10")

        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return jsonify({"table": table, "records": rows})

    def _format_report_response(report, doc_filename=None, live_filename=None):
        return {
            "doc_type": report.doc_type,
            "risk_score": report.risk_score,
            "verdict": report.verdict,
            "decision_text": report.decision_text,
            "reasons": report.reasons,
            "warnings": report.warnings,
            "timestamp": report.timestamp,
            "doc_filename": doc_filename,
            "live_filename": live_filename,
            "risk_breakdown": {
                "mrz_penalty": report.risk_breakdown.mrz_penalty,
                "cross_check_penalty": report.risk_breakdown.cross_check_penalty,
                "database_penalty": report.risk_breakdown.database_penalty,
                "pki_penalty": report.risk_breakdown.pki_penalty,
                "rule_penalty": report.risk_breakdown.rule_penalty,
                "blacklist_penalty": report.risk_breakdown.blacklist_penalty,
                "tampering_penalty": report.risk_breakdown.tampering_penalty,
                "face_penalty": report.risk_breakdown.face_penalty,
                "multi_identity_penalty": report.risk_breakdown.multi_identity_penalty,
            },
            "database": {
                "record_found": report.database_result.record_found if report.database_result else False,
                "status_in_db": report.database_result.status_in_db if report.database_result else "NOT_REGISTERED",
                "is_active": report.database_result.is_active if report.database_result else False,
                "discrepancies": report.database_result.discrepancies if report.database_result else [],
                "db_record": report.database_result.db_record if report.database_result else None,
            },
            "pki": {
                "pki_status": report.pki_result.pki_status if report.pki_result else "NO_CHIP",
                "signature_verified": report.pki_result.signature_verified if report.pki_result else False,
                "qr_detected": report.pki_result.qr_detected if report.pki_result else False,
                "csca_root": report.pki_result.csca_root_authority if report.pki_result else "ICAO-PKD-INDIA-CSCA",
                "discrepancies": report.pki_result.discrepancies if report.pki_result else [],
            },
            "ocr": {
                "fields": {k: str(v) for k, v in (report.ocr_result.viz_fields if report.ocr_result else {}).items()},
                "mrz_lines": report.ocr_result.mrz_lines if report.ocr_result else [],
                "mrz_all_ok": report.ocr_result.mrz_validation.all_ok if (report.ocr_result and report.ocr_result.mrz_validation) else False,
                "mrz_failures": report.ocr_result.mrz_validation.failures if (report.ocr_result and report.ocr_result.mrz_validation) else [],
                "ocr_confidence": report.ocr_result.ocr_confidence if report.ocr_result else None,
                "mrz_extracted": report.ocr_result.mrz_extracted if report.ocr_result else False,
            },
            "tampering": {
                "is_tampered": report.tampering_result.is_tampered if report.tampering_result else False,
                "confidence": report.tampering_result.tamper_confidence if report.tampering_result else 0.0,
                "reasons": report.tampering_result.reasons if report.tampering_result else [],
                "heatmaps": {k: Path(v).name for k, v in report.tampering_result.heatmap_paths.items()} if report.tampering_result else {},
            },
            "face": {
                "live_provided": bool(live_filename),
                "matched": report.face_result.matched if report.face_result else False,
                "similarity_score": report.face_result.similarity_score if report.face_result else 0.0,
                "status": report.face_result.status if report.face_result else "NOT_PERFORMED",
                "engine_used": report.face_result.engine_used if report.face_result else "none",
            },
            "gallery": {
                "multi_identity_flag": report.gallery_result.multi_identity_flag if report.gallery_result else False,
                "alert_message": report.gallery_result.alert_message if report.gallery_result else "",
            },
            "cross_check": {
                "all_matched": report.cross_check_result.all_matched if report.cross_check_result else True,
                "discrepancies": report.cross_check_result.discrepancies if report.cross_check_result else [],
                "field_results": [
                    {
                        "field_name": f.field_name,
                        "viz_value": str(f.viz_value),
                        "mrz_value": str(f.mrz_value),
                        "is_match": f.is_match,
                        "notes": f.notes,
                    }
                    for f in (report.cross_check_result.field_results if report.cross_check_result else [])
                ],
            },
            "blacklist": {
                "is_flagged": report.blacklist_result.is_flagged if report.blacklist_result else False,
                "summary": report.blacklist_result.alert_summary if report.blacklist_result else "",
            },
        }

    @app.route("/media/<path:filename>")
    def get_media(filename):
        return send_from_directory(str(OUT_DIR), filename)

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5050, debug=True)
