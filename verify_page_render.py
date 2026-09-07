import asyncio, sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        await page.goto('http://localhost:3000/index.html')
        await page.wait_for_timeout(2500)
        
        # Scroll to Cockpit de Ruptura
        await page.evaluate('window.scrollTo(0, 1800)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='screenshot_stock_cockpit_rendered.png')
        
        # Scroll to table
        await page.evaluate('window.scrollTo(0, 2400)')
        await page.wait_for_timeout(1000)
        await page.screenshot(path='screenshot_table_capilaridade_rendered.png')
        
        diag = await page.inner_text('#story-estoque')
        print('DIAGNOSTICO ESTOQUE:\n', diag)
        
        kpi_rup = await page.inner_text('#kpi-est-perda-ruptura')
        kpi_com = await page.inner_text('#kpi-est-perda-comercial')
        print(f'\nKPIS: Ruptura={kpi_rup} | Comercial={kpi_com}')
        
        rows = await page.query_selector_all('#table-body-rows tr')
        print(f'\nTotal rows: {len(rows)}')
        for r in rows[:6]:
            t = await r.inner_text()
            print('ROW:', t.replace('\n', ' | '))
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
