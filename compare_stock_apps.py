import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ESTOQUE_FINAL = "936a28fb-245f-4f19-b285-420535685c43"
APP_ECOMM = "671fa4f4-eb7d-418f-b4c9-936e87d8011d"

JS_QUERY = """async () => {
    const wsUrl = (appId) => `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;
    
    function connectApp(appId) {
        return new Promise((resolve, reject) => {
            const ws = new WebSocket(wsUrl(appId));
            let msgId = 1;
            const pending = {};

            function send(method, handle, params) {
                return new Promise((res, rej) => {
                    const id = msgId++;
                    pending[id] = { res, rej };
                    ws.send(JSON.stringify({ "jsonrpc": "2.0", "id": id, "method": method, "handle": handle, "params": params }));
                });
            }

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.id && pending[msg.id]) {
                    const { res, rej } = pending[msg.id];
                    delete pending[msg.id];
                    if (msg.error) rej(new Error(JSON.stringify(msg.error)));
                    else res(msg);
                }
            };

            ws.onopen = async () => {
                try {
                    await send("OpenDoc", -1, [appId]);
                    resolve({ ws, send, docHandle: 1 });
                } catch(e) {
                    ws.close();
                    reject(e);
                }
            };
        });
    }

    const results = {};

    // 1. Estoque Final (936a28fb-245f-4f19-b285-420535685c43)
    try {
        const { ws, send, docHandle } = await connectApp("936a28fb-245f-4f19-b285-420535685c43");
        
        // Verifica como está o estoque por filial no Estoque Final
        const cObj = await send("CreateSessionObject", docHandle, [{
            "qInfo": { "qType": "q_test" },
            "qHyperCubeDef": {
                "qDimensions": [
                    { "qDef": { "qFieldDefs": ["Cod_Unid"] } },
                    { "qDef": { "qFieldDefs": ["Desc_Filial"] } }
                ],
                "qMeasures": [
                    { "qDef": { "qDef": "Sum({1<Produto_ID={'10046653'}>} Qt_Estoque)" } },
                    { "qDef": { "qDef": "Sum({1<Produto_ID={'10046653'}>} Qt_Giro_030)" } }
                ],
                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 20, "qWidth": 4 }],
                "qSuppressZero": true
            }
        }]);
        const h = cObj.result.qReturn.qHandle;
        const l = await send("GetLayout", h, []);
        const matrix = l.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
        const totFiliais = l.result.qLayout.qHyperCube.qSize.qcy;

        results.estoqueFinal = {
            totFiliaisComEstoqueMounj5: totFiliais,
            sample: matrix.map(r => ({ cod: r[0]?.qText, nome: r[1]?.qText, estoque: r[2]?.qNum, giro30: r[3]?.qNum }))
        };

        // Total de Lojas distintas no app Estoque Final
        const eLojas = await send("Evaluate", docHandle, ["Count(distinct Cod_Unid)"]);
        results.estoqueFinal.totalLojasNoApp = eLojas.result?.qReturn;

        ws.close();
    } catch(e) {
        results.estoqueFinalError = e.message || String(e);
    }

    // 2. E-Commerce x Rede (671fa4f4-eb7d-418f-b4c9-936e87d8011d)
    // O que é [Quantidade Saldo]?
    try {
        const { ws, send, docHandle } = await connectApp("671fa4f4-eb7d-418f-b4c9-936e87d8011d");
        
        // Verifica se [Quantidade Saldo] tem filtro de data ou se varia por data
        const cObj2 = await send("CreateSessionObject", docHandle, [{
            "qInfo": { "qType": "q_test2" },
            "qHyperCubeDef": {
                "qDimensions": [
                    { "qDef": { "qFieldDefs": ["Dia"] } }
                ],
                "qMeasures": [
                    { "qDef": { "qDef": "Sum({1<Produto_ID={'10046653'}>} [Quantidade Saldo])" } },
                    { "qDef": { "qDef": "Sum({<Produto_ID={'10046653'}>} [Quantidade Saldo])" } }
                ],
                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 35, "qWidth": 3 }]
            }
        }]);
        const h2 = cObj2.result.qReturn.qHandle;
        const l2 = await send("GetLayout", h2, []);
        const matrix2 = l2.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
        results.ecomDias = matrix2.map(r => ({ dia: r[0]?.qText, saldoCom1: r[1]?.qNum, saldoSem1: r[2]?.qNum }));

        // Verifica os canais do app E-Commerce x Rede
        const cCanal = await send("CreateSessionObject", docHandle, [{
            "qInfo": { "qType": "q_canal" },
            "qHyperCubeDef": {
                "qDimensions": [{ "qDef": { "qFieldDefs": ["Canal"] } }],
                "qMeasures": [
                    { "qDef": { "qDef": "Sum({<Produto_ID={'10046653'}>} [Quantidade Saldo])" } }
                ],
                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 20, "qWidth": 2 }]
            }
        }]);
        const hC = cCanal.result.qReturn.qHandle;
        const lC = await send("GetLayout", hC, []);
        results.ecomCanais = (lC.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => ({ canal: r[0]?.qText, saldo: r[1]?.qNum }));

        ws.close();
    } catch(e) {
        results.ecomError = e.message || String(e);
    }

    return results;
}"""

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD}
        )
        page = await context.new_page()
        await page.goto(f"{QLIK_URL}/sense/app/{APP_ECOMM}", timeout=60000)
        try:
            await page.wait_for_selector('.qv-panel-sheet', timeout=20000)
        except Exception:
            await page.wait_for_timeout(4000)

        res = await page.evaluate(JS_QUERY)
        await browser.close()

    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(run())
