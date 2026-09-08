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

                // Consulta medidas mestres desse app
                const cMeasures = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "MeasureList" },
                    "qMeasureListDef": {
                        "qType": "measure",
                        "qData": {
                            "title": "/title",
                            "tags": "/tags",
                            "qMeasure": "/qMeasure"
                        }
                    }
                }]);
                const hM = cMeasures.result.qReturn.qHandle;
                const lM = await send("GetLayout", hM, []);
                const masterMeasures = (lM.result.qLayout.qMeasureList?.qItems || []).map(item => ({
                    id: item.qInfo?.qId,
                    title: item.qMetaDef?.title,
                    expression: item.qData?.qMeasure?.qDef,
                    label: item.qData?.qMeasure?.qLabel
                }));

                // Avaliações de Mounjaro 5mg (10046653) no app de Estoque Final
                const eQtEstoque = await send("Evaluate", docHandle, ["Sum({1<Produto_ID={'10046653'}>} Qt_Estoque)"]);
                const eQtEstoqueCD = await send("Evaluate", docHandle, ["Sum({1<Produto_ID={'10046653'}>} Qt_EstoqueCD)"]);
                const eTransito = await send("Evaluate", docHandle, ["Sum({1<Produto_ID={'10046653'}>} Qt_Transito_CDLJ)"]);

                // Total de estoque geral de todos os produtos
                const eTotGeralEstoque = await send("Evaluate", docHandle, ["Sum(Qt_Estoque)"]);
                const eTotGeralCD = await send("Evaluate", docHandle, ["Sum(Qt_EstoqueCD)"]);

                ws.close();
                resolve({
                    masterMeasures,
                    mounj5: {
                        qt_estoque_lojas: eQtEstoque.result?.qReturn,
                        qt_estoque_cd: eQtEstoqueCD.result?.qReturn,
                        qt_transito_cdlj: eTransito.result?.qReturn
                    },
                    totGeral: {
                        lojas: eTotGeralEstoque.result?.qReturn,
                        cd: eTotGeralCD.result?.qReturn
                    }
                });
            } catch (e) {
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
