"""
VeriVote — Biometric Engine
File: biometric/verify.py
Author: Person 1 (Aishhh)
Phase: 6 — Verification Flow

What this file does:
1. Booth officer enters Voter ID
2. Fetches voter record from Django backend
3. Check 1: Is voter registered? (404 = not enrolled)
4. Check 2: Has voter already voted? (has_voted flag)
5. Check 3: Biometric match (MatchISO live scan vs stored template)
6. If all checks pass → APPROVED → record vote in DB
7. If any check fails → REJECTED with specific reason

This is the core of the entire VeriVote system.
"""

import sys
import os
import base64
import requests

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

DJANGO_API_BASE = "http://127.0.0.1:8000"

GET_VOTER_URL    = f"{DJANGO_API_BASE}/api/voter/"
RECORD_VOTE_URL  = f"{DJANGO_API_BASE}/api/record-vote/"

ISO_MATCH_THRESHOLD = 40

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from capture import load_dll, init_scanner, capture_fingerprint, close_scanner


# ──────────────────────────────────────────────
# RESULT CODES
# ──────────────────────────────────────────────

APPROVED              = "APPROVED"
REJECTED_NOT_ENROLLED = "REJECTED_NOT_ENROLLED"
REJECTED_ALREADY_VOTED = "REJECTED_ALREADY_VOTED"
REJECTED_BIOMETRIC    = "REJECTED_BIOMETRIC"
REJECTED_SCAN_FAILED  = "REJECTED_SCAN_FAILED"
ERROR                 = "ERROR"


# ──────────────────────────────────────────────
# STEP 1 — FETCH VOTER FROM BACKEND
# ──────────────────────────────────────────────

def fetch_voter(voter_id):
    """
    Calls GET /api/voter/<voter_id>/ to fetch voter details.

    Returns:
        voter dict  if found
        None        if not found (404)
        "error"     if connection failed
    """
    try:
        response = requests.get(f"{GET_VOTER_URL}{voter_id}/", timeout=5)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            print(f"  [ERROR] Unexpected status {response.status_code}")
            return "error"

    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] Cannot connect to Django at {DJANGO_API_BASE}")
        print("  → Make sure 'python manage.py runserver' is running.")
        return "error"


# ──────────────────────────────────────────────
# STEP 2 — SCAN LIVE FINGERPRINT
# ──────────────────────────────────────────────

def scan_live_fingerprint(mfs):
    """
    Scans a live fingerprint at the booth.
    Returns ISO template bytes, or None if scan failed.
    """
    MAX_RETRIES = 3
    QUALITY_THRESHOLD = 60

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n  Attempt {attempt} of {MAX_RETRIES}")
        print("  Place finger on scanner...")

        finger_data, quality = capture_fingerprint(mfs, timeout_ms=15000)

        if finger_data is None:
            print("  [RETRY] Capture failed.")
            continue

        if quality < QUALITY_THRESHOLD:
            print(f"  [RETRY] Quality too low: {quality}/100")
            if attempt < MAX_RETRIES:
                print("  → Press more firmly and center on scanner.")
            continue

        try:
            iso_raw = finger_data.ISOTemplate
            if iso_raw is None:
                print("  [RETRY] ISO template is None.")
                continue
            iso_bytes = bytes(iso_raw)
            print(f"  [OK] Live scan captured! Quality: {quality}/100")
            return iso_bytes

        except Exception as e:
            print(f"  [RETRY] Could not get ISO template: {e}")
            continue

    print("\n  [FAILED] Could not get good scan after 3 attempts.")
    return None


# ──────────────────────────────────────────────
# STEP 3 — BIOMETRIC MATCHING
# ──────────────────────────────────────────────

def match_fingerprint(live_template_bytes, stored_template_b64):
    """
    Matches live fingerprint against stored template using MatchISO.

    The stored template comes from Django as base64 — we decode it first.
    Then we call MatchISO with both templates.

    Returns (is_match, score)
    """
    import System
    import clr

    DLL_PATH   = r"C:\Program Files\Mantra\MFS100\Driver\MFS100Test\MANTRA.MFS100.dll"
    DLL_FOLDER = os.path.dirname(DLL_PATH)

    try:
        # Load SDK
        if DLL_FOLDER not in sys.path:
            sys.path.append(DLL_FOLDER)
        clr.AddReference(DLL_PATH)
        from MANTRA import MFS100
        mfs_matcher = MFS100()

        # Initialize scanner for matching
        if not mfs_matcher.IsConnected():
            print("  [ERROR] Scanner not connected for matching.")
            return False, 0

        result = mfs_matcher.Init()
        code = result[0] if isinstance(result, tuple) else result
        if int(code) != 0:
            print(f"  [ERROR] Init failed for matching: {code}")
            return False, 0

        # Decode stored template from base64
        stored_bytes = base64.b64decode(stored_template_b64)

        # Convert to System.Byte[]
        live_dotnet   = System.Array[System.Byte](list(live_template_bytes))
        stored_dotnet = System.Array[System.Byte](list(stored_bytes))

        # Call MatchISO
        raw = mfs_matcher.MatchISO(live_dotnet, stored_dotnet, System.Int32(0))

        if isinstance(raw, tuple):
            error_code = int(raw[0])
            score = int(raw[1]) if len(raw) > 1 else 0
        else:
            error_code = 0
            score = int(raw)

        mfs_matcher.Uninit()

        if error_code != 0:
            print(f"  [ERROR] MatchISO error code: {error_code}")
            return False, 0

        is_match = score >= ISO_MATCH_THRESHOLD
        print(f"  [OK] Match score: {score} (threshold: {ISO_MATCH_THRESHOLD})")
        return is_match, score

    except Exception as e:
        print(f"  [ERROR] Matching exception: {e}")
        return False, 0


# ──────────────────────────────────────────────
# STEP 4 — RECORD VOTE IN BACKEND
# ──────────────────────────────────────────────

def record_vote(voter_id):
    """
    Calls POST /api/record-vote/ to mark voter as has_voted=True.
    This prevents them from voting again anywhere.
    Returns True if successful.
    """
    try:
        response = requests.post(
            RECORD_VOTE_URL,
            json={"voter_id": voter_id},
            timeout=5
        )
        if response.status_code == 200:
            return True
        else:
            print(f"  [ERROR] record-vote returned {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"  [ERROR] Could not record vote: {e}")
        return False


# ──────────────────────────────────────────────
# PRINT VERDICT
# ──────────────────────────────────────────────

def print_verdict(verdict, voter_name=None, score=None):
    """Prints a clear, prominent verdict on screen."""
    print("\n" + "█"*50)

    if verdict == APPROVED:
        print("█                                                █")
        print("█           ✅  APPROVED TO VOTE  ✅            █")
        print("█                                                █")
        if voter_name:
            name_line = f"█   Voter: {voter_name:<37}█"
            print(name_line)
        if score:
            print(f"█   Biometric Score: {score:<29}█")
        print("█   Please proceed to the EVM.                  █")
        print("█                                                █")

    elif verdict == REJECTED_NOT_ENROLLED:
        print("█                                                █")
        print("█         ❌  REJECTED — NOT ENROLLED  ❌       █")
        print("█                                                █")
        print("█   This Voter ID is not in the system.         █")
        print("█   Please contact the election officer.        █")
        print("█                                                █")

    elif verdict == REJECTED_ALREADY_VOTED:
        print("█                                                █")
        print("█       ❌  REJECTED — ALREADY VOTED  ❌        █")
        print("█                                                █")
        print("█   This voter has already cast their vote.     █")
        print("█   Duplicate voting attempt flagged.           █")
        print("█                                                █")

    elif verdict == REJECTED_BIOMETRIC:
        print("█                                                █")
        print("█    ❌  REJECTED — FINGERPRINT MISMATCH  ❌    █")
        print("█                                                █")
        print("█   Fingerprint does not match enrollment.      █")
        print("█   Possible impersonation attempt flagged.     █")
        if score is not None:
            print(f"█   Match score: {score} (required: {ISO_MATCH_THRESHOLD}+){' '*20}█")
        print("█                                                █")

    elif verdict == REJECTED_SCAN_FAILED:
        print("█                                                █")
        print("█      ❌  REJECTED — SCAN FAILED  ❌           █")
        print("█                                                █")
        print("█   Could not capture fingerprint.              █")
        print("█   Please try again or use OTP fallback.       █")
        print("█                                                █")

    elif verdict == ERROR:
        print("█                                                █")
        print("█         ⚠️   SYSTEM ERROR  ⚠️                 █")
        print("█                                                █")
        print("█   Could not connect to backend.               █")
        print("█   Contact technical support.                  █")
        print("█                                                █")

    print("█"*50)


# ──────────────────────────────────────────────
# MAIN VERIFICATION FLOW
# ──────────────────────────────────────────────

def verify_voter(mfs, voter_id):
    """
    Runs the complete verification flow for one voter.

    Parameters:
        mfs      : initialized MFS100 scanner object
        voter_id : voter ID typed by booth officer

    Returns verdict string (APPROVED or one of the REJECTED_ codes)
    """
    print(f"\n  Verifying voter: {voter_id}")
    print("  " + "─"*40)

    # ── CHECK 1: Is voter registered? ─────────
    print("\n  [CHECK 1] Looking up voter in database...")
    voter = fetch_voter(voter_id)

    if voter == "error":
        print_verdict(ERROR)
        return ERROR

    if voter is None:
        print(f"  → Voter {voter_id} not found in database.")
        print_verdict(REJECTED_NOT_ENROLLED)
        return REJECTED_NOT_ENROLLED

    print(f"  → Found: {voter['full_name']}")

    # ── CHECK 2: Already voted? ────────────────
    print("\n  [CHECK 2] Checking voting status...")

    if voter['has_voted']:
        print(f"  → {voter['full_name']} has already voted!")
        print_verdict(REJECTED_ALREADY_VOTED, voter['full_name'])
        return REJECTED_ALREADY_VOTED

    print("  → Has not voted yet. ✓")

    # ── CHECK 3: Biometric match ───────────────
    print(f"\n  [CHECK 3] Biometric verification for {voter['full_name']}")
    print("  Scanning live fingerprint...")

    live_template = scan_live_fingerprint(mfs)

    if live_template is None:
        print_verdict(REJECTED_SCAN_FAILED)
        return REJECTED_SCAN_FAILED

    print("  Matching against enrolled fingerprint...")
    is_match, score = match_fingerprint(live_template, voter['fingerprint_template'])

    if not is_match:
        print(f"  → Fingerprint mismatch! Score: {score}")
        print_verdict(REJECTED_BIOMETRIC, voter['full_name'], score)
        return REJECTED_BIOMETRIC

    print(f"  → Fingerprint matched! Score: {score} ✓")

    # ── ALL CHECKS PASSED — Record vote ────────
    print("\n  [RECORDING VOTE] Marking voter as voted...")
    success = record_vote(voter_id)

    if not success:
        print("  [ERROR] Could not record vote in database!")
        return ERROR

    print(f"  → Vote recorded for {voter['full_name']} ✓")
    print_verdict(APPROVED, voter['full_name'], score)
    return APPROVED


# ──────────────────────────────────────────────
# BOOTH SESSION
# ──────────────────────────────────────────────

def run_booth_session():
    """
    Runs a full polling booth session.
    Keeps verifying voters until officer types 'close'.
    """
    print("\n" + "="*50)
    print("  VeriVote — Polling Booth Terminal")
    print("  Phase 6: Voter Verification")
    print("="*50)
    print(f"\n  Backend: {DJANGO_API_BASE}")

    # Check backend
    try:
        requests.get(DJANGO_API_BASE, timeout=3)
        print("  [OK] Backend is reachable.")
    except Exception:
        print(f"  [ERROR] Cannot reach backend at {DJANGO_API_BASE}")
        print("  → Start Django: python manage.py runserver")
        return

    # Initialize scanner once
    print("\n  Initializing scanner...")
    mfs = load_dll()
    if mfs is None:
        print("  [ERROR] Could not load scanner.")
        return

    if not init_scanner(mfs):
        print("  [ERROR] Could not initialize scanner.")
        return

    print("\n  ✅ Booth is ready. Waiting for voters...")

    # Session stats
    stats = {
        APPROVED: 0,
        REJECTED_NOT_ENROLLED: 0,
        REJECTED_ALREADY_VOTED: 0,
        REJECTED_BIOMETRIC: 0,
        REJECTED_SCAN_FAILED: 0,
    }

    while True:
        print("\n" + "="*50)
        voter_id = input("  Enter Voter ID (or 'close' to end session): ").strip().upper()

        if voter_id in ("CLOSE", ""):
            print("\n  Closing booth session...")
            break

        verdict = verify_voter(mfs, voter_id)

        if verdict in stats:
            stats[verdict] += 1

        input("\n  Press Enter for next voter...")

    close_scanner(mfs)

    # Session summary
    total = sum(stats.values())
    print("\n" + "="*50)
    print("  BOOTH SESSION SUMMARY")
    print("="*50)
    print(f"  Total processed:       {total}")
    print(f"  ✅ Approved:           {stats[APPROVED]}")
    print(f"  ❌ Not enrolled:       {stats[REJECTED_NOT_ENROLLED]}")
    print(f"  ❌ Already voted:      {stats[REJECTED_ALREADY_VOTED]}")
    print(f"  ❌ Biometric mismatch: {stats[REJECTED_BIOMETRIC]}")
    print(f"  ❌ Scan failed:        {stats[REJECTED_SCAN_FAILED]}")
    print("="*50)


# ──────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────

if __name__ == "__main__":
    run_booth_session()