"""
VeriVote — Biometric Engine
File: biometric/matcher.py
Author: Person 1 (Aishhh)
Phase: 4 — Fingerprint Matching

ROOT CAUSE OF -1309 ERROR:
MFS100_E_NOT_INITIALIZED (-1309) means MatchISO requires the scanner
to be initialized (Init() called) before it will process any templates.
The scanner must be connected and Init() must succeed before matching.

TEMPLATE SIZE NOTE:
200-430 bytes is correct for Mantra's ISO templates. They are valid.

SIGNATURE (confirmed from DLL inspection):
    Int32 MatchISO(Byte[] template1, Byte[] template2, Int32 ByRef score)
    Returns tuple: (error_code, score)
    error_code 0 = success, score = match quality 0-100
"""

import os
import sys
import pickle
import cv2
import numpy as np

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

DLL_PATH   = r"C:\Program Files\Mantra\MFS100\Driver\MFS100Test\MANTRA.MFS100.dll"
DLL_FOLDER = os.path.dirname(DLL_PATH)

ISO_MATCH_THRESHOLD = 40
ORB_MATCH_THRESHOLD = 5.0
LOWE_RATIO          = 0.75

DESCRIPTOR_FOLDER = "descriptors"
CAPTURE_FOLDER    = "captured_fingerprints"


# ──────────────────────────────────────────────
# LOAD AND INITIALIZE SDK
# ──────────────────────────────────────────────

def load_and_init_mfs100():
    """
    Loads the DLL AND calls Init() — both are required before MatchISO.
    MFS100_E_NOT_INITIALIZED (-1309) is thrown if Init() is skipped.
    Scanner must be physically connected via USB.
    """
    try:
        import clr
        if DLL_FOLDER not in sys.path:
            sys.path.append(DLL_FOLDER)
        clr.AddReference(DLL_PATH)
        from MANTRA import MFS100

        mfs = MFS100()

        # Init() is REQUIRED before MatchISO — this was the root cause
        if not mfs.IsConnected():
            print("[ERROR] Scanner not connected. Plug in the USB scanner.")
            return None

        result = mfs.Init()
        code = result[0] if isinstance(result, tuple) else result
        if int(code) != 0:
            print(f"[ERROR] Init() failed with code {code}")
            return None

        print("[OK] Scanner loaded and initialized.")
        return mfs

    except Exception as e:
        print(f"[ERROR] Could not load/init MFS100: {e}")
        return None


def close_mfs100(mfs):
    try:
        mfs.Uninit()
    except Exception:
        pass


# ──────────────────────────────────────────────
# LOAD ISO TEMPLATE
# ──────────────────────────────────────────────

def load_iso_template(scan_label):
    path = os.path.join(CAPTURE_FOLDER, f"{scan_label}_iso_template.bin")
    if not os.path.exists(path):
        print(f"[WARNING] ISO template not found: {path}")
        return None
    with open(path, "rb") as f:
        data = f.read()
    print(f"[OK] ISO template: {path} ({len(data)} bytes)")
    return data


# ──────────────────────────────────────────────
# PRIMARY: ISO MATCHING
# ──────────────────────────────────────────────

def match_iso(mfs, t1_bytes, t2_bytes):
    """
    Calls MatchISO after scanner is initialized.
    Signature: Int32 MatchISO(Byte[], Byte[], Int32 ByRef)
    Returns tuple: (error_code, score)
    """
    import System

    t1 = System.Array[System.Byte](list(t1_bytes))
    t2 = System.Array[System.Byte](list(t2_bytes))

    try:
        raw = mfs.MatchISO(t1, t2, System.Int32(0))
        print(f"[DEBUG] MatchISO raw: {raw}")

        if isinstance(raw, tuple):
            error_code = int(raw[0])
            score = int(raw[1]) if len(raw) > 1 else 0
        else:
            error_code = 0
            score = int(raw)

        if error_code != 0:
            print(f"[ERROR] MatchISO error code: {error_code}")
            return None

        is_match = score >= ISO_MATCH_THRESHOLD
        print(f"[OK] MatchISO score: {score} → {'MATCH' if is_match else 'NO MATCH'}")

        return {
            "method": "ISO (MatchISO)",
            "is_match": is_match,
            "match_score": score,
            "verdict": "MATCH ✅" if is_match else "NO MATCH ❌"
        }

    except Exception as e:
        print(f"[ERROR] MatchISO exception: {str(e)[:120]}")
        return None


# ──────────────────────────────────────────────
# FALLBACK: ORB MATCHING
# ──────────────────────────────────────────────

def load_descriptor(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        desc = pickle.load(f)
    print(f"[OK] ORB descriptor: {path} ({desc.shape[0]} kp)")
    return desc


def match_orb(desc1, desc2):
    if desc1 is None or desc2 is None:
        return None
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    try:
        raw = bf.knnMatch(desc1, desc2, k=2)
    except Exception:
        return None
    good = []
    for pair in raw:
        if len(pair) == 2:
            b, s = pair
            if b.distance < LOWE_RATIO * s.distance:
                good.append(b)
    total = min(len(desc1), len(desc2))
    score = round((len(good) / total) * 100, 2) if total > 0 else 0
    return {
        "method": "ORB (fallback)",
        "is_match": score > ORB_MATCH_THRESHOLD,
        "match_score": score,
        "good_matches": len(good),
        "total_keypoints": total,
        "verdict": "MATCH ✅" if score > ORB_MATCH_THRESHOLD else "NO MATCH ❌"
    }


# ──────────────────────────────────────────────
# MAIN MATCH FUNCTION (called from Phase 6)
# ──────────────────────────────────────────────

def match_fingerprints(scan_label1, scan_label2):
    """
    Main function called from Phase 6.

    Parameters:
        scan_label1: e.g. "AISHHH_scan1"
        scan_label2: e.g. "AISHHH_scan2"

    Returns dict: is_match, match_score, method, verdict
    """
    mfs = load_and_init_mfs100()

    if mfs:
        t1 = load_iso_template(scan_label1)
        t2 = load_iso_template(scan_label2)
        if t1 and t2:
            result = match_iso(mfs, t1, t2)
            close_mfs100(mfs)
            if result:
                return result

    print("[INFO] Falling back to ORB matching.")
    d1 = load_descriptor(os.path.join(DESCRIPTOR_FOLDER, f"{scan_label1}_descriptor.pkl"))
    d2 = load_descriptor(os.path.join(DESCRIPTOR_FOLDER, f"{scan_label2}_descriptor.pkl"))
    return match_orb(d1, d2)


# ──────────────────────────────────────────────
# PRINT RESULT
# ──────────────────────────────────────────────

def print_match_result(result, label=""):
    if not result:
        print("[ERROR] No result.")
        return
    p = f"[{label}] " if label else ""
    method = result.get("method", "?")
    threshold = ISO_MATCH_THRESHOLD if "ISO" in method else ORB_MATCH_THRESHOLD
    print(f"\n{p}{'─'*45}")
    print(f"{p}Method:   {method}")
    print(f"{p}Verdict:  {result['verdict']}")
    print(f"{p}Score:    {result['match_score']}  (threshold: {threshold})")
    if "ORB" in method:
        print(f"{p}Matches:  {result.get('good_matches','?')} / {result.get('total_keypoints','?')}")
    print(f"{p}{'─'*45}")


# ──────────────────────────────────────────────
# TEST SUITE
# ──────────────────────────────────────────────

if __name__ == "__main__":

    print("="*55)
    print("  VeriVote — Fingerprint Matching Tests (Phase 4)")
    print("="*55)
    print("\nIMPORTANT: Make sure your MFS100 scanner is plugged in!")
    print("MatchISO requires the scanner to be connected.\n")

    iso_labels = sorted([f.replace("_iso_template.bin", "")
                         for f in os.listdir(CAPTURE_FOLDER)
                         if f.endswith("_iso_template.bin")])

    aishhh = [l for l in iso_labels if l.startswith("AISHHH")]
    others  = [l for l in iso_labels if not l.startswith("AISHHH")]

    print(f"AISHHH scans: {aishhh}")
    print(f"Other scans:  {others}")

    # Load and init scanner ONCE — reuse for all 3 tests
    mfs = load_and_init_mfs100()
    if mfs is None:
        print("\n[ERROR] Scanner could not be initialized.")
        print("Make sure the MFS100 is plugged into USB and try again.")
        exit(1)

    all_passed = True

    def run_iso_test(label1, label2, test_label, expect_match):
        t1 = load_iso_template(label1)
        t2 = load_iso_template(label2)
        if not t1 or not t2:
            print(f"  [SKIP] Could not load templates.")
            return
        result = match_iso(mfs, t1, t2)
        if result is None:
            print(f"  [ERROR] MatchISO returned None — check scanner connection.")
            return
        print_match_result(result, test_label)
        ok = result["is_match"] == expect_match
        print(f"  {'✅ PASSED' if ok else '❌ FAILED'}")
        if not ok:
            global all_passed
            all_passed = False

    # TEST 1 — self match
    print("\n\nTEST 1 — Same scan vs itself (expect MATCH)")
    print("─"*55)
    if aishhh:
        run_iso_test(aishhh[0], aishhh[0], "TEST 1", expect_match=True)

    # TEST 2 — same finger, different scan
    print("\n\nTEST 2 — Same finger, different scan (expect MATCH)")
    print("─"*55)
    if len(aishhh) >= 2:
        run_iso_test(aishhh[0], aishhh[1], "TEST 2", expect_match=True)
    else:
        print("  [SKIP] Need 2 AISHHH scans.")

    # TEST 3 — different fingers
    print("\n\nTEST 3 — Different fingers (expect NO MATCH)")
    print("─"*55)
    if aishhh and others:
        run_iso_test(aishhh[0], others[0], "TEST 3", expect_match=False)

    close_mfs100(mfs)

    print("\n"+"="*55)
    print(f"  Overall: {'ALL PASSED ✅' if all_passed else 'SOME FAILED ❌'}")
    print("="*55)