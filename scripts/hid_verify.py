#!/usr/bin/env python3
"""
Microsoft Teams HID Compliance Verification Script
Automated HID simulation and UI verification.
"""

import os
import sys
import time
from hid_simulator import simulate_hid_event
from image_verifier import capture_screenshot, verify_template
from logger_config import setup_logger

# Environment Check
IS_CI = os.environ.get('CI') == 'true'

logger = setup_logger(__name__)

def run_verification_cycle(page, usage, template_path, label):
    """
    Runs a single HID event and verification cycle.
    """
    logger.info(f"--- Starting {label} Verification (Page={hex(page)}, Usage={hex(usage)}) ---")

    if not simulate_hid_event(page, usage):
        logger.error(f"Failed to simulate HID event for {label}")
        return False

    # Wait for UI to update (previously handled inside simulator)
    time.sleep(2)

    # Use descriptive name for screenshots in hid_verify
    screenshot_name = f"screenshots/desktop_{label.lower().replace(' ', '_')}.png"
    screenshot = capture_screenshot(screenshot_name)

    if verify_template(screenshot, template_path):
        logger.info(f"{label} Verification: SUCCESS")
        return True
    else:
        logger.error(f"{label} Verification: FAILED")
        return False

def main():
    logger.info("Starting Teams HID Verification...")

    # 1. Simulate Mute (Telephony Page 0x0B, Usage 0x2F)
    if not run_verification_cycle(0x0B, 0x2F, "templates/mute_icon.png", "Telephony Mute"):
        if not IS_CI: sys.exit(1)

    # 2. Simulate Unmute (Telephony Page 0x0B, Usage 0x2F) - Toggle back
    if not run_verification_cycle(0x0B, 0x2F, "templates/unmute_icon.png", "Telephony Unmute"):
        if not IS_CI: sys.exit(1)

    # 3. Simulate Mute (Consumer Page 0x0C, Usage 0xE2)
    if not run_verification_cycle(0x0C, 0xE2, "templates/mute_icon.png", "Consumer Mute"):
        if not IS_CI: sys.exit(1)

    # 4. Simulate Unmute (Consumer Page 0x0C, Usage 0xE2) - Toggle back
    if not run_verification_cycle(0x0C, 0xE2, "templates/unmute_icon.png", "Consumer Unmute"):
        if not IS_CI: sys.exit(1)

    logger.info("Verification process completed.")

if __name__ == "__main__":
    main()
