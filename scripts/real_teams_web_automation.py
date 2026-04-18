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

        # 1. Check for "Pick an account"
        pick_account = page.locator("div[role='listitem'], .table-row")
        if await pick_account.first.is_visible(timeout=2000):
             logger.info("Pick an account screen detected.")
             use_other = page.locator("#otherTile, #use_another_account")
             if await use_other.is_visible():
                 await use_other.click()
                 await page.wait_for_timeout(2000)

        # 2. Email/Username
        email_input = page.locator("input[type='email'], input[name='loginfmt']")
        if await email_input.is_visible(timeout=5000):
            logger.info("Filling email/username...")
            await email_input.fill(username)
            await page.locator("input[type='submit'], #idSIButton9").click()
            await page.wait_for_timeout(2000)

        # 3. Password
        pass_input = page.locator("input[type='password'], input[name='passwd']")
        if await pass_input.is_visible(timeout=10000):
            logger.info("Filling password...")
            await pass_input.fill(password)
            await page.locator("input[type='submit'], #idSIButton9").click()
            await page.wait_for_timeout(2000)

        # 4. Handle 'Stay signed in?' / 'Keep me signed in'
        try:
            stay_btn = page.locator("#idSIButton9, input[type='submit'], button:has-text('Yes'), button:has-text('Ja')")
            if await stay_btn.is_visible(timeout=10000):
                await stay_btn.click()
                logger.info("Handled 'Stay signed in' prompt.")
        except:
            pass

        return True
    except Exception as e:
        logger.error(f"Login logic error: {e}")
        return False

async def main():
    meeting_url = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "https://teams.microsoft.com/v2/"
    user_creds = os.environ.get("TEAMS_USER")

    if user_creds:
        logger.info(f"TEAMS_USER secret detected (length: {len(user_creds)})")
    else:
        logger.warning("TEAMS_USER secret NOT detected. Login flow will be skipped.")

    async with async_playwright() as p:
        # Launch browser with flags to automatically grant media permissions
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-notifications",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            permissions=["microphone", "camera", "notifications"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        # Explicitly grant permissions for Teams domains
        origins = [
            "https://teams.microsoft.com",
            "https://teams.live.com",
            "https://login.microsoftonline.com",
            "https://teams.microsoft.com/v2/"
        ]
        for origin in origins:
            await context.grant_permissions(["microphone", "camera", "notifications"], origin=origin)

        page = await context.new_page()
        # Automatically accept all dialogs
        page.on("dialog", lambda dialog: dialog.accept())

        logger.info(f"Navigating to Teams: {meeting_url}")
        await page.goto(meeting_url)

        # Main setup loop to handle complex transitions (login, landing pages, pre-join)
        start_time = asyncio.get_event_loop().time()
        max_duration = 360 # 6 minutes total for setup
        mic_button_sel = "button[data-tid='microphone-button'], button[aria-label^='Mute'], button[aria-label^='Unmute'], button[aria-label*='Stummschalt']"

        while (asyncio.get_event_loop().time() - start_time) < max_duration:
            try:
                current_url = page.url
                page_title = await page.title()
                logger.info(f"Current Page: {page_title} ({current_url})")

                # 1. Target Reached: In Meeting UI
                if await page.locator(mic_button_sel).first.is_visible():
                    logger.info("Meeting UI reached.")
                    await safe_screenshot(page, "screenshots/real_teams_meeting_ui.png")
                    break

                # 2. Handle Microsoft Login
                if "login.microsoftonline.com" in current_url and user_creds:
                    logger.info("Entering login handling...")
                    await perform_login(page, user_creds)
                    await page.wait_for_timeout(3000)
                    continue

                # 3. Handle Launcher Page
                launcher_selectors = [
                    "button:has-text('Continue on this browser')",
                    "button:has-text('Webversion verwenden')",
                    "button:has-text('browser instead')",
                    "[data-tid='joinOnWeb']",
                    "button[aria-label*='browser']",
                    "a:has-text('Continue on this browser')",
                    "a:has-text('browser instead')"
                ]
                found_launcher = False
                for sel in launcher_selectors:
                    btn = page.locator(sel).first
                    if await btn.is_visible():
                        logger.info(f"Launcher detected ({sel}). Clicking.")
                        await safe_screenshot(page, "screenshots/real_teams_launcher.png")
                        try:
                            await btn.evaluate("node => node.click()")
                        except:
                            await btn.click(force=True)
                        await page.wait_for_timeout(5000)
                        found_launcher = True
                        break
                if found_launcher:
                    continue

                # 4. Pre-join / Lobby Screen (Filling Name)
                name_input = page.locator("input[data-tid='prejoin-display-name-input'], #prejoin-display-name-input, input[placeholder*='name'], input[placeholder*='Name']").first
                if await name_input.is_visible():
                    logger.info("Pre-join screen detected. Filling name.")
                    await name_input.fill("HID-Compliance-Tester")

                    join_btn_selectors = [
                        "button[data-tid='prejoin-join-button']",
                        "button:has-text('Join now')",
                        "button:has-text('Jetzt teilnehmen')",
                        "button:has-text('Join')"
                    ]
                    for j_sel in join_btn_selectors:
                        j_btn = page.locator(j_sel).first
                        if await j_btn.is_visible():
                            logger.info(f"Join button detected ({j_sel}). Clicking.")
                            await safe_screenshot(page, "screenshots/real_teams_prejoin.png")
                            await j_btn.click()
                            break
                    await page.wait_for_timeout(5000)
                    continue

                # 5. Handle Intermediate Prompts / Permissions / Device Selection
                confirm_btns = [
                    "button:has-text('Allow')",
                    "button:has-text('Allow once')",
                    "button:has-text('Always allow')",
                    "button:has-text('Got it')",
                    "button:has-text('OK')",
                    "button:has-text('Zulassen')",
                    "button:has-text('Verstanden')",
                    "button:has-text('Use this browser')",
                    "button:has-text('Dismiss')",
                    "button:has-text('Continue')",
                    "button:has-text('Join with audio')",
                    "button:has-text('Join with computer audio')",
                    "button[aria-label*='Allow']",
                    "button[aria-label*='Zulassen']"
                ]
                found_confirm = False
                for btn_sel in confirm_btns:
                    btn = page.locator(btn_sel).first
                    if await btn.is_visible():
                        logger.info(f"Detected intermediate prompt: {btn_sel}. Clicking.")
                        await btn.click()
                        found_confirm = True
                        break
                if found_confirm:
                    continue

                logger.info("Waiting for UI state transition...")
                await page.wait_for_timeout(5000)
            except Exception as loop_err:
                logger.warning(f"Error in setup loop iteration: {loop_err}")
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
                logger.error("HID Mute verification failed on real Teams instance.")
                await safe_screenshot(page, "screenshots/real_teams_mute_fail.png")
                sys.exit(1)
            else:
                logger.info("HID Mute verification SUCCESS on real Teams instance.")
                await safe_screenshot(page, "screenshots/real_teams_mute_success.png")

            # Unmute toggle
            logger.info("Triggering HID event again to toggle back...")
            simulate_hid_event(0x0B, 0x2F)
            await page.wait_for_timeout(5000)

            if not await verify_real_mute_state(page, is_initial_muted):
                logger.error("HID Unmute toggle failed on real Teams instance.")
                await safe_screenshot(page, "screenshots/real_teams_unmute_fail.png")
                sys.exit(1)
            else:
                logger.info("HID Unmute toggle SUCCESS on real Teams instance.")

            logger.info("Real Teams HID Compliance Verification: COMPLETED SUCCESSFULLY")

        except Exception as e:
            logger.error(f"Error during HID verification: {e}")
            await safe_screenshot(page, "screenshots/real_teams_error_final.png")
            sys.exit(1)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
