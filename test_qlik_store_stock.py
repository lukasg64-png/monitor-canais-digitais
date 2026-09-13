import asyncio
import json
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ECOMM = "671fa4f4-eb7d-418f-b4c9-936e87d8011d"
APP_RUPTURA = "4c210d43-3ea6-45ea-994f-ced22d3ceb0d"
APP_ESTOQUE = "936a28fb-245f-4f19-b285-420535685c43"

JS_TEST = """async () => {
    const wsUrl = (appId) => `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;
    function connectApp(appId) {
        return new Promise((resolve, reject) => {
            const ws = new WebSocket(wsUrl(appId));
            let id = 1;
            const pending = {};
            ws.onmessage = (e) => {
                const m = JSON.parse(e.data);
                if (m.id && pending[m.id]) {
                    const { res, rej } = pending[m.id];
                    delete pending[m.id];
                    if (m.error) rej(m.error); else res(m);
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
                    await send("OpenDoc", -1, [appId]);
                    resolve({ ws, send, docHandle: 1 });
                } catch(e) { ws.close(); reject(e); }
            };
        });
    }

    const report = {};
    // Test App E-Commerce x Rede: can we query store stock and turnover?
    try {
        const { ws, send, docHandle } = await connectApp("671fa4f4-eb7d-418f-b4c9-936e87d8011d");
        
        // Let's test evaluating store stock for Top 5 stores of a SKU (e.g. Mounjaro 10046653 or Leite Ninho 100015081)
        const cObj = await send("CreateSessionObject", docHandle, [{
            "qInfo": { "qType": "q_test_lojas_stock" },
            "qHyperCubeDef": {
                "qDimensions": [
                    { "qDef": { "qFieldDefs": ["Filial_ID"] } },
                    { "qDef": { "qFieldDefs": ["Desc_Filial"] } }
                ],
                "qMeasures": [
                    { "qDef": { "qDef": "Sum({1} [Quantidade Saldo])" } },
                    { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-09'}, Dia={'12'}>} [Receita Líquida])" } },
                    { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-09'}, Dia={'12'}>} [Quantidade Produto])" } },
                    { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-08'}>} [Quantidade Produto]) / 31" } } // Giro médio diário agosto
                ],
                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 20, "qWidth": 6 }],
                "qSuppressZero": true
            }
        }]);
        const h = cObj.result.qReturn.qHandle;
        const l = await send("GetLayout", h, []);
        const matrix = l.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
        report.ecomm_sample = matrix.map(r => ({
            filial_id: r[0]?.qText,
            nome: r[1]?.qText,
            saldo: r[2]?.qNum,
            receita_hoje: r[3]?.qNum,
            qtd_hoje: r[4]?.qNum,
            giro_diario: r[5]?.qNum
        }));
        ws.close();
    } catch(err) {
        report.ecomm_error = err.message || String(err);
    }

    return report;
}"""

async def run():
    print("Testando conexão e extração de estoque/giro por filial no Qlik Sense...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD}
        )
        page = await context.new_page()
        try:
            await page.goto(f"{QLIK_URL}/sense/app/{APP_ECOMM}", timeout=45000)
            await page.wait_for_timeout(4000)
            res = await page.evaluate(JS_TEST)
            print("Resultado da consulta:")
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except Exception as e:
            print("Erro no Playwright:", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
