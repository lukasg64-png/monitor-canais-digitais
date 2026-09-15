import asyncio, sys, json
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"
APP_ID = "dc8160b3-bafe-4040-a42e-4916ee9c463c"

async def check_stock():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        c = await b.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await c.new_page()
        await page.goto("https://fsj.us.qlikcloud.com/analytics/home", timeout=60000)
        await page.wait_for_timeout(3000)
        
        raw_js = """async () => {
            const appId = 'dc8160b3-bafe-4040-a42e-4916ee9c463c';
            const csrfRes = await fetch('/api/v1/csrf-token');
            const csrfToken = csrfRes.headers.get('qlik-csrf-token');
            const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?qlik-csrf-token=${csrfToken}`;
            return new Promise((resolve) => {
                const ws = new WebSocket(wsUrl);
                let id = 1;
                const pend = {};
                const send = (m, h, p) => new Promise((r, j) => { pend[id] = {r, j}; ws.send(JSON.stringify({jsonrpc:'2.0', id: id++, method: m, handle: h, params: p})); });
                ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.id && pend[d.id]) { pend[d.id].r(d); delete pend[d.id]; } };
                ws.onopen = async () => {
                    try {
                        const doc = (await send('OpenDoc', -1, [appId])).result.qReturn.qHandle;
                        const evalStock = await send('Evaluate', doc, ["Sum([Qt_Estoque])"]);
                        const obj = await send('CreateSessionObject', doc, [{
                            qInfo: { qType: 's' },
                            qHyperCubeDef: {
                                qDimensions: [{ qDef: { qFieldDefs: ['Desc_Produto'] } }],
                                qMeasures: [{ qDef: { qDef: 'Sum([Qt_Estoque])' } }],
                                qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 5, qWidth: 2 }]
                            }
                        }]);
                        const lay = await send('GetLayout', obj.result.qReturn.qHandle, []);
                        const sample = (lay.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => [r[0].qText, r[1].qNum]);
                        ws.close();
                        resolve({ evalStock: evalStock.result.qReturn, sample });
                    } catch(e) {
                        ws.close();
                        resolve({ error: String(e) });
                    }
                };
                setTimeout(() => { ws.close(); resolve({ error: 'timeout' }); }, 30000);
            });
        }"""
        res = await page.evaluate(raw_js)
        await b.close()
        return res

if __name__ == '__main__':
    res = asyncio.run(check_stock())
    print("EvalStock:", res.get('evalStock'))
    print("Sample:", res.get('sample'))
