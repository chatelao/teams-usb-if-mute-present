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
        # Standard Teams V2 and Light-meeting mic button selectors
        mic_selectors = [
            "button[data-tid='microphone-button']",
            "button[aria-label*='Mute' i]",
            "button[aria-label*='Unmute' i]",
            "button[aria-label*='Stumm' i]",
            "button[aria-label*='Micro' i]",
            "button:has-text('Mute')",
            "button:has-text('Unmute')"
        ]

        mic_button = None
        for sel in mic_selectors:
            try:
                found = page.locator(sel)
                if await found.count() > 0:
                    for i in range(await found.count()):
                        btn = found.nth(i)
                        if await btn.is_visible():
                            mic_button = btn
                            break
                if mic_button: break
            except:
                continue

        if not mic_button:
            logger.error("Microphone button not found in meeting UI")
            return False

        aria_label = await mic_button.get_attribute("aria-label") or ""
        inner_text = await mic_button.inner_text() or ""

        logger.info(f"Microphone button: aria='{aria_label}', text='{inner_text}'")

        # Logic: If the action is "Unmute" or "Stummschaltung aufheben", it is currently MUTED.
        is_muted = any(term in aria_label.lower() or term in inner_text.lower()
                       for term in ["unmute", "aufheben", "stummgeschaltet", "muted", "freischalten"])

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
    meeting_url = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "https://teams.microsoft.com/v2/"
    user_creds = os.environ.get("TEAMS_USER")

    if meeting_url == "https://teams.microsoft.com/v2/":
        logger.info("No meeting URL provided. Defaulting to Teams Web Portal. Note: This usually requires login.")
    else:
        logger.info(f"Using meeting URL: {meeting_url}")

    async with async_playwright() as p:
        # headless=False is preferred for pyautogui interaction in Xvfb.
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

        logger.info(f"Navigating to Teams Meeting: {meeting_url}")
        try:
            await page.goto(meeting_url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.error(f"Initial navigation failed: {e}")

        await page.wait_for_timeout(5000)
        await page.screenshot(path="screenshots/real_teams_initial_load.png")

        try:
            # 1. Handle Launcher/Landing Page (The "How do you want to join?" screen)
            logger.info("Checking for landing page / launcher...")
            launcher_selectors = [
                "button:has-text('Continue on this browser')",
                "button:has-text('Im Browser fortfahren')",
                "button:has-text('Browser')",
                "button:has-text('continue')",
                "[data-tid='joinOnWeb']",
                "button[aria-label*='browser' i]",
                "button[aria-label*='Browser' i]",
                "div[role='button']:has-text('browser' i)",
                "a:has-text('browser' i)"
            ]

            for _ in range(5):
                launcher_btn = None
                for sel in launcher_selectors:
                    try:
                        found = page.locator(sel)
                        if await found.count() > 0 and await found.first.is_visible():
                            launcher_btn = found.first
                            break
                    except:
                        continue

                if launcher_btn:
                    btn_text = (await launcher_btn.inner_text()).strip()
                    logger.info(f"Found launcher button: '{btn_text}'. Clicking...")
                    await launcher_btn.click()
                    # JavaScript fallback click
                    await page.evaluate("btn => btn.click()", await launcher_btn.element_handle())
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path="screenshots/real_teams_after_launcher.png")
                    break
                else:
                    logger.info("Waiting for launcher button to appear...")
                    await page.wait_for_timeout(3000)
            else:
                logger.info("No launcher button detected after retries or already passed.")

            # 2. Handle Pre-join / Guest Join Flow
            name_filled = False
            mic_button_found = False

            for attempt in range(20):
                url = page.url
                title = await page.title()
                logger.info(f"Attempt {attempt+1}: Page='{title}', URL='{url}'")

                # Check for Sign-in redirect
                if "login.microsoftonline.com" in url or "login.live.com" in url:
                    logger.error("Redirected to a Sign-in page. This meeting likely requires an account or the guest link is invalid.")
                    await page.screenshot(path="screenshots/real_teams_signin_blocked.png")
                    break

                # Check if we are ALREADY in the meeting
                mic_btn_sel = "button[data-tid='microphone-button'], button[aria-label*='Mute' i], button[aria-label*='Stumm' i]"
                if await page.locator(mic_btn_sel).count() > 0 and await page.locator(mic_btn_sel).first.is_visible():
                    logger.info("Detected Meeting UI.")
                    mic_button_found = True
                    break

                # Check for Lobby
                lobby_indicators = ["let you in soon", "einlässt", "Lobby", "Warteraum"]
                in_lobby = False
                for indicator in lobby_indicators:
                    if await page.locator(f"text='{indicator}'").count() > 0:
                        logger.info(f"Detected Lobby (Indicator: '{indicator}'). Waiting...")
                        await page.screenshot(path="screenshots/real_teams_lobby_state.png")
                        in_lobby = True
                        break
                if in_lobby:
                    await page.wait_for_timeout(5000)
                    continue

                # Handle Name Input (Guest Join)
                if not name_filled:
                    name_input_selectors = [
                        "input[data-tid='prejoin-display-name-input']",
                        "input[id='prejoin-display-name-input']",
                        "input[aria-label*='name' i]",
                        "input[placeholder*='name' i]",
                        "input[placeholder*='Name' i]"
                    ]
                    for sel in name_input_selectors:
                        found = page.locator(sel)
                        if await found.count() > 0 and await found.first.is_visible():
                            logger.info(f"Name input visible ({sel}). Filling...")
                            await found.first.fill("HID-Compliance-Tester")
                            name_filled = True
                            await page.wait_for_timeout(1000)
                            await page.screenshot(path="screenshots/real_teams_prejoin_filled.png")
                            break

                # Handle Join Button
                join_btn_selectors = [
                    "button[data-tid='prejoin-join-button']",
                    "button:has-text('Join now')",
                    "button:has-text('Jetzt teilnehmen')",
                    "button:has-text('Teilnehmen')",
                    "button[aria-label*='Join' i]",
                    "button[aria-label*='Teilnehmen' i]",
                    "button[type='submit']"
                ]
                for sel in join_btn_selectors:
                    found = page.locator(sel)
                    if await found.count() > 0 and await found.first.is_visible():
                        btn_label = await found.first.inner_text() or await found.first.get_attribute("aria-label")
                        logger.info(f"Join button visible: '{btn_label}'. Clicking...")
                        await found.first.click()
                        # JS click fallback
                        await page.evaluate("btn => btn.click()", await found.first.element_handle())
                        await page.wait_for_timeout(5000)
                        await page.screenshot(path="screenshots/real_teams_after_join_click.png")
                        break

                await page.wait_for_timeout(4000)
                logger.info("Waiting for target UI state transition...")

            if not mic_button_found:
                logger.error("Timed out waiting for Meeting UI (Microphone button).")
                await page.screenshot(path="screenshots/real_teams_final_failure.png")
                return

            # 3. Perform HID Test - Toggle Mute
            # Initial state detection
            mic_btn_sel = "button[data-tid='microphone-button'], button[aria-label*='Mute' i], button[aria-label*='Stumm' i]"
            aria_label = await page.locator(mic_btn_sel).first.get_attribute("aria-label") or ""
            is_initial_muted = any(term in aria_label.lower() for term in ["unmute", "aufheben", "stummgeschaltet"])
            logger.info(f"Initial state: {'Muted' if is_initial_muted else 'Unmuted'}")

            logger.info("Triggering HID Telephony Mute event (0x0B, 0x2F)...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(3000)

            if not await verify_real_mute_state(page, not is_initial_muted):
                logger.error("HID Mute verification failed on real Teams instance.")
                await page.screenshot(path="screenshots/real_teams_mute_fail.png")
            else:
                logger.info("HID Mute verification SUCCESS on real Teams instance.")
                await page.screenshot(path="screenshots/real_teams_mute_success.png")

            # 4. Perform HID Test - Toggle back
            logger.info("Triggering HID event again to toggle back...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(3000)

            if not await verify_real_mute_state(page, is_initial_muted):
                logger.error("HID Unmute toggle failed on real Teams instance.")
            else:
                logger.info("HID Unmute toggle SUCCESS on real Teams instance.")

        except Exception as e:
            logger.error(f"Error during Real Teams automation: {e}")
            await page.screenshot(path="screenshots/real_teams_critical_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
