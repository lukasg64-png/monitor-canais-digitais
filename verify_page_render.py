import asyncio, sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        await page.goto('http://localhost:3000/index.html')
        await page.wait_for_timeout(2000)
        
        # Screenshot top diagnostico
        await page.screenshot(path='screenshot_diagnostico_stock.png')
        
        # Click skus
        await page.click('[data-level="skus"]')
        await page.wait_for_timeout(1000)
        
        # Scroll to table
        el = await page.query_selector('.matrix-container')
        if el:
            await el.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await page.screenshot(path='screenshot_skus_stock_table.png')
            
        diag = await page.inner_text('#story-estoque')
        print('DIAGNOSTICO ESTOQUE:', diag)
        
        rows = await page.query_selector_all('#table-body-rows tr')
        print(f'Total rows rendered: {len(rows)}')
        for r in rows[:4]:
            t = await r.inner_text()
            print('ROW:', t.replace('\n', ' | '))
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
