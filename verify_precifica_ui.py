import asyncio
from playwright.async_api import async_playwright
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = f"file:///{os.path.join(BASE_DIR, 'index.html').replace(os.sep, '/')}"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop View (1920x1080)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        print(f"Loading {HTML_PATH}...")
        await page.goto(HTML_PATH, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Screenshot 1: Top section with Storytelling and Precifica Box
        await page.screenshot(path="screenshot_precifica_1_top.png")
        print("Captured screenshot_precifica_1_top.png")

        # Scroll down to Cockpit
        cockpit = page.locator("#cockpit-ruptura-container")
        if await cockpit.count() > 0:
            await cockpit.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)
            await page.screenshot(path="screenshot_precifica_2_cockpit.png")
            print("Captured screenshot_precifica_2_cockpit.png")

        # Scroll down to Table
        table = page.locator("#table-body-rows")
        if await table.count() > 0:
            await table.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)
            await page.screenshot(path="screenshot_precifica_3_table.png")
            print("Captured screenshot_precifica_3_table.png")

        # 2. Mobile View (iPhone 14 - 390x844)
        mobile_page = await browser.new_page(viewport={"width": 390, "height": 844})
        await mobile_page.goto(HTML_PATH, wait_until="networkidle")
        await mobile_page.wait_for_timeout(2000)

        await mobile_page.screenshot(path="mobile_precifica_1_top.png")
        print("Captured mobile_precifica_1_top.png")

        m_cockpit = mobile_page.locator("#cockpit-ruptura-container")
        if await m_cockpit.count() > 0:
            await m_cockpit.scroll_into_view_if_needed()
            await mobile_page.wait_for_timeout(1000)
            await mobile_page.screenshot(path="mobile_precifica_2_cockpit.png")
            print("Captured mobile_precifica_2_cockpit.png")

        await browser.close()
        print("Done verification screenshots!")

if __name__ == "__main__":
    asyncio.run(main())
