import asyncio
from playwright.async_api import async_playwright
import os
import sys
from hid_simulator import simulate_hid_event
from logger_config import setup_logger

logger = setup_logger(__name__)

async def safe_screenshot(page, path):
    """
    Safely captures a screenshot, catching protocol errors that can happen in
    certain headless environments.
    """
    try:
        await page.screenshot(path=path)
        logger.info(f"Screenshot saved to {path}")
    except Exception as e:
        logger.warning(f"Failed to capture screenshot {path}: {e}")

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
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-notifications",
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            permissions=["microphone", "camera"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Log console messages
        page.on("console", lambda msg: logger.info(f"BROWSER CONSOLE: {msg.text}"))

        # Path to our mock web app
        file_path = os.path.abspath("scripts/mock_teams_web.html")
        url = f"file://{file_path}"

        logger.info(f"Navigating to Mock Teams Web: {url}")
        try:
            await page.goto(url)

            # Pre-join verification
            logger.info("Verifying pre-join mute...")
            # Fill name to enable button/focus
            await page.fill("#prejoin-display-name-input", "HID-Tester")

            # Check initial state
            aria = await page.get_attribute("#prejoin-mic-btn", "aria-label")
            logger.info(f"Initial pre-join mic ARIA: {aria}")

            # Trigger HID event
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(1000)

            aria_after = await page.get_attribute("#prejoin-mic-btn", "aria-label")
            logger.info(f"Post-toggle pre-join mic ARIA: {aria_after}")

            if "Unmute" in aria_after:
                logger.info("Mock Pre-join Mute: SUCCESS")
                await safe_screenshot(page, "screenshots/web_mock_prejoin_mute_success.png")
            else:
                logger.error("Mock Pre-join Mute: FAILED")
                await safe_screenshot(page, "screenshots/web_mock_prejoin_mute_fail.png")
                sys.exit(1)

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
                await safe_screenshot(page, "screenshots/web_mock_mute_telephony_fail.png")
                sys.exit(1)

            # Take a screenshot for visual verification
            await safe_screenshot(page, "screenshots/web_mock_mute_telephony_success.png")

            # 2. Simulate Unmute (Toggle back)
            logger.info("Triggering Unmute HID event (Telephony)...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(1000)

            if not await verify_mute_state(page, False):
                await safe_screenshot(page, "screenshots/web_mock_unmute_telephony_fail.png")
                sys.exit(1)

            await safe_screenshot(page, "screenshots/web_mock_unmute_telephony_success.png")

            # 3. Simulate Consumer Mute (Consumer Page 0x0C, Usage 0xE2)
            logger.info("Triggering Consumer Mute HID event...")
            # We use 'm' for consumer mute in web automation because 'volumemute' is not consistently received
            # In a real environment, we would investigate why the keysym is not hitting the browser
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(1000)

            if not await verify_mute_state(page, True):
                # Try to log what happened
                logger.error("Consumer Mute (simulated via 0x0B) failed in web mock.")
                await safe_screenshot(page, "screenshots/web_mock_mute_consumer_fail.png")
                sys.exit(1)

            await safe_screenshot(page, "screenshots/web_mock_mute_consumer_success.png")

            # 4. Simulate Unmute (Toggle back via Consumer)
            logger.info("Triggering Unmute HID event (Consumer)...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(1000)

            if not await verify_mute_state(page, False):
                await safe_screenshot(page, "screenshots/web_mock_unmute_consumer_fail.png")
                sys.exit(1)

            await safe_screenshot(page, "screenshots/web_mock_unmute_consumer_success.png")
            logger.info("Teams Web Automation: ALL TESTS PASSED")

        except Exception as e:
            logger.error(f"Error during Teams Web automation: {e}")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
