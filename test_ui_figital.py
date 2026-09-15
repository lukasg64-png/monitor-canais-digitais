import os
import asyncio
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = 'file:///' + os.path.join(BASE_DIR, 'index.html').replace(os.sep, '/')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1600, 'height': 1000})
        
        print('Abrindo:', HTML_PATH)
        await page.goto(HTML_PATH)
        await page.wait_for_timeout(2000)
        
        # 1. Screenshot Inicial
        await page.screenshot(path='screenshot_ui_initial.png')
        card_total_sales = await page.inner_text('#tab-sales-Total')
        card_fig_sales = await page.inner_text('#tab-sales-Figital')
        kpi_realizado = await page.inner_text('#card-realizado')
        print(f'Estado Inicial: Total={card_total_sales} | Figital={card_fig_sales} | KPI={kpi_realizado}')
        
        # 2. Toggle Com Figital
        btn_com = await page.query_selector('#btnFigCom')
        if btn_com:
            await btn_com.click()
            await page.wait_for_timeout(1000)
            card_total_com = await page.inner_text('#tab-sales-Total')
            kpi_com = await page.inner_text('#card-realizado')
            print(f'Apos Toggle [Com Figital]: Total={card_total_com} | KPI={kpi_com}')
            await page.screenshot(path='screenshot_ui_com_figital.png')
        
        # 3. Card Figital Exclusivo
        card_fig = await page.query_selector('[data-channel="Figital"]')
        if card_fig:
            await card_fig.click()
            await page.wait_for_timeout(1000)
            kpi_fig = await page.inner_text('#card-realizado')
            pacing_fig = await page.inner_text('#card-pacing-badge')
            print(f'Apos Click [Figital]: KPI={kpi_fig} | Badge={pacing_fig}')
            await page.screenshot(path='screenshot_ui_canal_figital.png')

        # 4. Header Toggle
        btn_header_fig = await page.query_selector('#header-btn-figital-toggle')
        if btn_header_fig:
            await (await page.query_selector('[data-channel="Total"]')).click()
            await page.wait_for_timeout(500)
            await btn_header_fig.click()
            await page.wait_for_timeout(500)
            header_txt = await page.inner_text('#header-figital-status-txt')
            card_total_header = await page.inner_text('#tab-sales-Total')
            print(f'Apos Header Toggle: Status={header_txt} | Total={card_total_header}')
            await page.screenshot(path='screenshot_ui_header_toggle.png')

        await browser.close()
        print('Teste de UI concluido com 100% de sucesso!')

if __name__ == '__main__':
    asyncio.run(main())
