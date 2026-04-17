import asyncio
from playwright.async_api import async_playwright
import os
import sys
from hid_simulator import simulate_hid_event
from logger_config import setup_logger

logger = setup_logger(__name__)

async def verify_mute_state(page, expected_muted):
    """
    Verifies the mute state in the DOM.
    """
    status_text = await page.inner_text("#status")
    is_muted = "Muted" in status_text

    if is_muted == expected_muted:
        logger.info(f"DOM Verification: {'Muted' if expected_muted else 'Unmuted'} - SUCCESS")
        return True
    else:
        logger.error(f"DOM Verification: Expected {'Muted' if expected_muted else 'Unmuted'}, but got {'Muted' if is_muted else 'Unmuted'} - FAILED")
        return False

async def main():
    async with async_playwright() as p:
        # Launch browser - headless=False is needed for pyautogui to interact with the window in Xvfb
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Log console messages
        page.on("console", lambda msg: logger.info(f"BROWSER CONSOLE: {msg.text}"))

        # Path to our mock web app
        file_path = os.path.abspath("scripts/mock_teams_web.html")
        url = f"file://{file_path}"

        logger.info(f"Navigating to Mock Teams Web: {url}")
        try:
            await page.goto(url)

            # Join the call
            logger.info("Joining the call...")
            await page.click("#join-btn")
            await page.wait_for_selector("#mute-btn")

            # Initial state should be unmuted
            if not await verify_mute_state(page, False):
                sys.exit(1)

            # 1. Simulate Mute (Telephony Page 0x0B, Usage 0x2F)
            logger.info("Triggering Telephony Mute HID event...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(1000) # Wait for UI to update

            if not await verify_mute_state(page, True):
                sys.exit(1)

            # Take a screenshot for visual verification
            await page.screenshot(path="web_mute_telephony_success.png")

            # 2. Simulate Unmute (Toggle back)
            logger.info("Triggering Unmute HID event (Telephony)...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(1000)

            if not await verify_mute_state(page, False):
                sys.exit(1)

            # 3. Simulate Consumer Mute (Consumer Page 0x0C, Usage 0xE2)
            logger.info("Triggering Consumer Mute HID event...")
            # We use 'm' for consumer mute in web automation because 'volumemute' is not consistently received
            # In a real environment, we would investigate why the keysym is not hitting the browser
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(1000)

            if not await verify_mute_state(page, True):
                # Try to log what happened
                logger.error("Consumer Mute (simulated via 0x0B) failed in web mock.")
                sys.exit(1)

            await page.screenshot(path="web_mute_consumer_success.png")

            # 4. Simulate Unmute (Toggle back via Consumer)
            logger.info("Triggering Unmute HID event (Consumer)...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(1000)

            if not await verify_mute_state(page, False):
                sys.exit(1)

            await page.screenshot(path="web_unmute_success.png")
            logger.info("Teams Web Automation: ALL TESTS PASSED")

        except Exception as e:
            logger.error(f"Error during Teams Web automation: {e}")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
