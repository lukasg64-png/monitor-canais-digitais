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

JS_TEST_SKU_LOJA = """async () => {
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
    try {
        const { ws, send, docHandle } = await connectApp("671fa4f4-eb7d-418f-b4c9-936e87d8011d");
        
        // 1. Get Top 5 SKUs in digital sales this month or detractor SKUs
        // Let's test evaluating SKU x Filial for a top SKU: e.g., filter or query top SKUs
        const skuObj = await send("CreateSessionObject", docHandle, [{
            "qInfo": { "qType": "q_top_skus" },
            "qHyperCubeDef": {
                "qDimensions": [
                    { "qDef": { "qFieldDefs": ["Produto_ID"] } },
                    { "qDef": { "qFieldDefs": ["Desc_Produto"] } }
                ],
                "qMeasures": [
                    { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-09'}>} [Receita Líquida])" } },
                    { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-09'}>} [Quantidade Produto])" } },
                    { "qDef": { "qDef": "Sum({1} [Quantidade Saldo])" } }
                ],
                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 10, "qWidth": 5 }],
                "qSuppressZero": true
            }
        }]);
        const hSku = skuObj.result.qReturn.qHandle;
        const lSku = await send("GetLayout", hSku, []);
        const skus = lSku.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
        report.top_skus = skus.map(r => ({
            id: r[0]?.qText,
            nome: r[1]?.qText,
            receita: r[2]?.qNum,
            qtd: r[3]?.qNum,
            saldo: r[4]?.qNum
        }));

        // Pick the top SKU and query its stock and sales across stores in a specific municipality (e.g. Passo Fundo or Porto Alegre)
        const sampleSkuId = report.top_skus[0]?.id;
        report.selected_sku = sampleSkuId;

        // Query stores for this SKU
        const storeSkuObj = await send("CreateSessionObject", docHandle, [{
            "qInfo": { "qType": "q_store_sku" },
            "qHyperCubeDef": {
                "qDimensions": [
                    { "qDef": { "qFieldDefs": ["Filial_ID"] } },
                    { "qDef": { "qFieldDefs": ["Desc_Filial"] } },
                    { "qDef": { "qFieldDefs": ["Municipio"] } }
                ],
                "qMeasures": [
                    { "qDef": { "qDef": `Sum({1<Produto_ID={'${sampleSkuId}'}>} [Quantidade Saldo])` } },
                    { "qDef": { "qDef": `Sum({1<Produto_ID={'${sampleSkuId}'>, [Ano-Mes]={'2026-09'}>} [Quantidade Produto])` } },
                    { "qDef": { "qDef": `Sum({1<Produto_ID={'${sampleSkuId}'>, [Ano-Mes]={'2026-08'}>} [Quantidade Produto]) / 31` } }
                ],
                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 25, "qWidth": 6 }],
                "qSuppressZero": true
            }
        }]);
        const hStore = storeSkuObj.result.qReturn.qHandle;
        const lStore = await send("GetLayout", hStore, []);
        const stores = lStore.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
        report.store_distribution = stores.map(r => ({
            filial_id: r[0]?.qText,
            filial_nome: r[1]?.qText,
            municipio: r[2]?.qText,
            saldo_loja: r[3]?.qNum,
            qtd_vendida_set: r[4]?.qNum,
            giro_diario: r[5]?.qNum,
            dias_estoque: (r[5]?.qNum && r[5]?.qNum > 0) ? Math.round((r[3]?.qNum || 0) / r[5]?.qNum * 10) / 10 : (r[3]?.qNum > 0 ? 999 : 0)
        }));

        ws.close();
    } catch(err) {
        report.error = err.message || String(err);
    }
    return report;
}"""

async def run():
    print("Iniciando probe detalhado de SKU x Filiais x Estoque...")
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
            res = await page.evaluate(JS_TEST_SKU_LOJA)
            print("Resultado:")
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except Exception as e:
            print("Erro:", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
