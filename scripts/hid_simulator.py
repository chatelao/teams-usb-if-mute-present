#!/usr/bin/env python3
"""
HID Simulation Module
Encapsulates logic for simulating USB HID events.
"""

import time
import os
try:
    import pyautogui
except ImportError:
    pyautogui = None

from logger_config import setup_logger

logger = setup_logger(__name__)

# Supported HID Events
SUPPORTED_EVENTS = {
    (0x0B, 0x2F): "Telephony Mute",
    (0x0C, 0xE2): "Consumer Mute"
}

def simulate_hid_event(page, usage):
    """
    Simulates a USB HID event.
    Uses pyautogui as fallback when uinput is not available.

    Args:
        page (int): HID Usage Page
        usage (int): HID Usage ID
    """
    if (page, usage) not in SUPPORTED_EVENTS:
        logger.warning(f"Unsupported HID event requested: Page={hex(page)}, Usage={hex(usage)}")
        return False

    event_name = SUPPORTED_EVENTS[(page, usage)]
    logger.info(f"Simulating HID Event: {event_name} (Page={hex(page)}, Usage={hex(usage)})")

    if pyautogui is None:
        logger.error("pyautogui is not installed. Cannot simulate HID events.")
        return False

    # Check for DISPLAY environment variable
    if 'DISPLAY' not in os.environ:
        logger.error("DISPLAY environment variable not set. pyautogui requires a X11 session.")
        return False

    try:
        # Implementation using pyautogui fallback
        if page == 0x0B and usage == 0x2F:
            logger.info("Emulating Telephony Mute (0x0B, 0x2F) via pyautogui press('m')...")
            pyautogui.press('m')
        elif page == 0x0C and usage == 0xE2:
            logger.info("Emulating Consumer Mute (0x0C, 0xE2) via pyautogui press('volumemute')...")
            pyautogui.press('volumemute')

    except Exception as e:
        logger.error(f"Error during pyautogui simulation of {event_name}: {e}")
        return False

    # Short delay to allow UI to process the event
    time.sleep(2)
    return True

if __name__ == "__main__":
    logger.info("Testing HID Simulator standalone...")
    # Test valid event
    simulate_hid_event(0x0B, 0x2F)
    # Test invalid event
    simulate_hid_event(0xFF, 0xFF)
