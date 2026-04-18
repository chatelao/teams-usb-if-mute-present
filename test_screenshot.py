import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://google.com")
        await asyncio.sleep(2)
        try:
            await page.screenshot(path="test.png")
            print("Screenshot success")
        except Exception as e:
            print(f"Screenshot failed: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
