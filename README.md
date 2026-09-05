# AI-Based Fake Identity & Document Screening System
### Autonomous Border Control, MRTD Validation, Visual Forensics & Biometric Screening Platform

---

## 📌 Problem Overview & Border Checkpoint Challenges
Border checkpoints process thousands of identity and travel documents every day (passports, visas, national ID cards, driving licenses, and resident permits). Manual inspection is prone to fatigue, human error, and unable to detect sophisticated digital forgeries or multi-identity impersonation.

This platform provides an automated **4-Module AI Screening Solution**:
1. **Module 1: Multi-Document OCR & Field Extraction** (Passports, Visas, National IDs, Driving Licenses, Residence Permits).
2. **Module 2: Document Validation & Watchlists** (Full ICAO Doc 9303 TD1, TD2, TD3 Checksum validation, date logic, syntax validation, VIZ vs MRZ cross-checks, and INTERPOL SLTD / Sanctions database screening).
3. **Module 3: Core AI Tampering Detection** (Error Level Analysis (ELA), Local Noise Variance texture collapse, Photo replacement/splice detection, Visa stamp forgery detection, Metadata EXIF software trace analysis, and Copy-move text cloning detection).
4. **Module 4: Face Verification & Multi-Identity Impersonation Search** (Document portrait extraction, 1:1 live camera probe feature comparison, presentation anti-spoofing check, and 1:N Facial Gallery search to catch individuals using multiple names/passports).
5. **Integrated Risk Engine**: 0-100 weighted risk score with actionable traffic-light verdicts (`GREEN - CLEAR`, `YELLOW - SECONDARY REVIEW`, `RED - HIGH RISK FRAUD ESCALATION`).
6. **Border Officer Web Dashboard**: Live web kiosk with document viewer, visual heatmap overlays, biometric comparisons, and digital audit report exports.

---

## 🏛️ System Architecture

```
Facesih/
├── core/
│   ├── ocr/
│   │   ├── ocr_engine.py           # Multi-document OCR extractor & layout classifier
│   │   ├── mrz_ocr.py              # ICAO MRZ positional OCR & confusion corrector
│   │   └── field_parser.py         # Visual Inspection Zone (VIZ) parser
│   ├── validation/
│   │   ├── mrz_validator.py        # ICAO 9303 Check Digit Engine (TD1, TD2, TD3)
│   │   ├── rule_engine.py          # Date consistency, age checks, format/regex rules
│   │   ├── cross_validator.py      # VIZ vs MRZ cross-field comparator
│   │   └── blacklist_db.py         # Stolen travel document (SLTD) & watchlist database
│   ├── tampering/
│   │   ├── ela.py                  # Error Level Analysis (differential compression heatmap)
│   │   ├── variance.py             # Noise variance & texture consistency analyzer
│   │   ├── photo_splice.py         # Photo replacement & border splice gradient detector
│   │   ├── stamp_forgery.py        # Visa stamp detection & physical vs digital ink analysis
│   │   ├── metadata_forensics.py   # EXIF tags, software edit traces (Photoshop, GIMP)
│   │   ├── copy_move.py            # Text glyph duplication & block clone detector
│   │   └── forensic_orchestrator.py# Unified tampering forensics coordinator
│   ├── face/
│   │   ├── face_engine.py          # Face detection, portrait crop & biometric matcher
│   │   ├── liveness.py             # Anti-spoofing & screen glare heuristic
│   │   └── gallery_search.py       # 1:N facial search for multi-identity impersonation detection
│   └── risk_engine.py              # Weighted risk scoring engine (0-100) & decision verdict
├── generators/
│   ├── specimen_generator.py       # Multi-document synthetic generator (Passports, Visas, IDs)
│   └── fraud_synthesizer.py        # Fraud injections (DOB tamper, Photo splice, Stamp forgery, etc.)
├── ui/
│   ├── app.py                      # Flask Border Security Officer Web Dashboard
│   ├── templates/index.html        # Responsive command center dashboard UI
│   └── static/                     # CSS & client assets
├── tests/                          # Comprehensive automated unit & integration test suite
│   ├── test_mrz.py                 # TD1, TD2, TD3 ICAO check digit tests
│   ├── test_validation.py          # Rule engine, expiry, and watchlist tests
│   ├── test_tampering.py           # ELA, variance, splice, stamp, metadata tests
│   ├── test_face.py                # 1:1 biometrics & 1:N gallery search tests
│   ├── test_risk_scoring.py        # Risk scoring weights & verdicts tests
│   └── test_end_to_end.py          # End-to-end multi-specimen screening pipeline tests
├── run_pipeline.py                 # Unified CLI screening tool & test suite runner
├── requirements.txt                # Python dependencies
└── README.md                       # Documentation
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites & Installation
Ensure Python 3.9+ is installed. Install all dependencies:
```bash
pip install -r requirements.txt
```

### 2. Run End-to-End CLI Screening Demo
Generate the synthetic document suite and run automated 4-module screening across all test scenarios:
```bash
python3 run_pipeline.py --demo
```

### 3. Launch the Border Security Officer Web Dashboard
Start the web kiosk command center:
```bash
python3 run_pipeline.py --serve --port 5000
```
Then open your web browser at: **`http://localhost:5000`**

From the dashboard, border control officers can:
- Select from 8 preloaded synthetic fraud and genuine test scenarios
- Upload custom document scans and live traveler photos
- Inspect extracted VIZ fields and ICAO MRZ check digits
- View interactive **forensic heatmaps** (ELA, Variance, Photo Splice, Stamp Forgery)
- View side-by-side **biometric face matching** and **1:N Multi-Identity conflict alerts**
- Export timestamped digital screening reports (`.json`).

### 4. Run Automated Test Suite
Execute the test suite covering all modules:
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

---

## 📊 Module Capabilities Breakdown

### Module 1: Multi-Document OCR Extraction
- Extracts all standard fields from **Passports (TD3)**, **Visas (TD2)**, **National IDs (TD1)**, and **Driving Licenses**.
- Automatic positional OCR character confusion corrections ($O \leftrightarrow 0, I \leftrightarrow 1, S \leftrightarrow 5, B \leftrightarrow 8, Z \leftrightarrow 2$).
- Flexible date parser for all standard international date formats.

### Module 2: Document & Standards Validation
- **ICAO Doc 9303 Modulus 10 (7-3-1 weighting)** algorithm for TD1, TD2, and TD3.
- **Date consistency checks**: Issue date $\le$ Expiry date, expired document detection, age biological sanity checks.
- **Cross-field verification**: Matches printed VIZ text against MRZ decoded fields to catch asymmetric alterations.
- **Blacklist Database**: Screens document numbers and traveler names against INTERPOL Stolen & Lost Travel Documents (SLTD), UN sanctions, and border watchlists.

### Module 3: Tampering Detection (Core AI Innovation)
- **Error Level Analysis (ELA)**: Differential re-compression highlighting edited regions.
- **Noise Variance Forensics**: Flags localized variance collapse caused by digital solid-fill patch editing.
- **Photo Replacement / Splice Detection**: Detects edge gradient discontinuities and cut lines around document portrait boundaries.
- **Stamp Forgery Analysis**: Distinguishes authentic ink bleeding into paper fibers from sharp digital overlays.
- **Metadata & EXIF Forensics**: Extracts EXIF tags and flags photo editing software footprints (Adobe Photoshop, GIMP, Canva, ExifTool).
- **Copy-Move Forgery Detection**: Detects duplicated glyph blocks or cloned elements.

### Module 4: Face Verification & Multi-Identity Detection
- **1:1 Face Matching**: Compares document portrait against live camera probe using spatial color moments and gradient descriptors.
- **1:N Facial Watchlist & Impersonation Gallery**: Flags when the same individual attempts to cross the border under conflicting names or passports.
- **Presentation Attack / Anti-Spoofing Check**: Detects screen glare and flat display specular reflections.

---

## 🎯 Risk Scoring & Border Verdict Matrix

| Condition | Penalty | Impact |
| :--- | :---: | :--- |
| **Blacklist / SLTD Hit** | +65 | Immediate **RED** Verdict |
| **MRZ Checksum Failure** | +45 | Major Tampering Flag |
| **Multi-Identity Impersonation** | +45 | 1:N Biometric Conflict |
| **VIZ vs MRZ Field Mismatch** | +40 | Asymmetric Alteration |
| **Photo Splice / Replacement** | +40 | Impersonator Flag |
| **Local Variance Text Tamper** | +40 | Physical / Bitmap Modification |
| **Stamp Forgery** | +35 | Counterfeit Visa Stamp |
| **Biometric Face Mismatch** | +35 | Person is not Document Owner |
| **Expired Travel Document** | +30 | Document Invalid |

- 🟢 **GREEN ($0 - 24$)**: Cleared / Low Risk — Automated E-Gate Access.
- 🟡 **YELLOW ($25 - 59$)**: Warning / Secondary Inspection Recommended.
- 🔴 **RED ($60 - 100$)**: High Risk / Rejection / Escalate to Armed Border Officers.

---

## 📄 License & Safety Note
All synthetic specimen generation uses the fictional country **UTOPIA (UTO)** per ICAO testing conventions. No real identity documents or real personal information are used or generated.
