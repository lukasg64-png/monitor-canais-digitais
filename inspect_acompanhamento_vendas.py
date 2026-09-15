import asyncio, sys, json
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

QLIK_CLOUD_HOST = "fsj.us.qlikcloud.com"
STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"
APP_ID = "bd585cf0-316d-4173-aef1-81f9daa9125c"  # Acompanhamento Vendas

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await context.new_page()
        await page.goto(f"https://{QLIK_CLOUD_HOST}/analytics/home", timeout=60000)
        await page.wait_for_timeout(4000)
        
        raw_js = """async () => {
            const appId = "bd585cf0-316d-4173-aef1-81f9daa9125c";
            const csrfRes = await fetch('/api/v1/csrf-token');
            const csrfToken = csrfRes.headers.get('qlik-csrf-token');
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

                ws.onopen = async () => {
                    try {
                        const openRes = await send("OpenDoc", -1, [appId]);
                        const docHandle = openRes.result.qReturn.qHandle;

                        // Field list
                        const flObj = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "FieldList" },
                            "qFieldListDef": { "qShowSystem": false, "qShowHidden": true }
                        }]);
                        const flHandle = flObj.result.qReturn.qHandle;
                        const flLayout = await send("GetLayout", flHandle, []);
                        const fields = (flLayout.result.qLayout.qFieldList.qItems || []).map(f => f.qName);

                        // Max Data Venda e Max Hora Venda hoje
                        const evalMaxData = await send("Evaluate", docHandle, ["Date(Max([Data Venda]), 'DD/MM/YYYY')"]);
                        const evalMaxHora = await send("Evaluate", docHandle, ["Max([Hora Venda])"]);

                        // Procurar campo de Canal
                        let canalField = fields.find(f => f.toLowerCase().includes('canal'));

                        // Canais únicos e venda hoje
                        let canaisHoje = [];
                        if (canalField) {
                            const cObj = await send("CreateSessionObject", docHandle, [{
                                "qInfo": { "qType": "q_canais_hoje" },
                                "qHyperCubeDef": {
                                    "qDimensions": [{ "qDef": { "qFieldDefs": [canalField] } }],
                                    "qMeasures": [
                                        { "qDef": { "qDef": "Sum({1<[Data Venda]={'$(=Date(Max([Data Venda]), \\'DD/MM/YYYY\\'))'}>} [Venda])" } },
                                        { "qDef": { "qDef": "Sum({1<[Data Venda]={'$(=Date(Max([Data Venda]), \\'DD/MM/YYYY\\'))'}>} [Quantidade])" } }
                                    ],
                                    "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 50, "qWidth": 3 }],
                                    "qSuppressZero": false
                                }
                            }]);
                            const lObj = await send("GetLayout", cObj.result.qReturn.qHandle, []);
                            canaisHoje = (lObj.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => ({
                                canal: r[0].qText,
                                venda: r[1].qNum !== 'NaN' && typeof r[1].qNum === 'number' ? r[1].qNum : 0,
                                qtd: r[2].qNum !== 'NaN' && typeof r[2].qNum === 'number' ? r[2].qNum : 0
                            }));
                        }

                        // Horas únicas com venda hoje
                        const hObj = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "q_horas_hoje" },
                            "qHyperCubeDef": {
                                "qDimensions": [{ "qDef": { "qFieldDefs": ["Hora Venda"] } }],
                                "qMeasures": [
                                    { "qDef": { "qDef": "Sum({1<[Data Venda]={'$(=Date(Max([Data Venda]), \\'DD/MM/YYYY\\'))'}>} [Venda])" } }
                                ],
                                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 30, "qWidth": 2 }],
                                "qSuppressZero": true
                            }
                        }]);
                        const lH = await send("GetLayout", hObj.result.qReturn.qHandle, []);
                        const horasHoje = (lH.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => ({
                            hora: r[0].qText,
                            venda: r[1].qNum !== 'NaN' && typeof r[1].qNum === 'number' ? r[1].qNum : 0
                        })).sort((a, b) => parseInt(a.hora) - parseInt(b.hora));

                        ws.close();
                        resolve({
                            fields,
                            maxData: evalMaxData.result.qReturn,
                            maxHora: evalMaxHora.result.qReturn,
                            canalField,
                            canaisHoje,
                            horasHoje
                        });
                    } catch(e) {
                        ws.close();
                        resolve({ error: String(e) });
                    }
                };

                ws.onmessage = (event) => {
                    const msg = JSON.parse(event.data);
                    if (msg.id && pending[msg.id]) {
                        const { res, rej } = pending[msg.id];
                        delete pending[msg.id];
                        if (msg.error) rej(msg.error);
                        else res(msg);
                    }
                };

                setTimeout(() => { ws.close(); resolve({ error: 'timeout' }); }, 25000);
            });
        }"""

        res = await page.evaluate(raw_js)
        await browser.close()
        return res

if __name__ == '__main__':
    r = asyncio.run(inspect())
    print("\n--- APP ACOMPANHAMENTO VENDAS (QLIK CLOUD) ---")
    print(f"MaxData: {r.get('maxData')} | MaxHora: {r.get('maxHora')}")
    print(f"Campo de Canal: {r.get('canalField')}")
    print(f"\nTodos os {len(r.get('fields', []))} campos:")
    for f in sorted(r.get('fields', [])):
        print(f"  - {f}")
    print("\nCanais Hoje (15/09/2026):")
    for c in r.get('canaisHoje', []):
        print(f"  🛒 {c['canal']:25s}: R$ {c['venda']:12,.2f} ({c['qtd']} un)")
    print("\nVendas por Hora Hoje:")
    for h in r.get('horasHoje', []):
        print(f"  ⏰ {h['hora']}h: R$ {h['venda']:12,.2f}")
