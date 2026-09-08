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

async def test_skus_sort():
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

        print("2. Logged in! Waiting 4s for stabilization...")
        await page.wait_for_timeout(4000)

        print("3. Querying SKUs sorted by sales...")
        res = await page.evaluate("""async () => {
            const appId = "671fa4f4-eb7d-418f-b4c9-936e87d8011d";
            const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;
            const CHANNELS = "'APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'e_Commerce'";

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

                        // Query for top SKUs sorted by D-7 + Hoje sales
                        const cSKU = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "q_top_skus_sorted" },
                            "qHyperCubeDef": {
                                "qDimensions": [
                                    { 
                                        "qDef": { 
                                            "qFieldDefs": ["Produto_ID"],
                                            "qSortCriterias": [{
                                                "qSortByExpression": -1,
                                                "qExpression": { "qv": `Sum({1<[Canal]={${CHANNELS}}>} [Receita Líquida])` }
                                            }]
                                        } 
                                    },
                                    { "qDef": { "qFieldDefs": ["Desc_Produto"] } }
                                ],
                                "qMeasures": [
                                    { "qDef": { "qDef": `Sum({1<Dia={'08'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                                    { "qDef": { "qDef": `Sum({1<Dia={'07'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                                    { "qDef": { "qDef": `Sum({1<Dia={'01'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                                    { "qDef": { "qDef": "Sum({1} [Quantidade Saldo])" } }
                                ],
                                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 200, "qWidth": 6 }],
                                "qSuppressZero": true
                            }
                        }]);

                        const hSKU = cSKU.result.qReturn.qHandle;
                        const lSKU = await send("GetLayout", hSKU, []);
                        const matrix = lSKU.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
                        const totSKU = lSKU.result.qLayout.qHyperCube.qSize.qcy;

                        ws.close();
                        resolve({
                            totSKU: totSKU,
                            rows: matrix.map(row => [
                                row[0]?.qNum !== undefined ? row[0].qNum : row[0]?.qText,
                                row[1]?.qText,
                                row[2]?.qNum || 0,
                                row[3]?.qNum || 0,
                                row[4]?.qNum || 0,
                                row[5]?.qNum || 0
                            ])
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

        print(f"Total SKUs: {res.get('totSKU')}")
        print("First 15 sorted SKUs:")
        for r in res.get('rows', [])[:15]:
            print(" ", r)

        # Check if Mounjaro is in the rows
        moun = [r for r in res.get('rows', []) if 'MOUN' in str(r[1]).upper()]
        print(f"Mounjaro in first 200 rows: {len(moun)}")
        for m in moun:
            print("   ->", m)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_skus_sort())
