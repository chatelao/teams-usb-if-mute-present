import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Navigating to Microsoft Teams...")
        try:
            # Go to Teams Web App
            await page.goto("https://teams.microsoft.com")

            # Wait for some content to load or redirect to login
            await page.wait_for_timeout(5000)

            title = await page.title()
            print(f"Page Title: {title}")

            # Take a screenshot for verification
            screenshot_path = "teams_web_init.png"
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

        except Exception as e:
            print(f"Error during Teams Web automation: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
