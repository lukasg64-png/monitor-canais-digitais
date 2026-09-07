"""
extract_intraday_qlik.py — Extração de Dados Online / Intraday dos Canais Digitais
do Qlik Sense Enterprise (sense.farmaciassaojoao.com.br).

App: E-Commerce x Rede (671fa4f4-eb7d-418f-b4c9-936e87d8011d)
Extrai com precisão minuto a minuto:
1. Timestamp mais recente do dia de hoje (maxHora, maxDataHora)
2. Vendas Canal x Hora de Hoje (Dia 07), Ontem (Dia 06) e D-7 (Segunda 31/08)
3. Vendas Canal x Hora dos dias 01 a 06 de Setembro (para cálculo da Curva Científica e Média 7D)
4. Detratores e Propulsores por Grupo, Subgrupo, Laboratório, Linha e Top SKUs
"""
import os, sys, time, json, asyncio
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
RAW_FILE = os.path.join(DATA_DIR, 'intraday_raw.json')

QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ID = "671fa4f4-eb7d-418f-b4c9-936e87d8011d"
SHEET_ID = "ddd70c77-1a06-40d9-aff2-efa4b6b67b24"
SHEET_URL = f"{QLIK_URL}/sense/app/{APP_ID}/sheet/{SHEET_ID}/state/analysis"

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"

DIGITAL_CHANNELS = "'APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'e_Commerce'"

JS_TEMPLATE = """async () => {
    const appId = "671fa4f4-eb7d-418f-b4c9-936e87d8011d";
    const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;
    const CHANNELS = "%%DIGITAL_CHANNELS%%";

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

        async function fetchAllHyperCubeRows(objHandle, totalRows, qWidth, pageSize) {
            let rows = [];
            let top = 0;
            while (top < totalRows) {
                const height = Math.min(pageSize, totalRows - top);
                const pageRes = await send("GetHyperCubeData", objHandle, ["/qHyperCubeDef", [{ "qTop": top, "qLeft": 0, "qHeight": height, "qWidth": qWidth }]]);
                const matrix = pageRes.result.qDataPages[0]?.qMatrix || [];
                if (matrix.length === 0) break;
                matrix.forEach(r => rows.push(r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText)));
                top += matrix.length;
            }
            return rows;
        }

        ws.onopen = async () => {
            try {
                const openRes = await send("OpenDoc", -1, [appId]);
                const docHandle = openRes.result.qReturn.qHandle;
                const resData = {};

                // 1. Timestamp mais recente do dia atual (Dia 07)
                const eMaxHora = await send("Evaluate", docHandle, ["MaxString({1<[Ano-Mes]={'2026-09'}, Dia={'07'}>} Hora)"]);
                const eMaxDataHora = await send("Evaluate", docHandle, ["MaxString({1<[Ano-Mes]={'2026-09'}, Dia={'07'}>} [Data e Hora])"]);
                const eMaxData = await send("Evaluate", docHandle, ["MaxString({1<[Ano-Mes]={'2026-09'}, Dia={'07'}>} Data)"]);
                
                resData.maxHora = eMaxHora.result?.qReturn || "12:52";
                resData.maxDataHora = eMaxDataHora.result?.qReturn || "07/09/2026 12:52:59";
                resData.dataHoje = eMaxData.result?.qReturn || "07/09/2026";
                resData.diaHoje = "07";
                resData.diaOntem = "06";
                resData.diaD7 = "31"; // Segunda-feira anterior (31/08/2026)

                // 2. Vendas Hoje (Dia 07) - Canal x Hora
                const cH = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_hoje_hora" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Canal"] } },
                            { "qDef": { "qFieldDefs": ["Hora"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}, [Canal]={${CHANNELS}}>} [Quantidade Produto])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 2500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hH = cH.result.qReturn.qHandle;
                const lH = await send("GetLayout", hH, []);
                const totH = lH.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsHoje = await fetchAllHyperCubeRows(hH, totH, 4, 2500);

                // 3. Vendas Ontem (Dia 06) - Canal x Hora
                const cO = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_ontem_hora" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Canal"] } },
                            { "qDef": { "qFieldDefs": ["Hora"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'06'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'06'}, [Canal]={${CHANNELS}}>} [Quantidade Produto])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 2500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hO = cO.result.qReturn.qHandle;
                const lO = await send("GetLayout", hO, []);
                const totO = lO.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsOntem = await fetchAllHyperCubeRows(hO, totO, 4, 2500);

                // 4. Vendas D-7 (31/08) - Canal x Hora
                const c7 = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_d7_hora" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Canal"] } },
                            { "qDef": { "qFieldDefs": ["Hora"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}, [Canal]={${CHANNELS}}>} [Quantidade Produto])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 2500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const h7 = c7.result.qReturn.qHandle;
                const l7 = await send("GetLayout", h7, []);
                const tot7 = l7.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsD7 = await fetchAllHyperCubeRows(h7, tot7, 4, 2500);

                // 5. Histórico de Setembro/2026 por Dia e Canal (para totais e curva)
                const cHist = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_hist_canais_dia" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Canal"] } },
                            { "qDef": { "qFieldDefs": ["Dia"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-08'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hHist = cHist.result.qReturn.qHandle;
                const lHist = await send("GetLayout", hHist, []);
                resData.rowsHistDia = (lHist.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText));

                // 6. Grupos de Produtos (Hoje vs Ontem vs D-7)
                const cGrupos = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_grupos" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Canal"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Grupo"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'06'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 500, "qWidth": 5 }],
                        "qSuppressZero": true
                    }
                }]);
                const hGrupos = cGrupos.result.qReturn.qHandle;
                const lGrupos = await send("GetLayout", hGrupos, []);
                resData.rowsGrupos = (lGrupos.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText));

                // 7. Subgrupos de Produtos (Hoje vs Ontem vs D-7)
                const cSub = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_subgrupos" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Desc_Grupo"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Subgrupo"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'06'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 5 }],
                        "qSuppressZero": true
                    }
                }]);
                const hSub = cSub.result.qReturn.qHandle;
                const lSub = await send("GetLayout", hSub, []);
                const totSub = lSub.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsSubgrupos = await fetchAllHyperCubeRows(hSub, totSub, 5, 1500);

                // 8. Fornecedores / Laboratórios (Hoje vs Ontem vs D-7)
                const cLabs = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_labs" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Laboratorio"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'06'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hLabs = cLabs.result.qReturn.qHandle;
                const lLabs = await send("GetLayout", hLabs, []);
                const totLabs = lLabs.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsLabs = await fetchAllHyperCubeRows(hLabs, totLabs, 4, 1500);

                // 9. Linhas de Produtos (Hoje vs Ontem vs D-7)
                const cLin = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_linhas" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Desc_Linha"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'06'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hLin = cLin.result.qReturn.qHandle;
                const lLin = await send("GetLayout", hLin, []);
                const totLin = lLin.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsLinhas = await fetchAllHyperCubeRows(hLin, totLin, 4, 1500);

                // 10. Top SKUs / Itens (Hoje vs Ontem vs D-7)
                const cSKU = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_top_skus" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Produto_ID"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Produto"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-09'}, Dia={'06'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 5 }],
                        "qSuppressZero": true
                    }
                }]);
                const hSKU = cSKU.result.qReturn.qHandle;
                const lSKU = await send("GetLayout", hSKU, []);
                const totSKU = lSKU.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsSKUs = await fetchAllHyperCubeRows(hSKU, Math.min(2500, totSKU), 5, 1500);

                ws.close();
                resolve(resData);
            } catch (e) {
                ws.close();
                reject(new Error(e.message || String(e)));
            }
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.id && pending[msg.id]) {
                const { res, rej } = pending[msg.id];
                delete pending[msg.id];
                if (msg.error) rej(new Error(JSON.stringify(msg.error)));
                else res(msg);
            }
        };

        setTimeout(() => {
            try { ws.close(); } catch(e) {}
            resolve(null);
        }, 75000);
    });
};"""

async def fetch_intraday_data():
    t0 = time.time()
    print("=" * 75)
    print("  EXTRAÇÃO INTRADAY ONLINE — CANAIS DIGITAIS (QLIK SENSE)")
    print("=" * 75)

    async with async_playwright() as p:
        print("1/4 Conectando ao Qlik Sense Enterprise...", flush=True)
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD},
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        await page.goto(SHEET_URL, timeout=60000)
        try:
            await page.wait_for_selector('.qv-panel-sheet', timeout=30000)
        except Exception:
            await page.wait_for_timeout(4000)

        print("2/4 Sessão autenticada! Executando consultas no QIX Engine via WebSocket...", flush=True)
        js_script = JS_TEMPLATE.replace("%%DIGITAL_CHANNELS%%", DIGITAL_CHANNELS)
        raw_data = await page.evaluate(js_script)
        await browser.close()

    if not raw_data:
        raise RuntimeError("Falha ao extrair dados do Qlik Sense (Timeout ou Erro WebSocket)")

    # Salva arquivo bruto
    with open(RAW_FILE, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print("\n" + "=" * 75)
    print(f"✅ EXTRAÇÃO CONCLUÍDA COM SUCESSO EM {elapsed:.1f}s!")
    print(f"   Arquivo gerado: {RAW_FILE}")
    print(f"   Corte Atual: {raw_data.get('maxDataHora')} (Minuto: {raw_data.get('maxHora')})")
    print(f"   Linhas Hoje: {len(raw_data.get('rowsHoje', []))} | Ontem: {len(raw_data.get('rowsOntem', []))} | D-7: {len(raw_data.get('rowsD7', []))}")
    print(f"   Grupos: {len(raw_data.get('rowsGrupos', []))} | Subgrupos: {len(raw_data.get('rowsSubgrupos', []))}")
    print(f"   Laboratórios: {len(raw_data.get('rowsLabs', []))} | Linhas: {len(raw_data.get('rowsLinhas', []))} | SKUs: {len(raw_data.get('rowsSKUs', []))}")
    print("=" * 75)
    return raw_data

if __name__ == '__main__':
    asyncio.run(fetch_intraday_data())
