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
        logger.info("Waiting for email/username input...")
        email_input = page.locator("input[type='email'], input[name='loginfmt']")
        await email_input.wait_for(state="visible", timeout=30000)
        await email_input.fill(username)

        submit_btn = page.locator("input[type='submit'], #idSIButton9")
        await submit_btn.click()
        logger.info("Username submitted.")

        # 2. Password
        logger.info("Waiting for password input...")
        pass_input = page.locator("input[type='password'], input[name='passwd']")
        # Sometimes there's a transition, wait for it to be visible
        await pass_input.wait_for(state="visible", timeout=30000)
        await pass_input.fill(password)

        await submit_btn.wait_for(state="visible", timeout=10000)
        await submit_btn.click()
        logger.info("Password submitted.")

        # 3. Handle 'Stay signed in?' / 'Keep me signed in'
        try:
            logger.info("Checking for 'Stay signed in' prompt...")
            # Use a shorter timeout as this might not appear
            await submit_btn.wait_for(state="visible", timeout=15000)
            await submit_btn.click()
            logger.info("Handled 'Stay signed in' prompt.")
        except Exception as e:
            logger.info(f"No 'Stay signed in' prompt detected or click failed: {e}")

        return True
    except Exception as e:
        logger.error(f"Login failed: {e}")
        await safe_screenshot(page, "screenshots/login_failure.png")
        return False

async def main():
    meeting_url = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "https://teams.microsoft.com/v2/"
    user_creds = os.environ.get("TEAMS_USER")

    if meeting_url == "https://teams.microsoft.com/v2/":
        logger.info("No meeting URL provided. Defaulting to Teams Web Portal to ensure real instance is called.")
    else:
        logger.info(f"Using meeting URL: {meeting_url}")

    async with async_playwright() as p:
        # headless=False is required for pyautogui HID simulation to hit the browser window
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            permissions=["microphone", "camera"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        logger.info(f"Navigating to Teams: {meeting_url}")
        await page.goto(meeting_url)

        # Main setup loop to handle transitions (login, landing pages, pre-join)
        start_time = asyncio.get_event_loop().time()
        max_duration = 180 # 3 minutes total for setup

        mic_button_sel = "button[data-tid='microphone-button'], button[aria-label^='Mute'], button[aria-label^='Unmute']"

        while (asyncio.get_event_loop().time() - start_time) < max_duration:
            current_url = page.url
            logger.info(f"Current Page: {await page.title()} ({current_url})")

            # 1. Handle Microsoft Login
            if "login.microsoftonline.com" in current_url and user_creds:
                logger.info("Microsoft Login detected.")
                if not await perform_login(page, user_creds):
                    logger.error("Login attempt failed.")
                    sys.exit(1)
                await page.wait_for_timeout(5000)
                continue

            # 2. Handle Landing Page / Launcher
            continue_btn = page.locator("button:has-text('Continue on this browser'), [data-tid='joinOnWeb']")
            if await continue_btn.is_visible():
                logger.info("Landing page detected. Clicking 'Continue on this browser'.")
                await safe_screenshot(page, "screenshots/real_teams_landing_page.png")
                await continue_btn.click()
                await page.wait_for_timeout(5000)
                continue

            # 3. Handle Pre-join Screen (Guest Name)
            name_input = page.locator("input[data-tid='prejoin-display-name-input'], input[placeholder*='name'], input[placeholder*='Name'], #prejoin-display-name-input")
            if await name_input.is_visible():
                logger.info("Pre-join screen detected. Filling guest name.")
                await name_input.fill("HID-Compliance-Tester")
                await safe_screenshot(page, "screenshots/real_teams_prejoin_filled.png")
                join_btn = page.locator("button[data-tid='prejoin-join-button'], button:has-text('Join now')")
                await join_btn.wait_for(state="visible", timeout=5000)
                await join_btn.click()
                logger.info("Clicked 'Join now'")
                await page.wait_for_timeout(5000)
                continue

            # 4. Check if we reached the meeting UI
            if await page.locator(mic_button_sel).first.is_visible():
                logger.info("Successfully entered meeting UI.")
                await safe_screenshot(page, "screenshots/real_teams_meeting_ui.png")
                break

            # 5. Handle potential "Use this browser" or other one-off prompts
            browser_btn = page.locator("button:has-text('Use this browser')")
            if await browser_btn.is_visible():
                logger.info("One-off browser prompt detected. Clicking.")
                await browser_btn.click()
                continue

            logger.info("Waiting for UI state transition...")
            await page.wait_for_timeout(5000)
        else:
            logger.error("Timed out waiting to reach meeting UI.")
            await safe_screenshot(page, "screenshots/real_teams_setup_timeout.png")
            sys.exit(1)

        try:
            # Final verification of meeting UI before HID tests
            if not await page.locator(mic_button_sel).first.is_visible():
                logger.error("Lost meeting UI after setup loop.")
                sys.exit(1)

            # Initial state detection
            aria_label = await page.locator(mic_button_sel).first.get_attribute("aria-label")
            is_initial_muted = "Unmute" in (aria_label or "")
            logger.info(f"Initial state: {'Muted' if is_initial_muted else 'Unmuted'}")

            # 6. Perform HID Test - Toggle Mute
            logger.info("Triggering HID Telephony Mute event (0x0B, 0x2F)...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(3000)

            if not await verify_real_mute_state(page, not is_initial_muted):
                logger.error("HID Mute verification failed on real Teams instance.")
                await safe_screenshot(page, "screenshots/real_teams_mute_fail.png")
                sys.exit(1)
            else:
                logger.info("HID Mute verification SUCCESS on real Teams instance.")
                await safe_screenshot(page, "screenshots/real_teams_mute_success.png")

            # 7. Perform HID Test - Toggle back
            logger.info("Triggering HID event again to toggle back...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(3000)

            if not await verify_real_mute_state(page, is_initial_muted):
                logger.error("HID Unmute toggle failed on real Teams instance.")
                sys.exit(1)
            else:
                logger.info("HID Unmute toggle SUCCESS on real Teams instance.")

        except Exception as e:
            logger.error(f"Error during Real Teams automation: {e}")
            await safe_screenshot(page, "screenshots/real_teams_error_final.png")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
