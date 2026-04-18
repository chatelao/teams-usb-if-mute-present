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
    Prevents script termination due to environment-specific protocol errors.
    """
    try:
        await page.screenshot(path=path)
    except Exception as e:
        logger.warning(f"Failed to capture screenshot at {path}: {e}")

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
            "button[aria-label*='Stummschalt']",
            "button:has-text('Mute')",
            "button:has-text('Unmute')"
        ]

        mic_button = None
        for sel in mic_selectors:
            try:
                found = page.locator(sel).first
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
            aria_label = await mic_button.inner_text()

        logger.info(f"Microphone button state indicator: {aria_label}")

        # Teams Logic: "Unmute" (or German "aufheben") label means it IS currently muted.
        label_lower = (aria_label or "").lower()
        is_muted = "unmute" in label_lower or "aufheben" in label_lower

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
    Handles Microsoft Teams login flow using TEAMS_USER secret.
    Expected format: "username:password"
    """
    try:
        if ":" not in user_creds:
            logger.error("Invalid TEAMS_USER format. Expected 'username:password'")
            return False

        username, password = user_creds.split(":", 1)
        logger.info(f"Attempting login for user: {username}")

        # 1. Email/Username
        email_input = page.locator("input[type='email'], input[name='loginfmt']")
        await email_input.wait_for(state="visible", timeout=30000)
        await email_input.fill(username)
        await page.locator("input[type='submit'], #idSIButton9").click()
        logger.info("Username submitted.")

        # 2. Password
        pass_input = page.locator("input[type='password'], input[name='passwd']")
        await pass_input.wait_for(state="visible", timeout=30000)
        await pass_input.fill(password)
        await page.locator("input[type='submit'], #idSIButton9").click()
        logger.info("Password submitted.")

        # 3. Handle 'Stay signed in?'
        try:
            stay_btn = page.locator("#idSIButton9, input[type='submit']")
            await stay_btn.wait_for(state="visible", timeout=10000)
            await stay_btn.click()
            logger.info("Handled 'Stay signed in' prompt.")
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
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            permissions=["microphone", "camera"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        logger.info(f"Navigating to Teams: {meeting_url}")
        await page.goto(meeting_url)

        # Setup loop
        start_time = asyncio.get_event_loop().time()
        max_duration = 300
        mic_button_sel = "button[data-tid='microphone-button'], button[aria-label^='Mute'], button[aria-label^='Unmute'], button[aria-label*='Stummschalt']"

        while (asyncio.get_event_loop().time() - start_time) < max_duration:
            current_url = page.url
            logger.info(f"Current Page: {await page.title()} ({current_url})")

            # 1. Login
            if "login.microsoftonline.com" in current_url and user_creds:
                if not await perform_login(page, user_creds):
                    await page.wait_for_timeout(5000)
                continue

            # 2. Launcher
            continue_btn = page.locator("button:has-text('Continue on this browser'), [data-tid='joinOnWeb']")
            if await continue_btn.is_visible():
                logger.info("Landing page detected. Clicking 'Continue on this browser'.")
                await safe_screenshot(page, "screenshots/real_teams_landing_page.png")
                await continue_btn.click()
                await page.wait_for_timeout(5000)
                continue

            # 3. Pre-join
            name_input = page.locator("input[data-tid='prejoin-display-name-input'], #prejoin-display-name-input")
            if await name_input.is_visible():
                logger.info("Pre-join screen detected. Filling name.")
                await name_input.fill("HID-Compliance-Tester")
                await page.locator("button[data-tid='prejoin-join-button'], button:has-text('Join now')").click()
                await page.wait_for_timeout(5000)
                continue

            # 4. In Meeting?
            if await page.locator(mic_button_sel).first.is_visible():
                logger.info("Meeting UI reached.")
                await safe_screenshot(page, "screenshots/real_teams_meeting_ui.png")
                break

            await page.wait_for_timeout(5000)
        else:
            logger.error("Timed out waiting to reach meeting UI.")
            await safe_screenshot(page, "screenshots/real_teams_setup_timeout.png")
            sys.exit(1)

        # Start HID verification
        try:
            mic_button = page.locator(mic_button_sel).first
            aria_label = await mic_button.get_attribute("aria-label")
            label_lower = (aria_label or "").lower()
            is_initial_muted = "unmute" in label_lower or "aufheben" in label_lower
            logger.info(f"Initial state: {'Muted' if is_initial_muted else 'Unmuted'} (Label: {aria_label})")

            # Mute toggle
            logger.info("Triggering HID Mute (0x0B, 0x2F)...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(5000)

            if not await verify_real_mute_state(page, not is_initial_muted):
                await safe_screenshot(page, "screenshots/real_teams_mute_fail.png")
                sys.exit(1)

            # Unmute toggle
            logger.info("Triggering HID Unmute...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(5000)

            if not await verify_real_mute_state(page, is_initial_muted):
                await safe_screenshot(page, "screenshots/real_teams_unmute_fail.png")
                sys.exit(1)

            logger.info("Real Teams HID Verification SUCCESS")
        except Exception as e:
            logger.error(f"Error during HID verification: {e}")
            await safe_screenshot(page, "screenshots/real_teams_error.png")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
