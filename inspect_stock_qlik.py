"""
inspect_stock_qlik.py
Conecta ao Qlik Sense Enterprise e pesquisa campos relacionados a Estoque / Ruptura / Saldo:
1. Dentro do app atual 'E-Commerce x Rede' (671fa4f4-eb7d-418f-b4c9-936e87d8011d)
2. Dentro do app 'Ruptura' (4c210d43-3ea6-45ea-994f-ced22d3ceb0d)
3. Dentro do app 'Relatório Estoque Final' (936a28fb-245f-4f19-b285-420535685c43)
4. Dentro do app 'E-Commerce - Venda por Produto' (fad5c88c-dd80-444d-bf2d-bf853d0d8243)
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"

APPS_TO_CHECK = [
    {"name": "E-Commerce x Rede (Atual)", "id": "671fa4f4-eb7d-418f-b4c9-936e87d8011d"},
    {"name": "Ruptura", "id": "4c210d43-3ea6-45ea-994f-ced22d3ceb0d"},
    {"name": "Relatório Estoque Final", "id": "936a28fb-245f-4f19-b285-420535685c43"},
    {"name": "E-Commerce - Venda por Produto", "id": "fad5c88c-dd80-444d-bf2d-bf853d0d8243"}
]

JS_INSPECT = """async (appId) => {
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
                
                // 1. Pega lista de campos via GetFieldList
                const fieldListRes = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "FieldList" },
                    "qFieldListDef": { "qShowHidden": true }
                }]);
                const fHandle = fieldListRes.result.qReturn.qHandle;
                const fLayout = await send("GetLayout", fHandle, []);
                const fields = (fLayout.result.qLayout.qFieldList.qItems || []).map(f => f.qName);

                // 2. Pega medidas mestres (master measures)
                const measureListRes = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "MeasureList" },
                    "qMeasureListDef": { "qType": "measure", "qData": { "title": "/qMetaDef/title", "tags": "/qMetaDef/tags" } }
                }]);
                const mHandle = measureListRes.result.qReturn.qHandle;
                const mLayout = await send("GetLayout", mHandle, []);
                const measures = (mLayout.result.qLayout.qMeasureList.qItems || []).map(m => m.qMeta?.title || m.qInfo?.qId);

                ws.close();
                resolve({
                    success: true,
                    fieldsCount: fields.length,
                    fields: fields,
                    measures: measures
                });
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
    print("=" * 75)
    print("  INVESTIGAÇÃO DE ESTOQUE / RUPTURA NO QLIK SENSE ENTERPRISE")
    print("=" * 75)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD}
        )
        page = await context.new_page()
        print("Autenticando no Qlik Sense...", flush=True)
        await page.goto(f"{QLIK_URL}/sense/app/{APPS_TO_CHECK[0]['id']}", timeout=60000)
        try:
            await page.wait_for_selector('.qv-panel-sheet', timeout=20000)
        except Exception:
            await page.wait_for_timeout(4000)

        results = {}
        for app in APPS_TO_CHECK:
            print(f"\nInspecionando App: {app['name']} (ID: {app['id']})...", flush=True)
            res = await page.evaluate(JS_INSPECT, app['id'])
            results[app['name']] = res
            if res.get("success"):
                fields = res.get("fields", [])
                measures = res.get("measures", [])
                stock_fields = [f for f in fields if any(k in f.lower() for k in ["estoq", "rupt", "sald", "disp", "deposito", "loja_estoq", "saldo"])]
                stock_measures = [m for m in measures if any(k in str(m).lower() for k in ["estoq", "rupt", "sald", "disp"])]
                print(f"  -> Total de Campos: {len(fields)}")
                print(f"  -> Campos Estoque/Ruptura/Saldo ({len(stock_fields)}): {stock_fields}")
                print(f"  -> Medidas Mestres Estoque ({len(stock_measures)}): {stock_measures}")
            else:
                print(f"  -> Erro ao inspecionar: {res.get('error')}")

        await browser.close()

    with open("scratch_stock_inspection.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nResultados salvos em scratch_stock_inspection.json")

if __name__ == "__main__":
    asyncio.run(run())
