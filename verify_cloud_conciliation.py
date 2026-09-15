import asyncio, json
from playwright.async_api import async_playwright

STORAGE_STATE = r'c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json'
APP_ID = 'dc8160b3-bafe-4040-a42e-4916ee9c463c'

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await context.new_page()
        await page.goto('https://fsj.us.qlikcloud.com/analytics/home', timeout=60000)
        
        raw_js = """async () => {
            const csrfRes = await fetch('/api/v1/csrf-token');
            const csrfToken = csrfRes.headers.get('qlik-csrf-token');
            const wsUrl = "wss://" + window.location.host + "/app/" + encodeURIComponent("dc8160b3-bafe-4040-a42e-4916ee9c463c") + "?qlik-csrf-token=" + csrfToken;
            return new Promise((resolve) => {
                const ws = new WebSocket(wsUrl);
                let id = 1;
                const pend = {};
                ws.onmessage = (e) => {
                    const d = JSON.parse(e.data);
                    if (d.id && pend[d.id]) { pend[d.id](d); delete pend[d.id]; }
                };
                ws.onopen = async () => {
                    const send = (m, h, p) => new Promise(r => { pend[id] = r; ws.send(JSON.stringify({"jsonrpc":"2.0", "id": id++, "method": m, "handle": h, "params": p})); });
                    const doc = (await send("OpenDoc", -1, ["dc8160b3-bafe-4040-a42e-4916ee9c463c"])).result.qReturn.qHandle;
                    
                    const qProp = {
                        qInfo: { qType: "test_sum" },
                        qHyperCubeDef: {
                            qDimensions: [{ qDef: { qFieldDefs: ["TIPO_VENDA_DESCRICAO"] } }],
                            qMeasures: [{ qDef: { qDef: "Sum({1<INCLUSAO_DATA={'15/09/2026'}>} [VALOR_VENDA_LIQUIDA_M])" } }],
                            qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 20, qWidth: 2 }]
                        }
                    };
                    const obj = (await send("CreateSessionObject", doc, [qProp])).result.qReturn.qHandle;
                    const lay = (await send("GetLayout", obj, [])).result.qLayout;
                    const matrix = lay.qHyperCube.qDataPages[0].qMatrix;
                    ws.close();
                    resolve(matrix.map(r => ({ canal: r[0].qText, valor: r[1].qNum })));
                };
            });
        }"""
        res = await page.evaluate(raw_js)
        await browser.close()
        return res

if __name__ == '__main__':
    res = asyncio.run(verify())
    tot_digital = 0.0
    tot_figital = 0.0
    print("=== CONCILIAÇÃO DIRETA COM QLIK CLOUD SAAS ===")
    for r in res:
        c = r['canal']
        v = r['valor'] or 0.0
        if c in ['APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'E-commerce']:
            tot_digital += v
            print(f"  {c:20}: R$ {v:12,.2f}")
        elif c == 'Figital':
            tot_figital += v
            print(f"  {c:20}: R$ {v:12,.2f}")
    print("----------------------------------------------")
    print(f"  TOTAL DIGITAL (Sem Figital): R$ {tot_digital:12,.2f}")
    print(f"  FIGITAL (Exclusivo):         R$ {tot_figital:12,.2f}")
    print(f"  TOTAL CONSOLIDADO (Com Fig): R$ {tot_digital + tot_figital:12,.2f}")
