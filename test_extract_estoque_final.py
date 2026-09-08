import asyncio
import json
import os
import sys
import time
from playwright.async_api import async_playwright

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ESTOQUE_FINAL = "936a28fb-245f-4f19-b285-420535685c43"
SHEET_URL = f"{QLIK_URL}/sense/app/671fa4f4-eb7d-418f-b4c9-936e87d8011d/sheet/ddd70c77-1a06-40d9-aff2-efa4b6b67b24/state/analysis"

async def main():
    t0 = time.time()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        ctx = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD}
        )
        page = await ctx.new_page()
        print("1. Abrindo sessão Qlik...", flush=True)
        await page.goto(SHEET_URL, timeout=60000)
        try:
            await page.wait_for_selector('.qv-panel-sheet', timeout=30000)
        except Exception:
            await page.wait_for_timeout(4000)

        print("2. Consultando Relatório Estoque Final via WebSocket...", flush=True)
        js_code = """async () => {
            const appId = "936a28fb-245f-4f19-b285-420535685c43";
            const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;

            return new Promise((resolve, reject) => {
                const ws = new WebSocket(wsUrl);
                let id = 1;
                const pending = {};

                ws.onmessage = (e) => {
                    const msg = JSON.parse(e.data);
                    if (msg.id && pending[msg.id]) {
                        const { res, rej } = pending[msg.id];
                        delete pending[msg.id];
                        if (msg.error) rej(new Error(JSON.stringify(msg.error)));
                        else res(msg);
                    }
                };

                function send(method, handle, params) {
                    return new Promise((res, rej) => {
                        const mid = id++;
                        pending[mid] = { res, rej };
                        ws.send(JSON.stringify({ jsonrpc: "2.0", id: mid, method, handle, params }));
                    });
                }

                ws.onopen = async () => {
                    try {
                        const o = await send("OpenDoc", -1, [appId]);
                        const docHandle = o.result.qReturn.qHandle;

                        // Consulta HyperCube por Produto_ID com Qt_Estoque e Lojas com Estoque > 0
                        const cObj = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "q_estoque_produtos" },
                            "qHyperCubeDef": {
                                "qDimensions": [
                                    { "qDef": { "qFieldDefs": ["Produto_ID"] } }
                                ],
                                "qMeasures": [
                                    { "qDef": { "qDef": "Sum({1<AnoMes={'2026-09'}>} Qt_Estoque)" } },
                                    { "qDef": { "qDef": "Count(distinct {1<AnoMes={'2026-09'}, Qt_Estoque={'>0'}>} Cod_Unid)" } },
                                    { "qDef": { "qDef": "Sum({1<AnoMes={'2026-09'}>} Qt_EstoqueCD)" } },
                                    { "qDef": { "qDef": "Sum({1<AnoMes={'2026-09'}>} Qt_Transito_CDLJ)" } }
                                ],
                                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 2000, "qWidth": 5 }],
                                "qSuppressZero": true
                            }
                        }]);

                        const h = cObj.result.qReturn.qHandle;
                        const l = await send("GetLayout", h, []);
                        const totalRows = l.result.qLayout.qHyperCube.qSize.qcy;
                        const dataPages = l.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];

                        // Paginação completa para todos os SKUs
                        let allRows = [...dataPages];
                        let currentTop = 2000;
                        while (currentTop < totalRows) {
                            const pageRes = await send("GetHyperCubeData", h, ["/qHyperCubeDef", [{ "qTop": currentTop, "qLeft": 0, "qHeight": 2000, "qWidth": 5 }]]);
                            const newRows = pageRes.result.qDataPages[0]?.qMatrix || [];
                            allRows.push(...newRows);
                            currentTop += 2000;
                        }

                        ws.close();
                        resolve({
                            totalRows,
                            sampleCount: allRows.length,
                            rows: allRows.map(r => ({
                                id: r[0]?.qText,
                                estoqueLoja: r[1]?.qNum || 0,
                                lojasAtivas: r[2]?.qNum || 0,
                                estoqueCD: r[3]?.qNum || 0,
                                transito: r[4]?.qNum || 0
                            }))
                        });
                    } catch (e) {
                        ws.close();
                        reject(e.message || String(e));
                    }
                };
            });
        };"""

        res = await page.evaluate(js_code)
        await browser.close()

    elapsed = time.time() - t0
    print(f"Extração concluída em {elapsed:.1f}s! Total de SKUs com estoque: {res['totalRows']}", flush=True)
    
    # Verifica Mounjaro na amostra
    mounj5 = next((x for x in res['rows'] if x['id'] == '10046653'), None)
    mounj25 = next((x for x in res['rows'] if x['id'] == '10046652'), None)
    print(f"Mounjaro 5mg (10046653): {mounj5}")
    print(f"Mounjaro 2,5mg (10046652): {mounj25}")

    with open("test_estoque_final_extracted.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
