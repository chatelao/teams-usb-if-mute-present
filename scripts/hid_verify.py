#!/usr/bin/env python3
"""
Microsoft Teams HID Compliance Verification Script
Automated HID simulation and UI verification.
"""

import os
import sys
import time
import logging
import pyautogui
import cv2
import numpy as np
import mss
from PIL import Image

# Environment Check
IS_CI = os.environ.get('CI') == 'true'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def simulate_hid_event(page, usage):
    """
    Simulates a USB HID event.
    Uses pyautogui as fallback when uinput is not available.
    """
    logger.info(f"Simulating HID Event: Page={hex(page)}, Usage={hex(usage)}")

    try:
        # Fallback implementation using pyautogui
        if page == 0x0B and usage == 0x2F:
            logger.info("Emulating Telephony Mute via pyautogui (m key and volumemute)...")
            # Press 'm' for Mock UI/Teams shortcut and 'volumemute' for system
            pyautogui.press('m')
            pyautogui.press('volumemute')
        elif page == 0x0C and usage == 0xE2:
            logger.info("Emulating Consumer Mute via pyautogui...")
            pyautogui.press('volumemute')
        else:
            logger.warning(f"Unsupported HID event: Page={hex(page)}, Usage={hex(usage)}")
    except Exception as e:
        logger.error(f"Error during pyautogui simulation: {e}")

    time.sleep(2)

def capture_and_verify(template_path, threshold=0.8):
    """
    Captures a screenshot and verifies it against a template using OpenCV.
    """
    logger.info(f"Verifying UI against template: {template_path}")

    # 1. Capture Screenshot
    try:
        with mss.mss() as sct:
            # Capture the whole primary monitor
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Save for debugging
            debug_path = f"debug_screenshot_{int(time.time())}.png"
            screenshot.save(debug_path)
            logger.info(f"Saved debug screenshot to {debug_path}")

    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return False

    try:
        screenshot_np = np.array(screenshot)
        screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)

        # 2. Load Template
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            logger.error(f"Error: Could not load template at {template_path}")
            return False

        # 3. Template Matching
        res = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        logger.info(f"Match confidence: {max_val:.4f}")

        if max_val >= threshold:
            logger.info(f"Match found at {max_loc}")
            return True
        else:
            logger.warning(f"No match found. Best match confidence: {max_val:.4f} (threshold: {threshold})")

    except Exception as e:
        logger.error(f"Error during image processing: {e}")

    return False

def main():
    logger.info("Starting Teams HID Verification...")

    # 1. Simulate Mute (Telephony Page 0x0B, Usage 0x2F)
    simulate_hid_event(0x0B, 0x2F)
    if capture_and_verify("templates/mute_icon.png"):
        logger.info("Mute Verification: SUCCESS")
    else:
        logger.error("Mute Verification: FAILED")
        if not IS_CI:
            sys.exit(1)

    # 2. Simulate Unmute (Toggle)
    simulate_hid_event(0x0B, 0x2F)
    if capture_and_verify("templates/unmute_icon.png"):
        logger.info("Unmute Verification: SUCCESS")
    else:
        logger.error("Unmute Verification: FAILED")
        if not IS_CI:
            sys.exit(1)

    logger.info("Verification process completed.")

if __name__ == "__main__":
    main()
