import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ID = "671fa4f4-eb7d-418f-b4c9-936e87d8011d"
SHEET_ID = "ddd70c77-1a06-40d9-aff2-efa4b6b67b24"
SHEET_URL = f"{QLIK_URL}/sense/app/{APP_ID}/sheet/{SHEET_ID}/state/analysis"

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"

async def check_mounjaro_in_qlik():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        print("1. Logging in to Qlik Sense...")
        await page.goto(SHEET_URL, wait_until="networkidle", timeout=60000)

        # Check login
        if "login" in page.url.lower() or await page.query_selector('input[type="password"]'):
            user_input = await page.query_selector('input[name="username"], input[id*="user"], input[type="text"]')
            pass_input = await page.query_selector('input[name="password"], input[id*="pass"], input[type="password"]')
            if user_input and pass_input:
                await user_input.fill(USERNAME)
                await pass_input.fill(PASSWORD)
                btn = await page.query_selector('button[type="submit"], input[type="submit"]')
                if btn: await btn.click()
                await page.wait_for_load_state("networkidle", timeout=60000)

        print("2. Logged in! Querying Mounjaro SKUs...")
        res = await page.evaluate("""async () => {
            const appId = "671fa4f4-eb7d-418f-b4c9-936e87d8011d";
            const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;
            
            return new Promise((resolve, reject) => {
                const ws = new WebSocket(wsUrl);
                let msgId = 1;
                const pending = {};

                function send(method, handle, params) {
                    return new Promise((res, rej) => {
                        const id = msgId++;
                        pending[id] = { res, rej };
                        ws.send(JSON.stringify({ "jsonrpc": "2.0", "id": id, "method": method, "handle": handle, "params": params }));
                    });
                }

                ws.onopen = async () => {
                    try {
                        await send("OpenDoc", -1, [appId]);
                        const docHandle = 1;

                        // Query for Mounjaro or Lilly SKUs
                        const cSKU = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "q_mounjaro_test" },
                            "qHyperCubeDef": {
                                "qDimensions": [
                                    { "qDef": { "qFieldDefs": ["Produto_ID"] } },
                                    { "qDef": { "qFieldDefs": ["Desc_Produto"] } },
                                    { "qDef": { "qFieldDefs": ["Laboratorio"] } }
                                ],
                                "qMeasures": [
                                    { "qDef": { "qDef": "Sum({1<[Canal]={'APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'e_Commerce'}>} [Receita Líquida])" } },
                                    { "qDef": { "qDef": "Sum({1} [Quantidade Saldo])" } }
                                ],
                                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 500, "qWidth": 5 }]
                            }
                        }]);

                        const hSKU = cSKU.result.qReturn.qHandle;
                        const lSKU = await send("GetLayout", hSKU, []);
                        const totSKU = lSKU.result.qLayout.qHyperCube.qSize.qcy;
                        
                        // Search for Eli Lilly specifically
                        const cLilly = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "q_lilly_skus" },
                            "qHyperCubeDef": {
                                "qDimensions": [
                                    { "qDef": { "qFieldDefs": ["Produto_ID"] } },
                                    { "qDef": { "qFieldDefs": ["Desc_Produto"] } }
                                ],
                                "qMeasures": [
                                    { "qDef": { "qDef": "Sum({1<Laboratorio={'ELI LILLY DO BRASIL LTDA'}, [Canal]={'APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'e_Commerce'}>} [Receita Líquida])" } },
                                    { "qDef": { "qDef": "Sum({1<Laboratorio={'ELI LILLY DO BRASIL LTDA'}>} [Quantidade Saldo])" } }
                                ],
                                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 100, "qWidth": 4 }],
                                "qSuppressZero": true
                            }
                        }]);
                        const hLilly = cLilly.result.qReturn.qHandle;
                        const lLilly = await send("GetLayout", hLilly, []);
                        const matrixLilly = lLilly.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];

                        ws.close();
                        resolve({
                            totSKU: totSKU,
                            lillyRows: matrixLilly.map(row => row.map(cell => cell.qText || cell.qNum))
                        });
                    } catch(e) {
                        ws.close();
                        reject(e.message || String(e));
                    }
                };

                ws.onmessage = (event) => {
                    const msg = JSON.parse(event.data);
                    if (msg.id && pending[msg.id]) {
                        const { res, rej } = pending[msg.id];
                        delete pending[msg.id];
                        if (msg.error) rej(new Error(JSON.stringify(msg.error)));
                        else res(msg);
                    }
                };
            });
        }""");

        print(f"Total SKUs in Qlik app: {res.get('totSKU')}")
        print("Lilly SKUs count:", len(res.get('lillyRows', [])))
        for r in res.get('lillyRows', []):
            print(" ", r)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_mounjaro_in_qlik())
