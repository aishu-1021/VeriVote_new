"""
VeriVote — Biometric Engine
File: biometric/capture.py
Author: Person 1 (Aishhh)
Phase: 2 — Fingerprint Capture

FIX: Quality was reading as 0 because finger_data.Quality was being read
     before the FingerData object was populated by AutoCapture.
     Solution: Call MFS100GetQuality() directly on the mfs object AFTER
     capture, which reflects the last captured scan's quality score.
"""

import sys
import os

DLL_PATH = r"C:\Program Files\Mantra\MFS100\Driver\MFS100Test\MANTRA.MFS100.dll"
DLL_FOLDER = os.path.dirname(DLL_PATH)

OUTPUT_FOLDER = "captured_fingerprints"

QUALITY_THRESHOLD = 60
MAX_RETRIES = 3


def normalize_result(res):
    """AutoCapture sometimes returns a tuple (returncode, finger_data) — handle both cases."""
    if isinstance(res, tuple):
        return res[0], res[1] if len(res) > 1 else None
    return res, None


# ──────────────────────────────────────────────
# STEP 1 — LOAD DLL
# ──────────────────────────────────────────────

def load_dll():
    try:
        import clr

        if DLL_FOLDER not in sys.path:
            sys.path.append(DLL_FOLDER)

        clr.AddReference(DLL_PATH)
        from MANTRA import MFS100

        mfs = MFS100()
        print("[OK] MANTRA.MFS100 .NET assembly loaded successfully.")
        print(f"[INFO] SDK Version: {mfs.GetSDKVersion()}")
        return mfs

    except Exception as e:
        print(f"[ERROR] Failed to load .NET assembly: {e}")
        return None


# ──────────────────────────────────────────────
# STEP 2 — INITIALIZE SCANNER
# ──────────────────────────────────────────────

def init_scanner(mfs):
    try:
        if not mfs.IsConnected():
            print("[ERROR] Scanner is NOT connected. Check USB cable.")
            return False

        result = mfs.Init()
        code = result[0] if isinstance(result, tuple) else result

        if int(code) == 0:
            print("[OK] Scanner initialized successfully.")
            device_info = mfs.GetDeviceInfo()
            if device_info is not None:
                print(f"[INFO] Device:    {device_info.Make} {device_info.Model}")
                print(f"[INFO] Serial No: {device_info.SerialNo}")
                print(f"[INFO] Image Size:{device_info.Width} x {device_info.Height}")
            return True
        else:
            print(f"[ERROR] Init failed. Code: {code}")
            return False

    except Exception as e:
        print(f"[ERROR] Exception during Init: {e}")
        return False


# ──────────────────────────────────────────────
# STEP 3 — CAPTURE FINGERPRINT
# ──────────────────────────────────────────────

def capture_fingerprint(mfs, timeout_ms=30000):
    """
    Captures fingerprint and returns (finger_data, quality).

    THE KEY FIX IS HERE:
    After AutoCapture, we call mfs.GetLastQuality() or mfs.Quality
    instead of finger_data.Quality, because the FingerData object
    we passed in doesn't always get mutated in pythonnet's .NET bridge.

    We also try multiple ways to read quality to find what works
    with your specific SDK version.
    """
    print("\n[SCANNER] Place your finger on the scanner...")
    print(f"[INFO] Waiting up to {timeout_ms // 1000} seconds...")

    try:
        from MANTRA import FingerData

        finger_data = FingerData()

        # Call AutoCapture — returns (error_code, populated_finger_data) or just error_code
        raw_result = mfs.AutoCapture(finger_data, timeout_ms, False, True)
        code, returned_fd = normalize_result(raw_result)
        code = int(code)

        if code != 0:
            try:
                error_msg = mfs.GetErrorMsg(code)
            except:
                error_msg = "Unknown error"
            print(f"[ERROR] Capture failed. Code: {code} — {error_msg}")
            return None, 0

        # ── QUALITY READING — try all methods ──────────────────────────────
        # The SDK printed "MFS100AutoCapture Quality = 73" — that value is
        # accessible through one of these. We try all and pick the first non-zero.

        quality = 0

        # Method A: use the returned FingerData from the tuple (if it came back)
        if returned_fd is not None:
            try:
                q = int(returned_fd.Quality)
                if q > 0:
                    quality = q
                    print(f"[DEBUG] Quality from returned FingerData: {q}")
                    finger_data = returned_fd  # use the populated one
            except:
                pass

        # Method B: read from the finger_data we passed in (sometimes mutated)
        if quality == 0:
            try:
                q = int(finger_data.Quality)
                if q > 0:
                    quality = q
                    print(f"[DEBUG] Quality from passed FingerData: {q}")
            except:
                pass

        # Method C: call GetQuality() directly on mfs object (reflects last scan)
        if quality == 0:
            try:
                q = int(mfs.GetQuality())
                if q > 0:
                    quality = q
                    print(f"[DEBUG] Quality from mfs.GetQuality(): {q}")
            except:
                pass

        # Method D: MFS100GetQuality (alternate method name)
        if quality == 0:
            try:
                q = int(mfs.MFS100GetQuality())
                if q > 0:
                    quality = q
                    print(f"[DEBUG] Quality from mfs.MFS100GetQuality(): {q}")
            except:
                pass

        # Method E: read the Quality property directly on mfs
        if quality == 0:
            try:
                q = int(mfs.Quality)
                if q > 0:
                    quality = q
                    print(f"[DEBUG] Quality from mfs.Quality property: {q}")
            except:
                pass

        # Method F: scan all attributes of finger_data looking for quality
        if quality == 0:
            print("[DEBUG] Scanning finger_data attributes for quality...")
            try:
                for attr in dir(finger_data):
                    if 'qual' in attr.lower() or 'score' in attr.lower():
                        try:
                            val = getattr(finger_data, attr)
                            if callable(val):
                                val = val()
                            val = int(val)
                            print(f"[DEBUG]   finger_data.{attr} = {val}")
                            if val > 0:
                                quality = val
                        except:
                            pass
            except:
                pass

        print(f"[OK] Fingerprint captured! Quality: {quality}/100")
        return finger_data, quality

    except Exception as e:
        print(f"[ERROR] Exception during capture: {e}")
        return None, 0


# ──────────────────────────────────────────────
# STEP 4 — SAVE IMAGE
# ──────────────────────────────────────────────

def save_image(mfs, finger_data, filename="fingerprint.bmp"):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    filepath = os.path.join(OUTPUT_FOLDER, filename)

    # Method 1: SDK's RawToBitmapBytes
    try:
        raw_data = finger_data.RawData
        if raw_data is None:
            raise ValueError("RawData is None")

        bmp_bytes = mfs.RawToBitmapBytes(raw_data)
        with open(filepath, "wb") as f:
            f.write(bytes(bmp_bytes))
        print(f"[OK] Fingerprint BMP saved: {filepath}")
        return filepath

    except Exception as e1:
        print(f"[WARNING] Primary save failed: {e1} — trying Pillow fallback...")

    # Method 2: Pillow fallback
    try:
        from PIL import Image

        raw_data = finger_data.RawData
        if raw_data is None:
            print("[ERROR] RawData is None — cannot save image")
            return None

        raw_bytes = bytes(raw_data)
        finger_image = finger_data.FingerImage

        if finger_image is not None:
            width = finger_image.Width
            height = finger_image.Height
        else:
            width, height = 316, 354  # your scanner's actual resolution
            print(f"[WARNING] Using default dimensions {width}x{height}")

        img = Image.frombytes("L", (width, height), raw_bytes)
        img.save(filepath)
        print(f"[OK] Fingerprint image saved (Pillow): {filepath}")
        return filepath

    except Exception as e2:
        print(f"[ERROR] Both save methods failed: {e2}")
        return None


# ──────────────────────────────────────────────
# STEP 5 — SAVE ISO TEMPLATE
# ──────────────────────────────────────────────

def save_iso_template(finger_data, voter_id="test"):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    filepath = os.path.join(OUTPUT_FOLDER, f"{voter_id}_iso_template.bin")

    try:
        iso_template = finger_data.ISOTemplate
        if iso_template is None:
            print("[WARNING] ISO template is None — skipping template save")
            return None

        with open(filepath, "wb") as f:
            f.write(bytes(iso_template))

        print(f"[OK] ISO template saved: {filepath}")
        print(f"[INFO] Template size: {len(bytes(iso_template))} bytes")
        return filepath

    except Exception as e:
        print(f"[ERROR] Could not save ISO template: {e}")
        return None


# ──────────────────────────────────────────────
# STEP 6 — DISPLAY IMAGE
# ──────────────────────────────────────────────

def display_image(filepath):
    try:
        from PIL import Image
        img = Image.open(filepath)
        img.show()
        print("[OK] Image opened in viewer — verify it looks like a fingerprint.")
    except Exception as e:
        print(f"[WARNING] Could not open image: {e}")
        print(f"  → Open manually: {filepath}")


# ──────────────────────────────────────────────
# STEP 7 — CLOSE SCANNER
# ──────────────────────────────────────────────

def close_scanner(mfs):
    try:
        mfs.Uninit()
        print("[OK] Scanner closed cleanly.")
    except Exception as e:
        print(f"[WARNING] Could not close scanner: {e}")


# ──────────────────────────────────────────────
# MAIN FUNCTION
# ──────────────────────────────────────────────

def capture_and_save(voter_id="test"):
    """
    Full capture flow.

    Returns dict with image_path, template_path, iso_template, quality
    Returns None if all retries failed (caller should trigger OTP fallback).
    """
    print("=" * 55)
    print("  VeriVote — Fingerprint Capture")
    print("=" * 55)

    mfs = load_dll()
    if mfs is None:
        return None

    if not init_scanner(mfs):
        return None

    result_data = None
    attempt = 0

    while attempt < MAX_RETRIES:
        attempt += 1
        print(f"\n--- Attempt {attempt} of {MAX_RETRIES} ---")

        finger_data, quality = capture_fingerprint(mfs)

        if finger_data is None:
            print("[RETRY] Capture failed — trying again.")
            continue

        if quality < QUALITY_THRESHOLD:
            remaining = MAX_RETRIES - attempt
            print(f"[WARNING] Quality too low: {quality} < {QUALITY_THRESHOLD}")
            if remaining > 0:
                print(f"  → {remaining} attempt(s) remaining.")
                print("  → Tips: dry your finger, press firmly, center on scanner.")
            continue

        # Good quality — save everything
        image_path = save_image(mfs, finger_data, f"{voter_id}_attempt{attempt}.bmp")
        template_path = save_iso_template(finger_data, voter_id)

        iso_bytes = None
        try:
            iso_raw = finger_data.ISOTemplate
            if iso_raw is not None:
                iso_bytes = bytes(iso_raw)
        except Exception:
            pass

        if image_path:
            display_image(image_path)

        print(f"\n[SUCCESS] Capture complete!")
        print(f"  Quality:        {quality}/100")
        print(f"  Image saved:    {image_path}")
        print(f"  Template saved: {template_path}")
        print(f"  ISO template:   {len(iso_bytes) if iso_bytes else 0} bytes")

        result_data = {
            "image_path": image_path,
            "template_path": template_path,
            "iso_template": iso_bytes,
            "quality": quality,
            "finger_data": finger_data
        }
        break

    else:
        print("\n[FAILED] Could not get a good scan after 3 attempts.")
        print("  → OTP fallback should be triggered (Phase 7).")

    close_scanner(mfs)
    print("=" * 55)
    return result_data


# ──────────────────────────────────────────────
# RUN DIRECTLY FOR TESTING
# ──────────────────────────────────────────────

if __name__ == "__main__":
    result = capture_and_save(voter_id="TEST001")

    if result:
        print(f"\nCapture test PASSED ✅")
        print(f"  Image:    {result['image_path']}")
        print(f"  Template: {result['template_path']}")
        print(f"  Quality:  {result['quality']}/100")
        print(f"  ISO size: {len(result['iso_template']) if result['iso_template'] else 0} bytes")
    else:
        print("\nCapture test FAILED ❌ — check errors above.")
        print("  → If scanner detected but quality reads 0, run this debug command:")
        print("     python -c \"import clr,sys; sys.path.append(r'C:\\\\Program Files\\\\Mantra\\\\MFS100\\\\Driver\\\\MFS100Test'); clr.AddReference(r'C:\\\\Program Files\\\\Mantra\\\\MFS100\\\\Driver\\\\MFS100Test\\\\MANTRA.MFS100.dll'); from MANTRA import MFS100; mfs=MFS100(); print([m for m in dir(mfs) if 'qual' in m.lower() or 'Quality' in m])\"")