import asyncio, sys, json
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

QLIK_CLOUD_HOST = "fsj.us.qlikcloud.com"
STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"
USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
APP_ID = "dcfc3ede-5eab-407c-a9ce-12b546eb5bdf"  # Vendas Análise - Analítico

async def inspect_fields():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await context.new_page()
        print("Navegando para o Qlik Cloud...", flush=True)
        await page.goto(f"https://{QLIK_CLOUD_HOST}/analytics/home", timeout=60000)
        
        try:
            user_input = await page.wait_for_selector('#username', timeout=12000)
            if user_input:
                print("Identificado formulário do Keycloak SSO. Preenchendo credenciais...", flush=True)
                await page.fill('#username', USERNAME)
                await page.fill('#password', PASSWORD)
                await page.click('#kc-login')
                print("Credenciais enviadas. Aguardando retorno ao Qlik Cloud...", flush=True)
                await page.wait_for_url(f"**{QLIK_CLOUD_HOST}/analytics/**", timeout=60000)
                print("✅ Autenticação SSO concluída com sucesso!", flush=True)
                await page.wait_for_timeout(4000)
                await context.storage_state(path=STORAGE_STATE)
        except Exception:
            print("Sessão ativa mantida.", flush=True)

        print("Aguardando estabilização da página do Qlik Cloud...", flush=True)
        await page.wait_for_timeout(4000)
        
        raw_js = """async () => {
            const appId = "dcfc3ede-5eab-407c-a9ce-12b546eb5bdf";
            const csrfRes = await fetch('/api/v1/csrf-token');
            const csrfToken = csrfRes.headers.get('qlik-csrf-token');
            const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?qlik-csrf-token=${csrfToken}`;

            return new Promise((resolve, reject) => {
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

                        // Obter lista de campos
                        const flObj = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "FieldList" },
                            "qFieldListDef": { "qShowSystem": false, "qShowHidden": true }
                        }]);
                        const flHandle = flObj.result.qReturn.qHandle;
                        const flLayout = await send("GetLayout", flHandle, []);
                        const fields = (flLayout.result.qLayout.qFieldList.qItems || []).map(f => f.qName);

                        // Avaliar Max Data de Vendas
                        const evalMaxData = await send("Evaluate", docHandle, ["Max([Data Venda])"]);
                        const evalMaxDataStr = await send("Evaluate", docHandle, ["Date(Max([Data Venda]), 'DD/MM/YYYY')"]);

                        // Pegar os últimos 5 dias com venda no app
                        const cDias = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "q_ultimos_dias" },
                            "qHyperCubeDef": {
                                "qDimensions": [{ "qDef": { "qFieldDefs": ["Data Venda"] } }],
                                "qMeasures": [
                                    { "qDef": { "qDef": "Sum([Venda])" } }
                                ],
                                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 40, "qWidth": 2 }],
                                "qSuppressZero": true
                            }
                        }]);
                        const hDias = cDias.result.qReturn.qHandle;
                        const lDias = await send("GetLayout", hDias, []);
                        const mDias = (lDias.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => ({
                            data: r[0].qText,
                            venda: r[1].qNum !== 'NaN' && typeof r[1].qNum === 'number' ? r[1].qNum : 0
                        }));

                        ws.close();
                        resolve({ 
                            fields, 
                            maxData: evalMaxData.result.qReturn,
                            maxDataStr: evalMaxDataStr.result.qReturn,
                            ultimosDias: mDias.slice(-10)
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

                setTimeout(() => { ws.close(); resolve({ error: 'timeout' }); }, 40000);
            });
        }"""

        res = None
        for attempt in range(3):
            try:
                await page.wait_for_timeout(1000)
                res = await page.evaluate(raw_js)
                if res and 'fields' in res:
                    break
            except Exception as e:
                print(f"Tentativa {attempt+1}/3 erro: {e}")
                await page.wait_for_timeout(3000)

        await browser.close()
        return res

if __name__ == '__main__':
    r = asyncio.run(inspect_fields())
    print("\n--- RESULTADO DA INSPEÇÃO NO CLOUD ---")
    print("MaxData:", r.get('maxDataStr'))
    print("\nÚltimos Dias com venda na base:")
    for d in r.get('ultimosDias', []):
        print(f"  📅 {d.get('data')}: R$ {d.get('venda', 0):,.2f}")
    
    hora_fields = [f for f in r.get('fields', []) if any(k in f.lower() for k in ['hor', 'time', 'minut', 'data', 'dt', 'periodo'])]
    print("\nCampos de Data/Hora encontrados no App:", hora_fields)
