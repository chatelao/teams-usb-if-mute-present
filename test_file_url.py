import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        file_path = os.path.abspath("scripts/mock_teams_web.html")
        url = f"file://{file_path}"
        print(f"Navigating to: {url}")
        await page.goto(url)
        await asyncio.sleep(2)
        try:
            await page.screenshot(path="test_file.png")
            print("Screenshot success")
        except Exception as e:
            print(f"Screenshot failed: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
