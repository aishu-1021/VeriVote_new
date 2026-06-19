"""
VeriVote — Phase 3 Multi-Person Test Script
File: biometric/test_multi_capture.py

FIX: Scan number is now based on files already on disk,
so rerunning the program never overwrites previous scans.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from capture import load_dll, init_scanner, capture_fingerprint, save_image, save_iso_template, close_scanner
from extractor import extract_and_save

CAPTURE_FOLDER = "captured_fingerprints"


def get_next_scan_number(person_id):
    """
    Checks the captured_fingerprints/ folder on disk and finds
    the next available scan number for this person_id.

    Example:
        AISHHH_scan1.bmp exists → returns 2
        AISHHH_scan1.bmp + AISHHH_scan2.bmp exist → returns 3
        Nothing exists → returns 1
    """
    os.makedirs(CAPTURE_FOLDER, exist_ok=True)
    existing = os.listdir(CAPTURE_FOLDER)

    scan_num = 1
    while f"{person_id}_scan{scan_num}.bmp" in existing:
        scan_num += 1

    return scan_num


def capture_one_person(mfs, person_id):
    scan_number = get_next_scan_number(person_id)
    file_label = f"{person_id}_scan{scan_number}"

    if scan_number > 1:
        print(f"\n  Note: {person_id} already has {scan_number - 1} scan(s). Saving as scan #{scan_number}.")

    print(f"\n{'=' * 55}")
    print(f"  Capturing: {person_id} (Scan #{scan_number})")
    print(f"{'=' * 55}")

    MAX_RETRIES = 3
    QUALITY_THRESHOLD = 60
    finger_data = None
    quality = 0

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n  Attempt {attempt} of {MAX_RETRIES}")
        finger_data, quality = capture_fingerprint(mfs, timeout_ms=15000)

        if finger_data is None:
            print("  [RETRY] Capture failed.")
            continue

        if quality < QUALITY_THRESHOLD:
            print(f"  [RETRY] Quality too low: {quality}/100 — try again.")
            finger_data = None
            continue

        break

    if finger_data is None:
        print(f"  [FAILED] Could not get good scan for {person_id}.")
        return None

    image_path = save_image(mfs, finger_data, f"{file_label}.bmp")
    save_iso_template(finger_data, file_label)

    if image_path is None:
        print(f"  [ERROR] Image save failed.")
        return None

    print(f"  [OK] Image saved: {image_path} (quality: {quality}/100)")

    print(f"\n  Extracting features...")
    result = extract_and_save(image_path, voter_id=file_label)

    if result is None:
        print(f"  [ERROR] Feature extraction failed.")
        return None

    print(f"  [OK] {result['keypoint_count']} keypoints extracted.")

    return {
        "person_id": person_id,
        "scan_number": scan_number,
        "file_label": file_label,
        "image_path": image_path,
        "quality": quality,
        "keypoint_count": result["keypoint_count"],
        "descriptor_path": result["descriptor_path"]
    }


def run_multi_test():
    print("\n" + "=" * 55)
    print("  VeriVote — Multi-Person Capture Test")
    print("  Phase 3: Test with at least 5 fingerprints")
    print("=" * 55)
    print("\nTip: Enter the same person ID across multiple runs")
    print("     and it will automatically save as scan2, scan3 etc.")
    print("     without overwriting previous scans.\n")

    mfs = load_dll()
    if mfs is None:
        print("[ERROR] Could not load scanner DLL.")
        return

    if not init_scanner(mfs):
        print("[ERROR] Could not initialize scanner.")
        return

    results = []

    while True:
        print("\n" + "-" * 40)

        # Show existing scans so user knows what's already saved
        if os.path.exists(CAPTURE_FOLDER):
            existing_bmps = [f for f in os.listdir(CAPTURE_FOLDER) if f.endswith(".bmp")]
            if existing_bmps:
                print(f"  Existing scans ({len(existing_bmps)} total): {', '.join(sorted(existing_bmps))}")

        person_id = input("Enter person ID (or 'done' to finish): ").strip().upper()

        if person_id in ("DONE", ""):
            break

        result = capture_one_person(mfs, person_id)

        if result:
            results.append(result)
            print(f"\n  ✅ {result['file_label']} saved successfully!")
        else:
            print(f"\n  ❌ Capture failed — try again.")

        again = input("\nScan another? (y/n): ").strip().lower()
        if again != 'y':
            break

    close_scanner(mfs)

    # ── Summary ────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  SESSION SUMMARY")
    print("=" * 55)

    if not results:
        print("No captures this session.")
    else:
        print(f"\n{'Person ID':<20} {'Scan#':<8} {'Quality':<10} {'Keypoints'}")
        print("-" * 55)
        for r in results:
            print(f"{r['person_id']:<20} {r['scan_number']:<8} {r['quality']:<10} {r['keypoint_count']}")
        print(f"\nThis session: {len(results)} capture(s)")

    # Show ALL scans ever saved (across all sessions)
    print("\n" + "-" * 55)
    print("  ALL SCANS ON DISK (all sessions combined)")
    print("-" * 55)
    if os.path.exists(CAPTURE_FOLDER):
        all_bmps = sorted([f for f in os.listdir(CAPTURE_FOLDER) if f.endswith(".bmp")])
        if all_bmps:
            for f in all_bmps:
                pkl = f.replace(".bmp", "_descriptor.pkl")
                has_descriptor = os.path.exists(os.path.join("descriptors", pkl))
                status = "✅ image + descriptor" if has_descriptor else "⚠️  image only (no descriptor)"
                print(f"  {f:<35} {status}")
            print(f"\nTotal: {len(all_bmps)} fingerprint(s) saved")
        else:
            print("  No scans found.")

    # Phase 3 checklist
    all_bmps = sorted([f for f in os.listdir(CAPTURE_FOLDER) if f.endswith(".bmp")]) if os.path.exists(CAPTURE_FOLDER) else []
    unique_people = len(set(f.rsplit("_scan", 1)[0] for f in all_bmps))
    people_with_multi = [p for p in set(f.rsplit("_scan", 1)[0] for f in all_bmps)
                         if sum(1 for f in all_bmps if f.startswith(p + "_scan")) >= 2]

    print("\n" + "-" * 55)
    print("  PHASE 3 CHECKLIST")
    print("-" * 55)
    print(f"  {'✅' if len(all_bmps) >= 5 else '⬜'} At least 5 images extracted ({len(all_bmps)}/5)")
    print(f"  {'✅' if unique_people >= 3 else '⬜'} At least 3 different people ({unique_people}/3)")
    print(f"  {'✅' if people_with_multi else '⬜'} Same finger scanned twice "
          f"({'done: ' + ', '.join(people_with_multi) if people_with_multi else 'scan same person twice!'})")


if __name__ == "__main__":
    run_multi_test()