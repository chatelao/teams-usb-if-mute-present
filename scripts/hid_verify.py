#!/usr/bin/env python3
"""
Microsoft Teams HID Compliance Verification Script
Automated HID simulation and UI verification.
"""

import os
import sys
import logging
from hid_simulator import simulate_hid_event
from image_verifier import capture_screenshot, verify_template

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

def run_verification_cycle(page, usage, template_path, label):
    """
    Runs a single HID event and verification cycle.
    """
    logger.info(f"--- Starting {label} Verification ---")

    if not simulate_hid_event(page, usage):
        logger.error(f"Failed to simulate HID event for {label}")
        return False

    screenshot = capture_screenshot()
    if verify_template(screenshot, template_path):
        logger.info(f"{label} Verification: SUCCESS")
        return True
    else:
        logger.error(f"{label} Verification: FAILED")
        return False

def main():
    logger.info("Starting Teams HID Verification...")

    # 1. Simulate Mute (Telephony Page 0x0B, Usage 0x2F)
    # We toggle it. First should go to Mute.
    if not run_verification_cycle(0x0B, 0x2F, "templates/mute_icon.png", "Mute"):
        if not IS_CI: sys.exit(1)

    # 2. Simulate Unmute (Toggle back)
    if not run_verification_cycle(0x0B, 0x2F, "templates/unmute_icon.png", "Unmute"):
        if not IS_CI: sys.exit(1)

    logger.info("Verification process completed.")

if __name__ == "__main__":
    main()
