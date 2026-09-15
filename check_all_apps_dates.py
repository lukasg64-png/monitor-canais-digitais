import asyncio, sys, json
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

QLIK_CLOUD_HOST = "fsj.us.qlikcloud.com"
STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"

APPS = [
    {"name": "Indicadores de Vendas", "id": "dc8160b3-bafe-4040-a42e-4916ee9c463c"},
    {"name": "Vendas Análise - Analítico", "id": "dcfc3ede-5eab-407c-a9ce-12b546eb5bdf"},
    {"name": "Vendas Análise - Comparativo", "id": "10fece07-9ab7-415c-89d6-e0a8c395aefe"},
    {"name": "Acompanhamento Vendas", "id": "bd585cf0-316d-4173-aef1-81f9daa9125c"}
]

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await context.new_page()
        await page.goto(f"https://{QLIK_CLOUD_HOST}/analytics/home", timeout=60000)
        await page.wait_for_timeout(3000)
        
        raw_js = """async (apps) => {
            const csrfRes = await fetch('/api/v1/csrf-token');
            const csrfToken = csrfRes.headers.get('qlik-csrf-token');

            async function queryApp(appInfo) {
                const appId = appInfo.id;
                const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?qlik-csrf-token=${csrfToken}`;
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
                    ws.onmessage = (event) => {
                        const msg = JSON.parse(event.data);
                        if (msg.id && pending[msg.id]) {
                            const { res, rej } = pending[msg.id];
                            delete pending[msg.id];
                            if (msg.error) rej(msg.error);
                            else res(msg);
                        }
                    };
                    ws.onopen = async () => {
                        try {
                            const openRes = await send("OpenDoc", -1, [appId]);
                            const docHandle = openRes.result.qReturn.qHandle;

                            const flObj = await send("CreateSessionObject", docHandle, [{
                                "qInfo": { "qType": "FieldList" },
                                "qFieldListDef": { "qShowSystem": false, "qShowHidden": false }
                            }]);
                            const flLay = await send("GetLayout", flObj.result.qReturn.qHandle, []);
                            const fields = (flLay.result.qLayout.qFieldList.qItems || []).map(f => f.qName);

                            // Find date, hour, canal fields
                            const dateFields = fields.filter(f => /data/i.test(f));
                            const hourFields = fields.filter(f => /hora/i.test(f));
                            const canalFields = fields.filter(f => /canal|tipo.*venda/i.test(f));

                            let maxDate = null;
                            if (dateFields.length > 0) {
                                try {
                                    const evalD = await send("Evaluate", docHandle, [`Date(Max([${dateFields[0]}]), 'DD/MM/YYYY')`]);
                                    maxDate = evalD.result.qReturn;
                                } catch(e){}
                            }

                            // Distinct values of canal fields
                            let canalValues = {};
                            for (const cf of canalFields) {
                                try {
                                    const cObj = await send("CreateSessionObject", docHandle, [{
                                        "qInfo": { "qType": "c_" + cf },
                                        "qHyperCubeDef": {
                                            "qDimensions": [{ "qDef": { "qFieldDefs": [cf] } }],
                                            "qMeasures": [{ "qDef": { "qDef": "Count(1)" } }],
                                            "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 30, "qWidth": 2 }]
                                        }
                                    }]);
                                    const cLay = await send("GetLayout", cObj.result.qReturn.qHandle, []);
                                    canalValues[cf] = (cLay.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r[0].qText);
                                } catch(e){}
                            }

                            ws.close();
                            resolve({
                                name: appInfo.name,
                                id: appId,
                                fieldsCount: fields.length,
                                dateFields,
                                hourFields,
                                maxDate,
                                canalFields,
                                canalValues
                            });
                        } catch(e) {
                            ws.close();
                            resolve({ name: appInfo.name, id: appId, error: String(e) });
                        }
                    };
                    setTimeout(() => { ws.close(); resolve({ name: appInfo.name, id: appId, error: 'timeout' }); }, 20000);
                });
            }

            const results = [];
            for (const a of apps) {
                results.push(await queryApp(a));
            }
            return results;
        }"""

        res = await page.evaluate(raw_js, APPS)
        await browser.close()
        return res

if __name__ == '__main__':
    results = asyncio.run(inspect())
    for r in results:
        print(f"\n==========================================")
        print(f"APP: {r.get('name')} ({r.get('id')})")
        if 'error' in r:
            print(f"  ❌ Error: {r['error']}")
            continue
        print(f"  MaxDate ({r.get('dateFields', [''])[0]}): {r.get('maxDate')}")
        print(f"  Campos Data: {r.get('dateFields')}")
        print(f"  Campos Hora: {r.get('hourFields')}")
        print(f"  Campos Canal/Tipo Venda: {r.get('canalFields')}")
        print(f"  Valores dos Canais:")
        for cf, vals in r.get('canalValues', {}).items():
            print(f"    - {cf}: {vals}")
