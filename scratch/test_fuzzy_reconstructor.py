import re
from datetime import date
from core.validation.mrz_validator import auto_validate_mrz

def reconstruct_and_repair_td3(raw_l1: str, raw_l2: str) -> tuple:
    """Repair minor OCR noise in decoded TD3 lines using ICAO positional rules."""
    # Line 1: P<CCC SURNAME << GIVEN NAMES <<<<<...
    # Fix Line 1 header
    l1_chars = list(raw_l1.upper()[:44].ljust(44, "<"))
    l1_chars[0] = "P"
    l1_chars[1] = "<"
    l1_chars[2:5] = list("IND") if ("IND" in raw_l1 or "INQ" in raw_l1 or "JTD" in raw_l1) else l1_chars[2:5]
    
    # Line 2: [DocNum 9][CD 1][Country 3][DOB 6][CD 1][Sex 1][Exp 6][CD 1][Optional 14][CD 1][Composite 1]
    l2_chars = list(raw_l2.upper()[:44].ljust(44, "<"))
    
    # Force alpha/digits at known ICAO TD3 positions
    DIGIT_MAP = {"O": "0", "I": "1", "S": "5", "B": "8", "Z": "2", "Q": "0", "D": "0", "A": "4", "G": "6", "T": "7", "N": "0"}
    ALPHA_MAP = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z", "4": "A", "6": "G"}
    
    # Country at 10..12
    if "IND" in raw_l2 or "INQ" in raw_l2 or "JTD" in raw_l2:
        l2_chars[10:13] = list("IND")
        
    # Sex at index 20 (M/F/X)
    if l2_chars[20] in {"F", "P", "E"}:
        l2_chars[20] = "F"
    elif l2_chars[20] in {"M", "W", "H"}:
        l2_chars[20] = "M"
        
    # Correct digits at index 9, 13..19 (DOB), 21..27 (Expiry), 42..43
    for idx in [9, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 42, 43]:
        if idx < len(l2_chars) and l2_chars[idx] in DIGIT_MAP:
            l2_chars[idx] = DIGIT_MAP[l2_chars[idx]]
            
    return "".join(l1_chars), "".join(l2_chars)

raw_l1 = "MCINQTHAPL1YAL44G4SIPJ<<<<<<<<<<<<<<<<<<<<<<"
raw_l2 = "SMNN53BV4ZINQ9AQ7L35I3ACSC7F4FZF7ZSF4ZQJ4<Q1"
l1, l2 = reconstruct_and_repair_td3(raw_l1, raw_l2)
print("Repaired L1:", l1)
print("Repaired L2:", l2)
