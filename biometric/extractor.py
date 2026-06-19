"""
VeriVote — Biometric Engine
File: biometric/extractor.py
Author: Person 1 (Aishhh)
Phase: 3 — Feature Extraction

What this file does:
1. Loads a captured fingerprint .bmp image
2. Converts to grayscale
3. Applies histogram equalization (improve contrast)
4. Resizes to 300x300
5. Uses ORB to extract keypoints and descriptors
6. Saves the descriptor as a .pkl file (for Phase 4 matching + Phase 5 enrollment)
7. Saves a debug image showing keypoints drawn on the fingerprint (visual check)
"""

import cv2
import pickle
import os
import numpy as np

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────

# Standard size we resize every fingerprint to before extraction
# This ensures consistent comparison regardless of scanner resolution
STANDARD_SIZE = (300, 300)

# Number of keypoints ORB will try to find
# 500 is a good balance — enough for reliable matching, not too slow
MAX_KEYPOINTS = 500

# Where extracted descriptors get saved
DESCRIPTOR_FOLDER = "descriptors"

# Where debug images (keypoints visualized) get saved
DEBUG_FOLDER = "debug_images"


# ──────────────────────────────────────────────
# STEP 1 — LOAD IMAGE
# ──────────────────────────────────────────────

def load_image(image_path):
    """
    Loads a fingerprint image from disk using OpenCV.

    OpenCV loads images as NumPy arrays — a 2D grid of pixel values (0-255).
    For a grayscale image, each pixel is a single number:
        0   = pure black (ridge valley)
        255 = pure white (ridge peak)

    Returns the image array, or None if loading failed.
    """
    if not os.path.exists(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        return None

    # cv2.IMREAD_GRAYSCALE loads directly as grayscale
    # even if the BMP was saved as color, this converts it
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        print(f"[ERROR] OpenCV could not read image: {image_path}")
        return None

    print(f"[OK] Image loaded: {image_path}")
    print(f"[INFO] Original size: {image.shape[1]}x{image.shape[0]} pixels")
    return image


# ──────────────────────────────────────────────
# STEP 2 — PREPROCESS IMAGE
# ──────────────────────────────────────────────

def preprocess_image(image):
    """
    Prepares the raw fingerprint image for feature extraction.

    Three steps:
    A) Grayscale check — should already be grayscale from load_image(),
       but we handle color images too just in case.

    B) Histogram equalization — redistributes pixel brightness values
       so the full 0-255 range is used. This makes ridges sharper.
       Think of it like "auto levels" in Photoshop.

    C) Resize to 300x300 — standardizes all images to the same size
       so descriptors are comparable regardless of scanner resolution.
       Your scanner gives 316x354, we normalize to 300x300.

    Returns the preprocessed image array.
    """

    # A) Ensure grayscale
    if len(image.shape) == 3:
        # Image has 3 channels (BGR color) — convert to grayscale
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        print("[INFO] Converted color image to grayscale.")
    else:
        print("[INFO] Image is already grayscale.")

    print(f"[INFO] Pixel value range before equalization: "
          f"min={image.min()}, max={image.max()}, mean={image.mean():.1f}")

    # B) Histogram equalization
    # equalizeHist() takes a grayscale image and stretches its histogram
    # so dark images become clearer and washed-out images get more contrast
    equalized = cv2.equalizeHist(image)

    print(f"[INFO] Pixel value range after equalization:  "
          f"min={equalized.min()}, max={equalized.max()}, mean={equalized.mean():.1f}")

    # C) Resize to standard size
    # cv2.INTER_CUBIC = high quality interpolation for shrinking/enlarging
    resized = cv2.resize(equalized, STANDARD_SIZE, interpolation=cv2.INTER_CUBIC)

    print(f"[OK] Preprocessed: grayscale → equalized → resized to {STANDARD_SIZE[0]}x{STANDARD_SIZE[1]}")
    return resized


# ──────────────────────────────────────────────
# STEP 3 — EXTRACT FEATURES WITH ORB
# ──────────────────────────────────────────────

def extract_features(image):
    """
    Uses ORB (Oriented FAST and Rotated BRIEF) to extract keypoints
    and descriptors from the preprocessed fingerprint image.

    How ORB works internally:
    1. FAST corner detector scans the image for "interesting" points
       (ridge bifurcations, endings, loops — high local contrast areas)
    2. For each keypoint, ORB assigns an orientation angle (rotation invariance)
    3. BRIEF descriptor: for each keypoint, ORB samples 256 pairs of pixels
       in the neighbourhood and records which is brighter (1 or 0)
       → this gives a 32-byte binary string per keypoint

    Returns (keypoints, descriptors) or (None, None) if extraction failed.
    """

    # Create ORB detector with MAX_KEYPOINTS
    # nfeatures = max keypoints to detect
    orb = cv2.ORB_create(nfeatures=MAX_KEYPOINTS)

    # Detect keypoints AND compute descriptors in one call
    # keypoints = list of cv2.KeyPoint objects (x, y, size, angle, response)
    # descriptors = NumPy array of shape (N, 32) where N = keypoints found
    keypoints, descriptors = orb.detectAndCompute(image, None)

    if descriptors is None or len(keypoints) == 0:
        print("[ERROR] ORB found no features — image may be too blurry or blank.")
        return None, None

    print(f"[OK] ORB extracted {len(keypoints)} keypoints.")
    print(f"[INFO] Descriptor shape: {descriptors.shape} "
          f"(={len(keypoints)} keypoints × 32 bytes each)")
    print(f"[INFO] Descriptor dtype: {descriptors.dtype} "
          f"(uint8 binary = correct for ORB)")

    return keypoints, descriptors


# ──────────────────────────────────────────────
# STEP 4 — SAVE DESCRIPTOR
# ──────────────────────────────────────────────

def save_descriptor(descriptors, voter_id="test"):
    """
    Saves the descriptor array to a .pkl (pickle) binary file.

    Why pickle?
    - Descriptors are NumPy arrays — pickle preserves their exact data type
    - Fast to save and load
    - In Phase 5, we'll serialize this further to send to the Django backend

    Returns filepath if saved successfully, None if failed.
    """
    os.makedirs(DESCRIPTOR_FOLDER, exist_ok=True)
    filepath = os.path.join(DESCRIPTOR_FOLDER, f"{voter_id}_descriptor.pkl")

    try:
        with open(filepath, "wb") as f:
            pickle.dump(descriptors, f)

        file_size = os.path.getsize(filepath)
        print(f"[OK] Descriptor saved: {filepath}")
        print(f"[INFO] File size: {file_size} bytes")
        return filepath

    except Exception as e:
        print(f"[ERROR] Could not save descriptor: {e}")
        return None


# ──────────────────────────────────────────────
# STEP 5 — SAVE DEBUG IMAGE (visual check)
# ──────────────────────────────────────────────

def save_debug_image(image, keypoints, voter_id="test"):
    """
    Draws the detected keypoints ON the fingerprint image and saves it.
    Each keypoint appears as a small circle.

    This is purely for visual verification during development.
    You should see circles scattered across ridge endings and bifurcations.
    NOT used in production.

    Returns filepath if saved, None if failed.
    """
    os.makedirs(DEBUG_FOLDER, exist_ok=True)
    filepath = os.path.join(DEBUG_FOLDER, f"{voter_id}_keypoints.bmp")

    try:
        # drawKeypoints draws circles at each keypoint location
        # cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS draws circles
        # proportional to keypoint size with orientation lines
        debug_image = cv2.drawKeypoints(
            image,
            keypoints,
            None,
            color=(0, 255, 0),  # green circles
            flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS
        )

        cv2.imwrite(filepath, debug_image)
        print(f"[OK] Debug image saved: {filepath}")
        print(f"[INFO] Open this image to visually verify keypoints are on ridges.")
        return filepath

    except Exception as e:
        print(f"[ERROR] Could not save debug image: {e}")
        return None


# ──────────────────────────────────────────────
# MAIN FUNCTION — called from other files
# ──────────────────────────────────────────────

def extract_and_save(image_path, voter_id="test"):
    """
    Full Phase 3 pipeline for one fingerprint image.

    Called from:
    - Phase 5 (enrollment): after capture, extract and send to backend
    - Phase 6 (verification): extract from live scan, then match against stored

    Parameters:
        image_path (str): Path to the .bmp fingerprint image
        voter_id   (str): Used to name saved files

    Returns:
        dict with keys:
            "descriptors"       → NumPy array (N, 32) — the actual feature data
            "descriptor_path"   → path to saved .pkl file
            "debug_image_path"  → path to keypoints visualization image
            "keypoint_count"    → how many keypoints were found
        Returns None if extraction failed.
    """

    print("=" * 55)
    print("  VeriVote — Feature Extraction (Phase 3)")
    print("=" * 55)

    # Step 1: Load
    image = load_image(image_path)
    if image is None:
        return None

    # Step 2: Preprocess
    processed = preprocess_image(image)

    # Step 3: Extract features
    keypoints, descriptors = extract_features(processed)
    if descriptors is None:
        return None

    # Step 4: Save descriptor
    descriptor_path = save_descriptor(descriptors, voter_id)

    # Step 5: Save debug image
    debug_path = save_debug_image(processed, keypoints, voter_id)

    print(f"\n[SUCCESS] Feature extraction complete!")
    print(f"  Keypoints found:  {len(keypoints)}")
    print(f"  Descriptor shape: {descriptors.shape}")
    print(f"  Descriptor saved: {descriptor_path}")
    print(f"  Debug image:      {debug_path}")
    print("=" * 55)

    return {
        "descriptors": descriptors,
        "descriptor_path": descriptor_path,
        "debug_image_path": debug_path,
        "keypoint_count": len(keypoints)
    }


# ──────────────────────────────────────────────
# RUN DIRECTLY FOR TESTING
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # Use the image captured in Phase 2 for testing
    # You can also pass a different path as a command line argument:
    #   python extractor.py path/to/image.bmp
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
    else:
        test_image = os.path.join("captured_fingerprints", "TEST001_attempt1.bmp")

    print(f"[INFO] Testing with image: {test_image}")

    result = extract_and_save(test_image, voter_id="TEST001")

    if result:
        print(f"\nExtraction test PASSED ✅")
        print(f"  Keypoints:   {result['keypoint_count']}")
        print(f"  Descriptor:  {result['descriptor_path']}")
        print(f"  Debug image: {result['debug_image_path']}")
        print(f"\nNext step: open {result['debug_image_path']} and verify")
        print("  circles appear on fingerprint ridges/bifurcations.")
    else:
        print("\nExtraction test FAILED ❌ — check errors above.")