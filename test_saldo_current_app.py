"""
test_saldo_current_app.py
Verifica os valores reais do campo 'Quantidade Saldo' no app atual 'E-Commerce x Rede' (671fa4f4-eb7d-418f-b4c9-936e87d8011d).
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ID = "671fa4f4-eb7d-418f-b4c9-936e87d8011d"

JS_QUERY = """async () => {
    const appId = "671fa4f4-eb7d-418f-b4c9-936e87d8011d";
    const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;
    return new Promise((resolve) => {
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

                // Consulta Produto x Quantidade Saldo e Receita Líquida
                const cObj = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_check_saldo" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Produto_ID"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Produto"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": "Sum([Quantidade Saldo])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}>} [Receita Líquida])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}>} [Receita Líquida])" } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 30, "qWidth": 5 }],
                        "qSuppressZero": false
                    }
                }]);
                const h = cObj.result.qReturn.qHandle;
                const l = await send("GetLayout", h, []);
                const matrix = l.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
                const rows = matrix.map(r => r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText));

                ws.close();
                resolve({ success: true, rows: rows });
            } catch (e) {
                ws.close();
                resolve({ success: false, error: e.message || String(e) });
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

        setTimeout(() => {
            try { ws.close(); } catch(e) {}
            resolve({ success: false, error: "timeout" });
        }, 25000);
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
        await page.goto(f"{QLIK_URL}/sense/app/{APP_ID}", timeout=60000)
        try:
            await page.wait_for_selector('.qv-panel-sheet', timeout=20000)
        except Exception:
            await page.wait_for_timeout(4000)

        res = await page.evaluate(JS_QUERY)
        await browser.close()

    print("=" * 70)
    print("AMOSTRA DE 'Quantidade Saldo' NO APP ATUAL:")
    print("=" * 70)
    for r in res.get("rows", [])[:20]:
        print(f"SKU {r[0]} - {r[1][:40]}: Saldo={r[2]} | Venda Hoje={r[3]} | Venda D7={r[4]}")

if __name__ == "__main__":
    asyncio.run(run())
