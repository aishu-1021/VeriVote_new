"""
VeriVote — Biometric Engine
File: biometric/enroll.py
Author: Person 1 (Aishhh)
Phase: 5 — Enrollment Flow

What this file does:
1. Asks booth officer to type voter_id and full_name
2. Scans the voter's fingerprint (capture.py)
3. Extracts the ISO template
4. Sends everything to Django backend via POST /api/enroll-voter/
5. Confirms enrollment was saved in the database

To change the server address (if Django runs on a different machine):
    Change DJANGO_API_BASE at the top of this file.
    Same machine:      http://127.0.0.1:8000
    Different machine: http://<that-machine-ip>:8000
"""

import sys
import os
import base64
import requests  # pip install requests

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

# Change this if Django runs on a different machine
DJANGO_API_BASE = "http://127.0.0.1:8000"

ENROLL_URL = f"{DJANGO_API_BASE}/api/enroll-voter/"
GET_VOTER_URL = f"{DJANGO_API_BASE}/api/voter/"

# Make sure biometric folder is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from capture import load_dll, init_scanner, capture_fingerprint, save_image, save_iso_template, close_scanner


# ──────────────────────────────────────────────
# STEP 1 — GET VOTER DETAILS FROM BOOTH OFFICER
# ──────────────────────────────────────────────

def get_voter_details():
    """
    Asks the booth officer to type in the voter's details.
    Returns (voter_id, full_name) or (None, None) if cancelled.
    """
    print("\n" + "─"*50)
    print("  VOTER ENROLLMENT — Enter Details")
    print("─"*50)

    voter_id = input("  Enter Voter ID (or 'cancel' to quit): ").strip().upper()
    if voter_id in ("CANCEL", ""):
        return None, None

    full_name = input("  Enter Full Name: ").strip()
    if not full_name:
        print("  [ERROR] Full name cannot be empty.")
        return None, None

    # Confirm details before scanning
    print(f"\n  Voter ID:  {voter_id}")
    print(f"  Name:      {full_name}")
    confirm = input("\n  Is this correct? (y/n): ").strip().lower()

    if confirm != 'y':
        print("  [CANCELLED] Please re-enter details.")
        return None, None

    return voter_id, full_name


# ──────────────────────────────────────────────
# STEP 2 — CHECK IF VOTER ALREADY ENROLLED
# ──────────────────────────────────────────────

def check_already_enrolled(voter_id):
    """
    Calls GET /api/voter/<voter_id>/ to check if voter exists.
    Returns True if already enrolled, False if not.
    """
    try:
        response = requests.get(f"{GET_VOTER_URL}{voter_id}/", timeout=5)
        if response.status_code == 200:
            return True   # voter exists
        elif response.status_code == 404:
            return False  # voter not found — safe to enroll
        else:
            print(f"  [WARNING] Unexpected status {response.status_code} checking voter.")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] Cannot connect to Django server at {DJANGO_API_BASE}")
        print("  → Make sure 'python manage.py runserver' is running.")
        return None  # None = connection error


# ──────────────────────────────────────────────
# STEP 3 — SCAN FINGERPRINT
# ──────────────────────────────────────────────

def scan_fingerprint(mfs, voter_id):
    """
    Captures fingerprint and returns the ISO template bytes.
    Retries up to 3 times if quality is low.
    Returns iso_template_bytes or None if failed.
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
                print("  → Try again: press firmly, center on scanner.")
            continue

        # Get ISO template
        try:
            iso_raw = finger_data.ISOTemplate
            if iso_raw is None:
                print("  [RETRY] ISO template is None.")
                continue
            iso_bytes = bytes(iso_raw)
            print(f"  [OK] Fingerprint captured! Quality: {quality}/100")
            print(f"  [OK] ISO template: {len(iso_bytes)} bytes")

            # Save locally as backup
            save_image(mfs, finger_data, f"{voter_id}_enrollment.bmp")
            save_iso_template(finger_data, f"{voter_id}_enrollment")

            return iso_bytes

        except Exception as e:
            print(f"  [RETRY] Could not get ISO template: {e}")
            continue

    print("\n  [FAILED] Could not get good scan after 3 attempts.")
    print("  → OTP fallback should be triggered (Phase 7).")
    return None


# ──────────────────────────────────────────────
# STEP 4 — SEND TO DJANGO BACKEND
# ──────────────────────────────────────────────

def send_to_backend(voter_id, full_name, iso_template_bytes):
    """
    Sends voter details + fingerprint template to Django API.

    The ISO template is converted to base64 before sending
    because HTTP JSON can't carry raw binary data directly.

    Returns True if enrolled successfully, False otherwise.
    """
    # Convert binary ISO template → base64 string for JSON
    template_b64 = base64.b64encode(iso_template_bytes).decode('utf-8')

    payload = {
        "voter_id": voter_id,
        "full_name": full_name,
        "fingerprint_template": template_b64
    }

    print(f"\n  Sending to backend...")
    print(f"  URL: {ENROLL_URL}")
    print(f"  Payload size: {len(template_b64)} chars (base64 template)")

    try:
        response = requests.post(ENROLL_URL, json=payload, timeout=10)

        if response.status_code == 201:
            data = response.json()
            print(f"  [OK] Backend response: {data.get('message')}")
            return True

        elif response.status_code == 409:
            print(f"  [ERROR] Voter {voter_id} already enrolled in database.")
            return False

        else:
            print(f"  [ERROR] Backend returned status {response.status_code}")
            print(f"  Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"  [ERROR] Cannot connect to Django at {DJANGO_API_BASE}")
        print("  → Is 'python manage.py runserver' running?")
        return False

    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}")
        return False


# ──────────────────────────────────────────────
# MAIN ENROLLMENT FLOW
# ──────────────────────────────────────────────

def run_enrollment():
    """
    Full enrollment session.
    Keeps enrolling voters until the officer types 'done'.
    """
    print("\n" + "="*50)
    print("  VeriVote — Voter Enrollment Station")
    print("  Phase 5: Biometric Enrollment")
    print("="*50)
    print(f"\n  Django Backend: {DJANGO_API_BASE}")

    # Check backend is reachable before starting
    try:
        requests.get(DJANGO_API_BASE, timeout=3)
        print("  [OK] Backend is reachable.")
    except Exception:
        print(f"  [ERROR] Cannot reach backend at {DJANGO_API_BASE}")
        print("  → Start Django server: python manage.py runserver")
        print("  → Or update DJANGO_API_BASE at top of enroll.py")
        return

    # Load scanner once — reuse for all enrollments
    print("\n  Initializing scanner...")
    mfs = load_dll()
    if mfs is None:
        print("  [ERROR] Could not load scanner DLL.")
        return

    if not init_scanner(mfs):
        print("  [ERROR] Could not initialize scanner.")
        return

    enrolled_count = 0

    while True:
        print("\n" + "="*50)

        # Step 1: Get voter details
        voter_id, full_name = get_voter_details()
        if voter_id is None:
            print("\n  Exiting enrollment.")
            break

        # Step 2: Check not already enrolled
        already = check_already_enrolled(voter_id)
        if already is None:
            # Connection error
            break
        if already:
            print(f"\n  [REJECTED] Voter {voter_id} is already enrolled.")
            print("  → Cannot enroll same voter twice.")
            continue

        # Step 3: Scan fingerprint
        print(f"\n  Ready to scan fingerprint for {full_name} ({voter_id})")
        iso_bytes = scan_fingerprint(mfs, voter_id)

        if iso_bytes is None:
            print("  [FAILED] Enrollment incomplete — fingerprint scan failed.")
            again = input("  Try again? (y/n): ").strip().lower()
            if again == 'y':
                continue
            else:
                break

        # Step 4: Send to backend
        success = send_to_backend(voter_id, full_name, iso_bytes)

        if success:
            enrolled_count += 1
            print(f"\n  ✅ ENROLLMENT COMPLETE!")
            print(f"  Voter {voter_id} ({full_name}) is now registered.")
            print(f"  Total enrolled this session: {enrolled_count}")
        else:
            print(f"\n  ❌ ENROLLMENT FAILED for {voter_id}.")

        # Ask if another voter to enroll
        another = input("\n  Enroll another voter? (y/n): ").strip().lower()
        if another != 'y':
            break

    close_scanner(mfs)

    print("\n" + "="*50)
    print(f"  Session complete. Enrolled {enrolled_count} voter(s).")
    print("="*50)


# ──────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────

if __name__ == "__main__":
    run_enrollment()