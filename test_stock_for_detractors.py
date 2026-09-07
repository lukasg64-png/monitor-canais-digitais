"""
test_stock_for_detractors.py
Verifica o estoque real ([Quantidade Saldo]) dos principais detratores e alavancadores
no próprio app 'E-Commerce x Rede' (671fa4f4-eb7d-418f-b4c9-936e87d8011d).
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

                // Consulta Produto_ID, Desc_Produto, Saldo, Venda Hoje, Venda D-7
                const cObj = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_check_skus_saldo" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Produto_ID"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Produto"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": "Sum({1} [Quantidade Saldo])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}>} [Receita Líquida])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}>} [Receita Líquida])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}>} [Quantidade Produto])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}>} [Quantidade Produto])" } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 100, "qWidth": 7 }],
                        "qSuppressZero": true
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

    rows = res.get("rows", [])
    print("=" * 85)
    print("ANÁLISE DE ESTOQUE REAL (QUANTIDADE SALDO) VS VENDAS:")
    print("=" * 85)
    
    # Procura alguns produtos de interesse (Mounjaro, Fraldas, Leite, etc.)
    for r in rows[:40]:
        saldo = r[2]
        v_hoje = r[3]
        v_d7 = r[4]
        q_d7 = r[5]
        q_hoje = r[6]
        gap = (v_hoje or 0) - (v_d7 or 0)
        status_estoque = "🚨 ZERADO / BAIXO" if (saldo is None or saldo <= 5) else ("⚠️ CRÍTICO" if saldo < 30 else "✅ DISPONÍVEL")
        print(f"SKU {r[0]} | {r[1][:40]:<40} | Saldo: {saldo} ({status_estoque}) | Venda Hoje: R$ {v_hoje:,.0f} | D7: R$ {v_d7:,.0f} | GAP: R$ {gap:,.0f}")

if __name__ == "__main__":
    asyncio.run(run())
