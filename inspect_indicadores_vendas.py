import asyncio, sys, json
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

QLIK_CLOUD_HOST = "fsj.us.qlikcloud.com"
STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"
APP_ID = "dc8160b3-bafe-4040-a42e-4916ee9c463c"  # Indicadores de Vendas

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await context.new_page()
        await page.goto(f"https://{QLIK_CLOUD_HOST}/analytics/home", timeout=60000)
        await page.wait_for_timeout(3000)
        
        raw_js = """async (appId) => {
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

                        // Fields
                        const flObj = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "FieldList" },
                            "qFieldListDef": { "qShowSystem": false, "qShowHidden": true }
                        }]);
                        const flLay = await send("GetLayout", flObj.result.qReturn.qHandle, []);
                        const fields = (flLay.result.qLayout.qFieldList.qItems || []).map(f => f.qName);

                        // Master measures
                        let measures = [];
                        try {
                            const mmObj = await send("CreateSessionObject", docHandle, [{
                                "qInfo": { "qType": "MeasureList" },
                                "qMeasureListDef": { "qType": "measure" }
                            }]);
                            const mmLay = await send("GetLayout", mmObj.result.qReturn.qHandle, []);
                            measures = (mmLay.result.qLayout.qMeasureList.qItems || []).map(m => ({
                                title: m.qMeta?.title,
                                expr: m.qData?.qMeasure?.qDef || m.qMeta?.qDef || ''
                            }));
                        } catch(e) {}

                        // Max Date & Max Timestamp
                        const evalDate = await send("Evaluate", docHandle, ["Date(Max([INCLUSAO_DATA]), 'DD/MM/YYYY')"]);
                        const evalTime = await send("Evaluate", docHandle, ["Max([INCLUSAO_DATA_TIME])"]);
                        const evalMaxHour = await send("Evaluate", docHandle, ["Hour(Max([INCLUSAO_DATA_TIME]))"]);

                        // Digital Channels breakdown for Today (15/09/2026)
                        const cObj = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "q_canais" },
                            "qHyperCubeDef": {
                                "qDimensions": [{ "qDef": { "qFieldDefs": ["TIPO_VENDA_DESCRICAO"] } }],
                                "qMeasures": [
                                    { "qDef": { "qDef": "Count(1)" } },
                                    { "qDef": { "qDef": "Sum({<[INCLUSAO_DATA]={'$(=Date(Max([INCLUSAO_DATA]), \\'DD/MM/YYYY\\'))'}>} [VALOR_VENDA_LIQUIDA_M])" } },
                                    { "qDef": { "qDef": "Sum({<[INCLUSAO_DATA]={'$(=Date(Max([INCLUSAO_DATA]), \\'DD/MM/YYYY\\'))'}>} [VALOR_BRUTO_M])" } },
                                    { "qDef": { "qDef": "Sum({<[INCLUSAO_DATA]={'$(=Date(Max([INCLUSAO_DATA]), \\'DD/MM/YYYY\\'))'}>} [QUANTIDADE_MERCADORIA_M])" } }
                                ],
                                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 50, "qWidth": 5 }]
                            }
                        }]);
                        const cLay = await send("GetLayout", cObj.result.qReturn.qHandle, []);
                        const canaisHoje = (cLay.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => ({
                            canal: r[0].qText,
                            count: r[1].qNum,
                            vendaLiquida: r[2].qNum !== 'NaN' && typeof r[2].qNum === 'number' ? r[2].qNum : 0,
                            vendaBruta: r[3].qNum !== 'NaN' && typeof r[3].qNum === 'number' ? r[3].qNum : 0,
                            qtd: r[4].qNum !== 'NaN' && typeof r[4].qNum === 'number' ? r[4].qNum : 0
                        }));

                        // Hour by hour for Today (using Hour(INCLUSAO_DATA_TIME))
                        const hObj = await send("CreateSessionObject", docHandle, [{
                            "qInfo": { "qType": "q_horas" },
                            "qHyperCubeDef": {
                                "qDimensions": [{ "qDef": { "qFieldDefs": ["=Hour([INCLUSAO_DATA_TIME])"] } }],
                                "qMeasures": [
                                    { "qDef": { "qDef": "Sum({<[INCLUSAO_DATA]={'$(=Date(Max([INCLUSAO_DATA]), \\'DD/MM/YYYY\\'))'}, TIPO_VENDA_DESCRICAO={'APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'E-commerce'}>} [VALOR_VENDA_LIQUIDA_M])" } },
                                    { "qDef": { "qDef": "Sum({<[INCLUSAO_DATA]={'$(=Date(Max([INCLUSAO_DATA]), \\'DD/MM/YYYY\\'))'}, TIPO_VENDA_DESCRICAO={'Figital'}>} [VALOR_VENDA_LIQUIDA_M])" } }
                                ],
                                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 30, "qWidth": 3 }]
                            }
                        }]);
                        const hLay = await send("GetLayout", hObj.result.qReturn.qHandle, []);
                        const horasHoje = (hLay.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => ({
                            hora: r[0].qText,
                            vendaDigital: r[1].qNum !== 'NaN' && typeof r[1].qNum === 'number' ? r[1].qNum : 0,
                            vendaFigital: r[2].qNum !== 'NaN' && typeof r[2].qNum === 'number' ? r[2].qNum : 0
                        })).sort((a, b) => parseInt(a.hora) - parseInt(b.hora));

                        ws.close();
                        resolve({
                            fields,
                            measures,
                            maxDate: evalDate.result.qReturn,
                            maxTime: evalTime.result.qReturn,
                            maxHour: evalMaxHour.result.qReturn,
                            canaisHoje,
                            horasHoje
                        });
                    } catch(e) {
                        ws.close();
                        resolve({ error: String(e) });
                    }
                };
                setTimeout(() => { ws.close(); resolve({ error: 'timeout' }); }, 30000);
            });
        }"""

        res = await page.evaluate(raw_js, APP_ID)
        await browser.close()
        return res

if __name__ == '__main__':
    r = asyncio.run(inspect())
    if 'error' in r:
        print(f"❌ Erro: {r['error']}")
        sys.exit(1)

    print("\n--- APP INDICADORES DE VENDAS ---")
    print(f"MaxDate: {r.get('maxDate')} | MaxTime: {r.get('maxTime')} | MaxHour: {r.get('maxHour')}")
    print(f"Total de campos: {len(r.get('fields', []))}")
    for f in sorted(r.get('fields', [])):
        print(f"  - {f}")

    print("\n--- CANAIS HOJE (15/09/2026) ---")
    for c in r.get('canaisHoje', []):
        print(f"  🛒 {c['canal']:25s} | Venda Líq: R$ {c['vendaLiquida']:12,.2f} | Venda Bruta: R$ {c['vendaBruta']:12,.2f} | Qtd: {c['qtd']:8,d}")

    print("\n--- CURVA HORÁRIA HOJE (DIGITAL x FIGITAL) ---")
    for h in r.get('horasHoje', []):
        print(f"  ⏰ {h['hora']}h: Digital R$ {h['vendaDigital']:10,.2f} | Figital R$ {h['vendaFigital']:10,.2f}")
