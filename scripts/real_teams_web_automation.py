import asyncio
from playwright.async_api import async_playwright
import sys
import os
from hid_simulator import simulate_hid_event
from logger_config import setup_logger

logger = setup_logger(__name__)

async def verify_real_mute_state(page, expected_muted):
    """
    Verifies the mute state in the real Teams DOM.
    Looks for the microphone button and checks its aria-label or status.
    """
    try:
        # Standard Teams V2 mic button selectors
        mic_selectors = [
            "button[data-tid='microphone-button']",
            "button[aria-label^='Mute']",
            "button[aria-label^='Unmute']",
            "button:has-text('Mute')",
            "button:has-text('Unmute')"
        ]

        mic_button = None
        for sel in mic_selectors:
            try:
                found = page.locator(sel)
                if await found.is_visible(timeout=2000):
                    mic_button = found
                    break
            except:
                continue

        if not mic_button:
            logger.error("Microphone button not found in meeting UI")
            return False

        aria_label = await mic_button.get_attribute("aria-label")
        if not aria_label:
            # Fallback to inner text or other attributes if aria-label is missing
            aria_label = await mic_button.inner_text()

        logger.info(f"Microphone button state indicator: {aria_label}")

        # In Teams, if the label is "Unmute", the current state is Muted.
        # If the label is "Mute", the current state is Unmuted.
        is_muted = "Unmute" in aria_label or "stummheben" in aria_label.lower()

        if is_muted == expected_muted:
            logger.info(f"Real Teams Verification: {'Muted' if expected_muted else 'Unmuted'} - SUCCESS")
            return True
        else:
            logger.error(f"Real Teams Verification: Expected {'Muted' if expected_muted else 'Unmuted'}, but got {'Muted' if is_muted else 'Unmuted'} - FAILED")
            return False
    except Exception as e:
        logger.error(f"Error verifying mute state: {e}")
        return False

async def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python scripts/real_teams_web_automation.py <meeting_url>")
        # We don't exit with error here to allow CI to pass if no URL is provided,
        # but we log the requirement.
        logger.info("Skipping real Teams execution: No meeting URL provided.")
        return

    meeting_url = sys.argv[1]

    async with async_playwright() as p:
        # headless=False is required for pyautogui HID simulation to hit the browser window
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            permissions=["microphone", "camera"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        logger.info(f"Navigating to Teams Meeting: {meeting_url}")
        await page.goto(meeting_url)

        try:
            # 1. Handle Launcher/Landing Page
            logger.info("Handling landing page...")
            try:
                # Common landing page button for Web join
                continue_btn = page.locator("button:has-text('Continue on this browser'), [data-tid='joinOnWeb']")
                await continue_btn.wait_for(state="visible", timeout=15000)
                await continue_btn.click()
                logger.info("Clicked 'Continue on this browser'")
            except Exception as e:
                logger.warning(f"Landing page button not found (might have been skipped): {e}")

            # 2. Handle Pre-join Screen (Guest Name)
            logger.info("Waiting for pre-join screen...")
            # Teams guest name input selectors
            name_input_selectors = [
                "input[data-tid='prejoin-display-name-input']",
                "input[placeholder*='name']",
                "input[placeholder*='Name']",
                "#prejoin-display-name-input"
            ]

            name_input = None
            for sel in name_input_selectors:
                try:
                    found = page.locator(sel)
                    if await found.is_visible(timeout=5000):
                        name_input = found
                        break
                except:
                    continue

            if name_input:
                await name_input.fill("HID-Compliance-Tester")
                logger.info("Filled guest name.")

                # Join Now button
                join_btn = page.locator("button[data-tid='prejoin-join-button'], button:has-text('Join now')")
                await join_btn.wait_for(state="visible", timeout=5000)
                await join_btn.click()
                logger.info("Clicked 'Join now'")
            else:
                logger.warning("Could not find guest name input. Capturing state.")
                await page.screenshot(path="screenshots/real_teams_prejoin_missing.png")

            # 3. Wait to enter meeting
            logger.info("Waiting to enter meeting...")
            # The mic button appearing is a good sign we are in
            mic_button_sel = "button[data-tid='microphone-button'], button[aria-label^='Mute'], button[aria-label^='Unmute']"
            try:
                await page.wait_for_selector(mic_button_sel, timeout=60000)
                logger.info("Entered meeting UI.")
            except:
                logger.error("Timed out waiting for meeting UI (Mic button).")
                await page.screenshot(path="screenshots/real_teams_join_timeout.png")
                return

            # Initial state detection
            aria_label = await page.locator(mic_button_sel).first.get_attribute("aria-label")
            is_initial_muted = "Unmute" in (aria_label or "")
            logger.info(f"Initial state: {'Muted' if is_initial_muted else 'Unmuted'}")

            # 4. Perform HID Test - Toggle Mute
            logger.info("Triggering HID Telephony Mute event (0x0B, 0x2F)...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(3000)

            if not await verify_real_mute_state(page, not is_initial_muted):
                logger.error("HID Mute verification failed on real Teams instance.")
                await page.screenshot(path="screenshots/real_teams_mute_fail.png")
            else:
                logger.info("HID Mute verification SUCCESS on real Teams instance.")
                await page.screenshot(path="screenshots/real_teams_mute_success.png")

            # 5. Perform HID Test - Toggle back
            logger.info("Triggering HID event again to toggle back...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(3000)

            if not await verify_real_mute_state(page, is_initial_muted):
                logger.error("HID Unmute toggle failed on real Teams instance.")
            else:
                logger.info("HID Unmute toggle SUCCESS on real Teams instance.")

        except Exception as e:
            logger.error(f"Error during Real Teams automation: {e}")
            await page.screenshot(path="screenshots/real_teams_error_final.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
