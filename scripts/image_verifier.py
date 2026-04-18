#!/usr/bin/env python3
"""
Visual Verification Module
Handles screenshot capture and template matching.
"""

import logging
import time
import cv2
import numpy as np
import mss
from PIL import Image

logger = logging.getLogger(__name__)

def capture_screenshot(custom_path=None):
    """
    Captures a screenshot of the primary monitor.
    """
    try:
        with mss.mss() as sct:
            # Capture the whole primary monitor
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Save path
            if custom_path:
                save_path = custom_path
            else:
                save_path = f"screenshots/debug_screenshot_{int(time.time())}.png"

            screenshot.save(save_path)
            logger.info(f"Saved screenshot to {save_path}")
            return screenshot

    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return None

def verify_template(screenshot, template_path, threshold=0.8):
    """
    Verifies if a template exists within a screenshot.
    """
    if screenshot is None:
        return False

    logger.info(f"Verifying UI against template: {template_path}")

    try:
        screenshot_np = np.array(screenshot)
        screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)

        # Load Template
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            logger.error(f"Error: Could not load template at {template_path}")
            return False

        # Template Matching
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

if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing Image Verifier...")
    ss = capture_screenshot()
    if ss:
        logger.info("Screenshot captured successfully.")
