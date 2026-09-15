import asyncio, json
from playwright.async_api import async_playwright

STORAGE_STATE = r'c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json'
APPS = [
    {'name': 'Indicadores de Vendas', 'id': 'dc8160b3-bafe-4040-a42e-4916ee9c463c'},
    {'name': 'Vendas Análise - Analítico', 'id': 'dcfc3ede-5eab-407c-a9ce-12b546eb5bdf'},
    {'name': 'Vendas Análise - Comparativo', 'id': '10fece07-9ab7-415c-89d6-e0a8c395aefe'},
    {'name': 'Acompanhamento Vendas', 'id': 'bd585cf0-316d-4173-aef1-81f9daa9125c'}
]

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await context.new_page()
        await page.goto('https://fsj.us.qlikcloud.com/analytics/home', timeout=60000)
        
        raw_js = """async (apps) => {
            const csrfRes = await fetch('/api/v1/csrf-token');
            const csrfToken = csrfRes.headers.get('qlik-csrf-token');
            
            async function getReload(a) {
                const wsUrl = "wss://" + window.location.host + "/app/" + encodeURIComponent(a.id) + "?qlik-csrf-token=" + csrfToken;
                return new Promise((resolve) => {
                    const ws = new WebSocket(wsUrl);
                    let id = 1;
                    const pend = {};
                    ws.onmessage = (e) => {
                        const d = JSON.parse(e.data);
                        if (d.id && pend[d.id]) {
                            pend[d.id](d);
                            delete pend[d.id];
                        }
                    };
                    ws.onopen = async () => {
                        const send = (m, h, p) => new Promise(r => {
                            pend[id] = r;
                            ws.send(JSON.stringify({"jsonrpc": "2.0", "id": id++, "method": m, "handle": h, "params": p}));
                        });
                        const openRes = await send("OpenDoc", -1, [a.id]);
                        const doc = openRes.result ? openRes.result.qReturn.qHandle : null;
                        if (!doc) {
                            ws.close();
                            resolve({ name: a.name, id: a.id, error: "OpenDoc failed" });
                            return;
                        }
                        const layRes = await send("GetAppLayout", doc, []);
                        const lay = layRes.result ? layRes.result.qLayout : {};
                        ws.close();
                        resolve({ name: a.name, id: a.id, reloadTime: lay.qLastReloadTime, title: lay.qTitle });
                    };
                    setTimeout(() => { ws.close(); resolve({ name: a.name, id: a.id, error: "timeout" }); }, 15000);
                });
            }
            const out = [];
            for (const a of apps) {
                out.push(await getReload(a));
            }
            return out;
        }"""
        res = await page.evaluate(raw_js, APPS)
        await browser.close()
        return res

if __name__ == '__main__':
    res = asyncio.run(check())
    for r in res:
        print(r)
