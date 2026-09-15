import asyncio, sys, json
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

QLIK_CLOUD_HOST = "fsj.us.qlikcloud.com"
STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"

APPS = [
    {"name": "Vendas Análise - Analítico", "id": "dcfc3ede-5eab-407c-a9ce-12b546eb5bdf"},
    {"name": "Acompanhamento Vendas", "id": "bd585cf0-316d-4173-aef1-81f9daa9125c"},
    {"name": "Indicadores de Vendas", "id": "dc8160b3-bafe-4040-a42e-4916ee9c463c"},
    {"name": "Vendas Análise - Comparativo", "id": "10fece07-9ab7-415c-89d6-e0a8c395aefe"},
    {"name": "F10 - Resumo Produto", "id": "532f1821-c7b2-4028-b1b7-621bbbd7cb72"}
]

async def check_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await context.new_page()
        await page.goto(f"https://{QLIK_CLOUD_HOST}/analytics/home", timeout=60000)
        await page.wait_for_timeout(4000)
        
        results = []
        for app in APPS:
            app_id = app['id']
            app_name = app['name']
            
            raw_js = f"""async () => {{
                const appId = "{app_id}";
                const csrfRes = await fetch('/api/v1/csrf-token');
                const csrfToken = csrfRes.headers.get('qlik-csrf-token');
                const wsUrl = `wss://${{window.location.host}}/app/${{encodeURIComponent(appId)}}?qlik-csrf-token=${{csrfToken}}`;

                return new Promise((resolve) => {{
                    const ws = new WebSocket(wsUrl);
                    let msgId = 1;
                    const pending = {{}};

                    function send(method, handle, params) {{
                        return new Promise((res, rej) => {{
                            const id = msgId++;
                            pending[id] = {{ res, rej }};
                            ws.send(JSON.stringify({{ "jsonrpc": "2.0", "id": id, "method": method, "handle": handle, "params": params }}));
                        }});
                    }}

                    ws.onopen = async () => {{
                        try {{
                            const openRes = await send("OpenDoc", -1, [appId]);
                            const docHandle = openRes.result.qReturn.qHandle;

                            // Field list
                            const flObj = await send("CreateSessionObject", docHandle, [{{
                                "qInfo": {{ "qType": "FieldList" }},
                                "qFieldListDef": {{ "qShowSystem": false, "qShowHidden": true }}
                            }}]);
                            const flHandle = flObj.result.qReturn.qHandle;
                            const flLayout = await send("GetLayout", flHandle, []);
                            const fields = (flLayout.result.qLayout.qFieldList.qItems || []).map(f => f.qName);

                            // Eval max date
                            let maxDate = null;
                            for (const dateField of ['Data Venda', 'Data', 'Dt_Venda', 'DataHora', 'Dia']) {{
                                if (fields.includes(dateField)) {{
                                    const evalRes = await send("Evaluate", docHandle, [`Date(Max([${{dateField}}]), 'DD/MM/YYYY')`]);
                                    maxDate = `${{dateField}}: ${{evalRes.result.qReturn}}`;
                                    break;
                                }}
                            }}

                            // Check hora
                            let horaField = fields.find(f => ['Hora', 'Hora Venda', 'Hora_Venda', 'DataHora', 'HoraMinuto'].includes(f));

                            ws.close();
                            resolve({{ name: "{app_name}", id: appId, maxDate, horaField, fieldsCount: fields.length, fields }});
                        }} catch(e) {{
                            ws.close();
                            resolve({{ name: "{app_name}", id: appId, error: String(e) }});
                        }}
                    }};

                    ws.onmessage = (event) => {{
                        const msg = JSON.parse(event.data);
                        if (msg.id && pending[msg.id]) {{
                            const {{ res, rej }} = pending[msg.id];
                            delete pending[msg.id];
                            if (msg.error) rej(msg.error);
                            else res(msg);
                        }}
                    }};

                    setTimeout(() => {{ ws.close(); resolve({{ name: "{app_name}", id: appId, error: 'timeout' }}); }}, 20000);
                }});
            }}"""
            try:
                res = await page.evaluate(raw_js)
                results.append(res)
            except Exception as e:
                results.append({"name": app_name, "id": app_id, "error": str(e)})

        await browser.close()
        return results

if __name__ == '__main__':
    res = asyncio.run(check_all())
    print("\n--- RESUMO DE TODOS OS APPS NO QLIK CLOUD ---")
    for r in res:
        print(f"\nApp: {r.get('name')} (ID: {r.get('id')})")
        if 'error' in r:
            print(f"  ❌ Erro: {r.get('error')}")
        else:
            print(f"  📅 MaxDate: {r.get('maxDate')}")
            print(f"  ⏰ HoraField: {r.get('horaField')}")
            print(f"  📊 Total Campos: {r.get('fieldsCount')}")
            # Campos de interesse
            interesting = [f for f in r.get('fields', []) if any(k in f.lower() for k in ['canal', 'hora', 'minuto', 'tempo', 'online', 'ecommerce'])]
            print(f"  🔍 Campos Relevantes: {interesting}")
