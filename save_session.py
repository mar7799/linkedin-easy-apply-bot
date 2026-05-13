"""
Run this ONCE to save your LinkedIn session.
After logging in manually, it saves cookies to session.json.
"""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")

        print("\n==> LinkedIn login page is open.")
        print("==> Log in with your credentials in the browser.")
        print("==> Once you are on the LinkedIn home feed, come back here and press Enter.\n")
        input("Press Enter when fully logged in: ")

        await context.storage_state(path="session.json")
        print("\nSession saved to session.json — you can now run main.py")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
