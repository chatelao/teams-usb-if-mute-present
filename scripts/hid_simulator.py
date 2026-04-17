#!/usr/bin/env python3
"""
HID Simulation Module
Encapsulates logic for simulating USB HID events.
"""

import logging
import time
import pyautogui

logger = logging.getLogger(__name__)

def simulate_hid_event(page, usage):
    """
    Simulates a USB HID event.
    Uses pyautogui as fallback when uinput is not available.
    """
    logger.info(f"Simulating HID Event: Page={hex(page)}, Usage={hex(usage)}")

    try:
        # Implementation using pyautogui fallback
        if page == 0x0B and usage == 0x2F:
            logger.info("Emulating Telephony Mute (0x0B, 0x2F) via pyautogui...")
            # 'm' toggles mute in our mock UI and is a common Teams shortcut
            # 'volumemute' is the consumer page mute equivalent
            pyautogui.press('m')
            pyautogui.press('volumemute')
        elif page == 0x0C and usage == 0xE2:
            logger.info("Emulating Consumer Mute (0x0C, 0xE2) via pyautogui...")
            pyautogui.press('volumemute')
        else:
            logger.warning(f"Unsupported HID event: Page={hex(page)}, Usage={hex(usage)}")
            return False
    except Exception as e:
        logger.error(f"Error during pyautogui simulation: {e}")
        return False

    time.sleep(2)
    return True

if __name__ == "__main__":
    # Setup basic logging for standalone testing
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing HID Simulator...")
    simulate_hid_event(0x0B, 0x2F)
