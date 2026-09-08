import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ESTOQUE_FINAL = "936a28fb-245f-4f19-b285-420535685c43"

JS_QUERY = """async () => {
    const appId = "936a28fb-245f-4f19-b285-420535685c43";
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
                const openRes = await send("OpenDoc", -1, [appId]);
                const docHandle = openRes.result.qReturn.qHandle;

                // 1. Listar valores do campo AnoMes
                const cField = await send("GetField", docHandle, ["AnoMes"]);
                const hF = cField.result.qReturn.qHandle;
                const cardRes = await send("GetCardinal", hF, []);
                
                // Pega todos os valores de AnoMes
                const cObj = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_anomes_list" },
                    "qHyperCubeDef": {
                        "qDimensions": [{ "qDef": { "qFieldDefs": ["AnoMes"] } }],
                        "qMeasures": [
                            { "qDef": { "qDef": "Sum({1<Produto_ID={'10046653'}>} Qt_Estoque)" } },
                            { "qDef": { "qDef": "Sum({1<Produto_ID={'10046653'}>} Qt_EstoqueCD)" } },
                            { "qDef": { "qDef": "Sum({1<Produto_ID={'10046652'}>} Qt_Estoque)" } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 50, "qWidth": 4 }]
                    }
                }]);
                const h = cObj.result.qReturn.qHandle;
                const l = await send("GetLayout", h, []);
                const rows = (l.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => ({
                    anoMes: r[0]?.qText,
                    mounj5_loja: r[1]?.qNum,
                    mounj5_cd: r[2]?.qNum,
                    mounj25_loja: r[3]?.qNum
                }));

                ws.close();
                resolve({
                    success: true,
                    anoMesRows: rows
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
}"""

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD}
        )
        page = await context.new_page()
        await page.goto(f"{QLIK_URL}/sense/app/{APP_ESTOQUE_FINAL}", timeout=60000)
        try:
            await page.wait_for_selector('.qv-panel-sheet', timeout=20000)
        except Exception:
            await page.wait_for_timeout(4000)

        res = await page.evaluate(JS_QUERY)
        await browser.close()

    print(json.dumps(res, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(run())
