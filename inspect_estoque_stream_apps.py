import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"

STREAM_APPS = [
    {"name": "Compras x Vendas", "id": "262099a2-37ba-4c6f-8efd-46e31a9172e4"},
    {"name": "F7", "id": "6ca61bc5-e8bf-47a5-bb1f-9087b864c638"},
    {"name": "Excesso Produtos", "id": "a10b4a09-a6fe-42cf-8f62-680a9d70aa89"},
    {"name": "Produto em Trânsito", "id": "d86e5e19-6488-4c8b-bd30-90dc497dc610"},
    {"name": "Vendas PV", "id": "a07d503b-790c-4a70-925c-10dca1590d05"},
    {"name": "Controle Remanejos", "id": "391643ee-edf9-4bc8-b8b2-84149c6787fe"}
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        ctx = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD}
        )
        page = await ctx.new_page()
        # Navega para o hub para abrir sessão autenticada
        await page.goto(f"{QLIK_URL}/hub/stream/9befd6bf-7c87-43bf-b756-93c8fbf61fe2", timeout=60000)
        await page.wait_for_timeout(5000)

        results = {}

        for app_info in STREAM_APPS:
            app_id = app_info["id"]
            app_name = app_info["name"]
            print(f"Inspecionando {app_name} ({app_id})...", flush=True)

            try:
                res = await page.evaluate("""async (targetAppId) => {
                    return new Promise((resolve) => {
                        const ws = new WebSocket(`wss://${window.location.host}/app/${encodeURIComponent(targetAppId)}?reloadUri=https://${window.location.host}/`);
                        let id = 1;
                        const pending = {};
                        ws.onmessage = e => {
                            const m = JSON.parse(e.data);
                            if (m.id && pending[m.id]) { pending[m.id](m); delete pending[m.id]; }
                        };
                        function send(method, handle, params) {
                            return new Promise(r => { const mid = id++; pending[mid] = r; ws.send(JSON.stringify({ jsonrpc: '2.0', id: mid, method, handle, params })); });
                        }
                        ws.onopen = async () => {
                            try {
                                const o = await send("OpenDoc", -1, [targetAppId]);
                                const docHandle = o.result.qReturn.qHandle;

                                // 1. Medidas Mestres
                                const cM = await send("CreateSessionObject", docHandle, [{
                                    qInfo: { qType: "MeasureList" },
                                    qMeasureListDef: { qType: "measure", qData: { title: "/title", qMeasure: "/qMeasure" } }
                                }]);
                                const lM = await send("GetLayout", cM.result.qReturn.qHandle, []);
                                const measures = (lM.result.qLayout.qMeasureList?.qItems || []).map(x => ({
                                    title: x.qMetaDef?.title,
                                    expr: x.qData?.qMeasure?.qDef
                                }));

                                // 2. Folhas (Sheets)
                                const cS = await send("CreateSessionObject", docHandle, [{
                                    qInfo: { qType: "SheetList" },
                                    qAppObjectListDef: { qType: "sheet", qData: { title: "/qMetaDef/title", description: "/qMetaDef/description" } }
                                }]);
                                const lS = await send("GetLayout", cS.result.qReturn.qHandle, []);
                                const sheets = (lS.result.qLayout.qAppObjectList?.qItems || []).map(x => ({
                                    title: x.qMetaDef?.title,
                                    desc: x.qMetaDef?.description
                                }));

                                // 3. Avalia Mounjaro 5mg (10046653)
                                const evalStock = {};
                                const testExprs = ["Sum(Qt_Estoque)", "Sum([Estoque])", "Sum([Quantidade Saldo])", "Sum(Qt_Saldo)", "Sum(Qt_Disponivel)"];
                                for (const te of testExprs) {
                                    try {
                                        const ev = await send("Evaluate", docHandle, [`Sum({1<Produto_ID={'10046653'}>} ${te.replace('Sum(', '')}`]);
                                        if (ev.result?.qReturn && ev.result.qReturn !== '0' && ev.result.qReturn !== '-') {
                                            evalStock[te] = ev.result.qReturn;
                                        }
                                    } catch(e) {}
                                }

                                ws.close();
                                resolve({ measures, sheets, evalStock });
                            } catch(e) {
                                ws.close();
                                resolve({ error: e.message });
                            }
                        };
                    });
                }""", app_id)
                results[app_name] = res
            except Exception as e:
                results[app_name] = {"error": str(e)}

        print("=== RESULTADOS DOS APPS DA STREAM ESTOQUE ===")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        with open("stream_estoque_analysis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
