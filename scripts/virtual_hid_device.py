#!/usr/bin/env python3
"""
Virtual USB-HID Device Simulator using evdev/uinput.
This script demonstrates how to send real USB-HID commands for
Telephony and Consumer pages via the Linux kernel.
"""

import sys
import time
from logger_config import setup_logger

logger = setup_logger(__name__)

try:
    from evdev import UInput, ecodes as e
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    logger.warning("evdev not installed. Please run 'pip install evdev'")

def create_virtual_device():
    """
    Creates a virtual HID device.
    Returns the UInput object or None if creation fails.
    """
    if not EVDEV_AVAILABLE:
        return None

    # Capabilities: What keys can this device press?
    # KEY_MICMUTE maps to HID Telephony (0x0B, 0x2F)
    # KEY_MUTE maps to HID Consumer (0x0C, 0xE2)
    cap = {
        e.EV_KEY: [e.KEY_MICMUTE, e.KEY_MUTE]
    }

    try:
        ui = UInput(cap, name="Virtual-Teams-HID-Device", vendor=0x045e, product=0x0605)
        logger.info(f"Created virtual device: {ui}")
        return ui
    except Exception as ex:
        logger.error(f"Failed to create virtual device (check /dev/uinput permissions): {ex}")
        return None

def emit_event(ui, key_code):
    """
    Emits a key press and release event.
    """
    if ui is None:
        logger.error("No virtual device available to emit events.")
        return

    logger.info(f"Emitting HID event for key code: {key_code}")
    ui.write(e.EV_KEY, key_code, 1) # Press
    ui.write(e.EV_KEY, key_code, 0) # Release
    ui.syn()

def main():
    if len(sys.argv) < 2:
        print("Usage: virtual_hid_device.py [telephony|consumer]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    ui = create_virtual_device()

    if ui is None:
        logger.error("Exiting: Virtual device could not be initialized.")
        sys.exit(1)

    # Small delay to ensure device is registered by the OS
    time.sleep(1)

    if cmd == "telephony":
        emit_event(ui, e.KEY_MICMUTE)
    elif cmd == "consumer":
        emit_event(ui, e.KEY_MUTE)
    else:
        logger.error(f"Unknown command: {cmd}")
        sys.exit(1)

    # Keep alive for a moment to ensure OS processes the events
    time.sleep(0.5)
    ui.close()

if __name__ == "__main__":
    main()
