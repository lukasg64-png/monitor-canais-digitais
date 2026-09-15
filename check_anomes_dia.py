import asyncio, sys, json
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"
APP_ID = "dc8160b3-bafe-4040-a42e-4916ee9c463c"

async def check_fields():
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
                        
                        // Distinct ANOMES
                        const objAM = await send('CreateSessionObject', doc, [{
                            qInfo: { qType: 'am' },
                            qHyperCubeDef: {
                                qDimensions: [{ qDef: { qFieldDefs: ['ANOMES'] } }],
                                qMeasures: [{ qDef: { qDef: 'Count(1)' } }],
                                qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 20, qWidth: 2 }]
                            }
                        }]);
                        const layAM = await send('GetLayout', objAM.result.qReturn.qHandle, []);
                        const anomes = (layAM.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r[0].qText);

                        // Distinct DIA
                        const objDia = await send('CreateSessionObject', doc, [{
                            qInfo: { qType: 'dia' },
                            qHyperCubeDef: {
                                qDimensions: [{ qDef: { qFieldDefs: ['DIA'] } }],
                                qMeasures: [{ qDef: { qDef: 'Count(1)' } }],
                                qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 35, qWidth: 2 }]
                            }
                        }]);
                        const layDia = await send('GetLayout', objDia.result.qReturn.qHandle, []);
                        const dias = (layDia.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r[0].qText);

                        // Distinct Distrital / Diretor
                        const objDist = await send('CreateSessionObject', doc, [{
                            qInfo: { qType: 'dist' },
                            qHyperCubeDef: {
                                qDimensions: [{ qDef: { qFieldDefs: ['Distrital'] } }],
                                qMeasures: [{ qDef: { qDef: 'Count(1)' } }],
                                qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 20, qWidth: 2 }]
                            }
                        }]);
                        const layDist = await send('GetLayout', objDist.result.qReturn.qHandle, []);
                        const distritais = (layDist.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r[0].qText);

                        // Distinct Coordenador
                        const objCoord = await send('CreateSessionObject', doc, [{
                            qInfo: { qType: 'coord' },
                            qHyperCubeDef: {
                                qDimensions: [{ qDef: { qFieldDefs: ['Coordenador'] } }],
                                qMeasures: [{ qDef: { qDef: 'Count(1)' } }],
                                qInitialDataFetch: [{ qTop: 0, qLeft: 0, qHeight: 20, qWidth: 2 }]
                            }
                        }]);
                        const layCoord = await send('GetLayout', objCoord.result.qReturn.qHandle, []);
                        const coordenadores = (layCoord.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r[0].qText);

                        ws.close();
                        resolve({ anomes, dias, distritais, coordenadores });
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
    res = asyncio.run(check_fields())
    print("ANOMES:", res.get('anomes'))
    print("DIAS:", sorted(res.get('dias', []), key=lambda x: int(x) if x.isdigit() else 0))
    print(f"Distritais ({len(res.get('distritais', []))}):", res.get('distritais'))
    print(f"Coordenadores (amostra):", res.get('coordenadores', [])[:5])
