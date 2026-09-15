import asyncio, sys, json
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"
APP_ID = "dc8160b3-bafe-4040-a42e-4916ee9c463c"

async def main():
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
                        const evalMin = await send('Evaluate', doc, ["Date(Min([INCLUSAO_DATA]), 'DD/MM/YYYY')"]);
                        const evalMax = await send('Evaluate', doc, ["Date(Max([INCLUSAO_DATA]), 'DD/MM/YYYY')"]);
                        
                        const dObj = (await send('CreateSessionObject', doc, [{
                            "qInfo": { "qType": "d" },
                            "qHyperCubeDef": {
                                "qDimensions": [{ "qDef": { "qFieldDefs": ["INCLUSAO_DATA"] } }],
                                "qMeasures": [
                                    { "qDef": { "qDef": "Sum({<TIPO_VENDA_DESCRICAO={'APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'E-commerce'}>} [VALOR_VENDA_LIQUIDA_M])" } },
                                    { "qDef": { "qDef": "Sum({<TIPO_VENDA_DESCRICAO={'Figital'}>} [VALOR_VENDA_LIQUIDA_M])" } }
                                ],
                                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 100, "qWidth": 3 }]
                            }
                        }])).result.qReturn.qHandle;
                        const dLay = (await send('GetLayout', dObj, [])).result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
                        ws.close();
                        resolve({
                            minDate: evalMin.result.qReturn,
                            maxDate: evalMax.result.qReturn,
                            datas: dLay.map(r => ({ data: r[0].qText, digital: r[1].qNum !== 'NaN' && typeof r[1].qNum === 'number' ? r[1].qNum : 0, figital: r[2].qNum !== 'NaN' && typeof r[2].qNum === 'number' ? r[2].qNum : 0 }))
                        });
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
        print('Período:', res.get('periodo'))
        print('Datas disponíveis:')
        for d in sorted(res.get('datas', []), key=lambda x: str(x['data'])):
            print(f"  {d['data']}: Digital R$ {d['digital']:12,.2f} | Figital R$ {d['figital']:12,.2f}")

if __name__ == '__main__':
    asyncio.run(main())
