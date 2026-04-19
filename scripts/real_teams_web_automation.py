import asyncio
from playwright.async_api import async_playwright
import sys
import os
from hid_simulator import simulate_hid_event
from logger_config import setup_logger

logger = setup_logger(__name__)

async def safe_screenshot(page, path):
    """
    Attempts to capture a screenshot, logging a warning if it fails.
    """
    try:
        await page.screenshot(path=path)
    except Exception as e:
        logger.warning(f"Failed to capture screenshot at {path}: {e}")

async def verify_real_mute_state(page, expected_muted):
    """
    Verifies the mute state in the real Teams DOM.
    """
    try:
        mic_selectors = [
            "button[data-tid='microphone-button']",
            "button[aria-label^='Mute']",
            "button[aria-label^='Unmute']",
            "button[aria-label*='Stummschalt']",
            "button[aria-label*='Stummheben']",
            "button:has-text('Mute')",
            "button:has-text('Unmute')",
            "button:has-text('Stummschalt')"
        ]

        mic_button = None
        for sel in mic_selectors:
            try:
                found = page.locator(sel).first
                # Use a very short timeout for rapid polling
                if await found.is_visible(timeout=500):
                    mic_button = found
                    break
            except:
                continue

        if not mic_button:
            logger.error("Microphone button not found in UI")
            return False

        aria_label = await mic_button.get_attribute("aria-label")
        if not aria_label:
            aria_label = await mic_button.inner_text()

        logger.info(f"Microphone button state indicator: {aria_label}")

        label_lower = (aria_label or "").lower()
        # Teams Logic: "Unmute" (or German "aufheben") label means it IS currently muted.
        is_muted = "unmute" in label_lower or "aufheben" in label_lower or "stummheben" in label_lower

        if is_muted == expected_muted:
            logger.info(f"Real Teams Verification: {'Muted' if expected_muted else 'Unmuted'} - SUCCESS")
            return True
        else:
            logger.error(f"Real Teams Verification: Expected {'Muted' if expected_muted else 'Unmuted'}, but got {'Muted' if is_muted else 'Unmuted'} - FAILED")
            return False
    except Exception as e:
        logger.error(f"Error verifying mute state: {e}")
        return False

async def perform_login(page, user_creds):
    """
    Handles Microsoft Teams login flow.
    """
    try:
        if ":" not in user_creds:
            logger.error("Invalid TEAMS_USER format.")
            return False

        username, password = user_creds.split(":", 1)
        logger.info(f"Attempting login for user: {username}")

        # 1. Email/Username
        email_input = page.locator("input[type='email'], input[name='loginfmt']")
        await email_input.wait_for(state="visible", timeout=15000)
        await email_input.fill(username)
        await page.locator("input[type='submit'], #idSIButton9").click()

        # 2. Password
        pass_input = page.locator("input[type='password'], input[name='passwd']")
        await pass_input.wait_for(state="visible", timeout=15000)
        await pass_input.fill(password)
        await page.locator("input[type='submit'], #idSIButton9").click()

        # 3. Stay signed in?
        try:
            stay_btn = page.locator("#idSIButton9, input[type='submit']")
            await stay_btn.wait_for(state="visible", timeout=10000)
            await stay_btn.click()
        except:
            pass

        return True
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return False

async def main():
    meeting_url = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "https://teams.microsoft.com/v2/"
    user_creds = os.environ.get("TEAMS_USER")

    async with async_playwright() as p:
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

        await context.grant_permissions(["microphone", "camera"], origin="https://teams.microsoft.com")

        page = await context.new_page()
        # Ensure no operation waits longer than 30s as requested
        page.set_default_timeout(30000)
        page.on("dialog", lambda dialog: dialog.accept())

        logger.info(f"Navigating to Teams: {meeting_url}")
        await page.goto(meeting_url, timeout=30000)

        start_time = asyncio.get_event_loop().time()
        max_duration = 300 # Overall timeout
        mic_button_sel = "button[data-tid='microphone-button'], button[aria-label^='Mute'], button[aria-label^='Unmute'], button[aria-label*='Stummschalt'], button[aria-label*='Stummheben']"

        while (asyncio.get_event_loop().time() - start_time) < max_duration:
            try:
                current_url = page.url
                page_title = await page.title()
                logger.info(f"Current Page: {page_title} ({current_url})")

                # Check for target microphone button - this is our priority
                mic_btn = page.locator(mic_button_sel).first
                if await mic_btn.is_visible(timeout=500):
                    logger.info("Microphone button detected! Target UI reached.")
                    await safe_screenshot(page, "screenshots/real_teams_ready.png")
                    break

                # 1. Handle Microsoft Login
                if "login.microsoftonline.com" in current_url and user_creds:
                    logger.info("Login page detected.")
                    if not await perform_login(page, user_creds):
                        await page.wait_for_timeout(2000)
                    continue

                # 2. Handle Launcher Page
                launcher_selectors = [
                    "button:has-text('Continue on this browser')",
                    "button:has-text('Webversion verwenden')",
                    "button:has-text('browser instead')",
                    "[data-tid='joinOnWeb']"
                ]
                found_launcher = False
                for sel in launcher_selectors:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=500):
                        logger.info(f"Launcher detected ({sel}). Clicking.")
                        await btn.evaluate("node => node.click()")
                        found_launcher = True
                        break
                if found_launcher:
                    await page.wait_for_timeout(3000)
                    continue

                # 3. Handle Pre-join Screen Name Entry (ONLY if mic button NOT visible)
                # Note: We prioritize the mic button check at the top of the loop.
                name_input = page.locator("input[data-tid='prejoin-display-name-input'], #prejoin-display-name-input").first
                if await name_input.is_visible(timeout=500):
                    logger.info("Name input visible. Filling guest name...")
                    await name_input.fill("HID-Compliance-Tester")
                    await page.wait_for_timeout(2000)

                # 4. Handle Intermediate Prompts
                prompts = ["button:has-text('Allow')", "button:has-text('Got it')", "button:has-text('OK')", "button:has-text('Zulassen')"]
                found_prompt = False
                for p_sel in prompts:
                    btn = page.locator(p_sel).first
                    if await btn.is_visible(timeout=500):
                        logger.info(f"Clicking intermediate prompt: {p_sel}")
                        await btn.click()
                        found_prompt = True
                        break
                if found_prompt:
                    continue

                logger.info("Waiting for target UI state transition...")
                await page.wait_for_timeout(3000)
            except Exception as loop_err:
                logger.warning(f"Loop iteration error: {loop_err}")
                await page.wait_for_timeout(2000)
        else:
            logger.error("Timed out waiting for target UI (Microphone button).")
            await safe_screenshot(page, "screenshots/real_teams_timeout.png")
            sys.exit(1)

        # ----------------------------------------------------------------------
        # HID Standard Compliance Verification
        # ----------------------------------------------------------------------
        try:
            # Re-verify mic button presence
            mic_button = page.locator(mic_button_sel).first
            aria_label = await mic_button.get_attribute("aria-label")
            label_lower = (aria_label or "").lower()
            is_initial_muted = "unmute" in label_lower or "aufheben" in label_lower or "stummheben" in label_lower
            logger.info(f"Initial state: {'Muted' if is_initial_muted else 'Unmuted'} (Label: {aria_label})")

            # 1. Trigger Mute Toggle
            logger.info("Triggering HID Telephony Mute event (0x0B, 0x2F)...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(5000)

            if not await verify_real_mute_state(page, not is_initial_muted):
                logger.error("HID Mute verification failed on Teams UI.")
                await safe_screenshot(page, "screenshots/real_teams_mute_fail.png")
                sys.exit(1)
            else:
                logger.info("HID Mute verification SUCCESS on Teams UI.")
                await safe_screenshot(page, "screenshots/real_teams_mute_success.png")

            # 2. Trigger Toggle back (Unmute)
            logger.info("Triggering HID event again to toggle back...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(5000)

            if not await verify_real_mute_state(page, is_initial_muted):
                logger.error("HID Unmute toggle failed on Teams UI.")
                await safe_screenshot(page, "screenshots/real_teams_unmute_fail.png")
                sys.exit(1)
            else:
                logger.info("HID Unmute toggle SUCCESS on Teams UI.")

            logger.info("Real Teams HID Compliance Verification: COMPLETED SUCCESSFULLY")

        except Exception as e:
            logger.error(f"Error during HID verification: {e}")
            await safe_screenshot(page, "screenshots/real_teams_error_final.png")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
