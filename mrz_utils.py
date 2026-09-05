"""
mrz_utils.py
------------
Implements the ICAO Doc 9303 Part 4 check-digit algorithm for TD3
(passport-style, 2-line x 44-char) Machine Readable Zones.

This is the same public algorithm every real passport, and every
e-gate / border kiosk, uses to validate the MRZ. It is not a secret
or proprietary system — it's an open ICAO standard. Implementing it
correctly is what lets Module 2 (Document Validation) catch a huge
class of forgeries "for free": if even a single character in the
MRZ or the fields it encodes is altered, the check digit(s) break.

Reference worked example we self-test against (from ICAO 9303-4,
also widely reproduced in MRZ tutorials):

    Line 1: P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<
    Line 2: L898902C36UTO7408122F1204159ZE184226B<<<<<10
"""

from dataclasses import dataclass
from datetime import date

WEIGHTS = [7, 3, 1]


def _char_value(c: str) -> int:
    """Map a single MRZ character to its numeric value per ICAO 9303."""
    if c == "<":
        return 0
    if c.isdigit():
        return int(c)
    if c.isalpha():
        return ord(c.upper()) - ord("A") + 10
    raise ValueError(f"Invalid MRZ character: {c!r}")


def check_digit(data: str) -> int:
    """Compute the ICAO 9303 check digit for a string of MRZ characters."""
    total = 0
    for i, c in enumerate(data):
        total += _char_value(c) * WEIGHTS[i % 3]
    return total % 10


def verify_check_digit(data: str, digit: str) -> bool:
    if digit == "<":
        # Some fields use '<' as a filler check digit when the field is empty
        return data.strip("<") == ""
    return check_digit(data) == int(digit)


@dataclass
class PassportMRZFields:
    surname: str
    given_names: str
    passport_number: str
    nationality: str  # 3-letter code, e.g. UTO
    dob: date
    sex: str  # 'M', 'F', or 'X'
    expiry: date
    country_code: str  # issuing country, 3-letter, e.g. UTO
    personal_number: str = ""  # optional, up to 14 chars


def _fmt_yymmdd(d: date) -> str:
    return d.strftime("%y%m%d")


def _pad(s: str, length: int) -> str:
    s = s[:length]
    return s + "<" * (length - len(s))


def build_td3_mrz(f: PassportMRZFields) -> tuple[str, str]:
    """Build a valid two-line TD3 MRZ from passport fields, computing all
    check digits so the result is internally consistent (a "genuine" MRZ)."""

    # ---- Line 1 ----
    name_field = f"{f.surname.upper()}<<{f.given_names.upper()}".replace(" ", "<")
    line1 = "P<" + _pad(f.country_code.upper(), 3) + _pad(name_field, 39)
    line1 = _pad(line1, 44)

    # ---- Line 2 ----
    passport_no = _pad(f.passport_number.upper(), 9)
    passport_cd = check_digit(passport_no)

    dob_str = _fmt_yymmdd(f.dob)
    dob_cd = check_digit(dob_str)

    expiry_str = _fmt_yymmdd(f.expiry)
    expiry_cd = check_digit(expiry_str)

    personal_no = _pad(f.personal_number, 14)
    personal_cd = check_digit(personal_no)

    composite_input = (
        passport_no + str(passport_cd) + dob_str + str(dob_cd) +
        expiry_str + str(expiry_cd) + personal_no + str(personal_cd)
    )
    composite_cd = check_digit(composite_input)

    line2 = (
        passport_no + str(passport_cd) +
        _pad(f.nationality.upper(), 3) +
        dob_str + str(dob_cd) +
        f.sex.upper()[:1] +
        expiry_str + str(expiry_cd) +
        personal_no + str(personal_cd) +
        str(composite_cd)
    )
    line2 = _pad(line2, 44)

    return line1, line2


@dataclass
class MRZValidationResult:
    passport_number_ok: bool
    dob_ok: bool
    expiry_ok: bool
    personal_number_ok: bool
    composite_ok: bool

    @property
    def all_ok(self) -> bool:
        return all([
            self.passport_number_ok, self.dob_ok,
            self.expiry_ok, self.personal_number_ok, self.composite_ok,
        ])

    def failures(self) -> list[str]:
        names = {
            "passport_number_ok": "passport number check digit",
            "dob_ok": "date-of-birth check digit",
            "expiry_ok": "expiry date check digit",
            "personal_number_ok": "personal number check digit",
            "composite_ok": "composite (final) check digit",
        }
        return [label for field, label in names.items() if not getattr(self, field)]


def validate_td3_line2(line2: str) -> MRZValidationResult:
    """Recompute every check digit in an MRZ line 2 and compare against what
    is actually printed. This is exactly what an e-gate / kiosk does, and
    exactly what should flag a document where a field was edited without
    regenerating the MRZ (the #1 tell-tale sign of amateur tampering)."""
    line2 = line2.strip("\n")
    if len(line2) != 44:
        raise ValueError(f"TD3 line 2 must be 44 chars, got {len(line2)}")

    passport_no = line2[0:9]
    passport_cd = line2[9]
    dob_str = line2[13:19]
    dob_cd = line2[19]
    expiry_str = line2[21:27]
    expiry_cd = line2[27]
    personal_no = line2[28:42]
    personal_cd = line2[42]

    composite_input = (
        passport_no + passport_cd + dob_str + dob_cd +
        expiry_str + expiry_cd + personal_no + personal_cd
    )
    composite_cd = line2[43]

    return MRZValidationResult(
        passport_number_ok=verify_check_digit(passport_no, passport_cd),
        dob_ok=verify_check_digit(dob_str, dob_cd),
        expiry_ok=verify_check_digit(expiry_str, expiry_cd),
        personal_number_ok=verify_check_digit(personal_no, personal_cd),
        composite_ok=verify_check_digit(composite_input, composite_cd),
    )


if __name__ == "__main__":
    # Self-test against the official ICAO 9303 worked example
    icao_line2 = "L898902C36UTO7408122F1204159ZE184226B<<<<<10"
    result = validate_td3_line2(icao_line2)
    print("ICAO reference example line 2:", icao_line2)
    print("Validation result:", result)
    assert result.all_ok, "MRZ engine does NOT match the ICAO reference example!"
    print("PASS: MRZ engine matches the official ICAO 9303 reference example.\n")

    # Round-trip test: build our own MRZ, then validate it
    fields = PassportMRZFields(
        surname="SHARMA", given_names="ARUN KUMAR",
        passport_number="X1234567", nationality="UTO",
        dob=date(1995, 3, 14), sex="M", expiry=date(2032, 6, 30),
        country_code="UTO",
    )
    l1, l2 = build_td3_mrz(fields)
    print("Generated line 1:", l1)
    print("Generated line 2:", l2)
    r2 = validate_td3_line2(l2)
    assert r2.all_ok, "Freshly generated MRZ failed its own validation!"
    print("PASS: freshly generated MRZ validates cleanly.\n")

    # Tamper test: change DOB digit in the printed data WITHOUT recomputing MRZ
    tampered = list(l2)
    tampered[13] = "9" if tampered[13] != "9" else "8"  # flip one DOB digit
    tampered_l2 = "".join(tampered)
    r3 = validate_td3_line2(tampered_l2)
    print("Tampered line 2:", tampered_l2)
    print("Validation result:", r3, "-> failures:", r3.failures())
    assert not r3.all_ok, "Tamper test should have failed validation!"
    print("PASS: single-digit tamper is correctly caught.")
