import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
STREAM_URL = "https://sense.farmaciassaojoao.com.br/hub/stream/9befd6bf-7c87-43bf-b756-93c8fbf61fe2"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        ctx = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD},
            viewport={'width': 1920, 'height': 1080}
        )
        page = await ctx.new_page()
        print("Acessando Stream do Qlik Sense...", flush=True)
        await page.goto(STREAM_URL, timeout=60000)
        await page.wait_for_timeout(8000)
        
        title = await page.title()
        url = page.url
        print(f"Título: {title} | URL: {url}")
        
        # Inspeciona os elementos do Hub
        data = await page.evaluate("""() => {
            // Pega nome do stream selecionado
            const activeStream = document.querySelector('.stream.active, .selected-stream, .stream-name, h1')?.innerText || '';
            
            // Pega todos os cards de aplicativos visíveis
            const items = [];
            const cards = document.querySelectorAll('.qv-card, .qv-app-card, [ng-repeat*="item in"]');
            cards.forEach(c => {
                const title = c.querySelector('.title, .item-title, h3, h2')?.innerText || c.getAttribute('title') || '';
                const desc = c.querySelector('.description, .item-description, p')?.innerText || '';
                const link = c.querySelector('a')?.href || '';
                if (title) {
                    items.push({ title: title.trim(), desc: desc.trim(), link });
                }
            });
            
            // Se não pegou por cards, varre todos os links para /sense/app/
            const links = Array.from(document.querySelectorAll('a[href*="/app/"]')).map(a => ({
                text: a.innerText.trim(),
                href: a.href
            }));

            // Pega também o menu lateral de streams
            const streams = Array.from(document.querySelectorAll('.stream, [ng-repeat*="stream"]')).map(s => s.innerText.trim());

            return {
                activeStream,
                items,
                links,
                streams: streams.slice(0, 20),
                bodyText: document.body.innerText.slice(0, 1500)
            };
        }""")
        
        # Tira screenshot do Hub para conferir visualmente
        await page.screenshot(path="hub_stream_view.png", full_page=True)
        print("Screenshot salvo em hub_stream_view.png")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
