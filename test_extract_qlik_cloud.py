import asyncio, sys, json, time
from datetime import datetime, timedelta
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

QLIK_CLOUD_HOST = "fsj.us.qlikcloud.com"
STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"
APP_ID = "dc8160b3-bafe-4040-a42e-4916ee9c463c"  # Indicadores de Vendas

JS_TEMPLATE = """async () => {
    const appId = "%%APP_ID%%";
    const CHANNELS = "%%CHANNELS%%";
    const D_HOJE = "%%D_HOJE%%";
    const D_ONTEM = "%%D_ONTEM%%";
    const D_D7 = "%%D_D7%%";

    const csrfRes = await fetch('/api/v1/csrf-token');
    const csrfToken = csrfRes.headers.get('qlik-csrf-token');
    const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?qlik-csrf-token=${csrfToken}`;

    return new Promise((resolve) => {
        const ws = new WebSocket(wsUrl);
        let id = 1;
        const pend = {};
        const send = (m, h, p) => new Promise((r, j) => { pend[id] = {r, j}; ws.send(JSON.stringify({jsonrpc:'2.0', id: id++, method: m, handle: h, params: p})); });
        ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.id && pend[d.id]) { pend[d.id].r(d); delete pend[d.id]; } };

        async function fetchAllRows(handle, totalRows, width, pageSize = 1500) {
            let rows = [];
            let top = 0;
            while (top < totalRows) {
                const h = Math.min(pageSize, totalRows - top);
                const res = await send("GetHyperCubeData", handle, ["/qHyperCubeDef", [{ "qTop": top, "qLeft": 0, "qHeight": h, "qWidth": width }]]);
                const matrix = res.result.qDataPages[0]?.qMatrix || [];
                if (matrix.length === 0) break;
                matrix.forEach(r => rows.push(r.map(col => col.qNum !== 'NaN' && typeof col.qNum === 'number' ? col.qNum : col.qText)));
                top += matrix.length;
            }
            return rows;
        }

        ws.onopen = async () => {
            try {
                const doc = (await send('OpenDoc', -1, [appId])).result.qReturn.qHandle;
                const resData = {};

                // 1. Timestamps
                const evalMaxTime = await send("Evaluate", doc, [`MaxString({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} INCLUSAO_DATA_TIME)`]);
                resData.maxDataHora = evalMaxTime.result.qReturn || `${D_HOJE} 12:00`;
                const parts = (resData.maxDataHora || "").split(' ');
                resData.maxHora = parts.length > 1 ? parts[1].substring(0, 5) : "12:00";
                resData.maxDate = D_HOJE;
                resData.diaHoje = "%%DIA_HOJE%%";
                resData.diaOntem = "%%DIA_ONTEM%%";
                resData.diaD7 = "%%DIA_D7%%";
                resData.anoMesHoje = "%%ANO_MES_HOJE%%";
                resData.anoMesOntem = "%%ANO_MES_ONTEM%%";
                resData.anoMesD7 = "%%ANO_MES_D7%%";

                // 2. Rows Hoje (Canal, Hora, Receita Liquida, Qtd)
                const objH = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_hoje_hora" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["TIPO_VENDA_DESCRICAO"] } },
                            { "qDef": { "qFieldDefs": ["=Hour(INCLUSAO_DATA_TIME)"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [QUANTIDADE_MERCADORIA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hH = objH.result.qReturn.qHandle;
                const layH = await send("GetLayout", hH, []);
                const totH = layH.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsHoje = await fetchAllRows(hH, totH, 4, 1500);

                // 3. Rows Ontem (Canal, Hora, Receita Liquida, Qtd)
                const objO = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_ontem_hora" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["TIPO_VENDA_DESCRICAO"] } },
                            { "qDef": { "qFieldDefs": ["=Hour(INCLUSAO_DATA_TIME)"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [QUANTIDADE_MERCADORIA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hO = objO.result.qReturn.qHandle;
                const layO = await send("GetLayout", hO, []);
                const totO = layO.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsOntem = await fetchAllRows(hO, totO, 4, 1500);

                // 4. Rows D-7 (Canal, Hora, Receita Liquida, Qtd)
                const obj7 = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_d7_hora" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["TIPO_VENDA_DESCRICAO"] } },
                            { "qDef": { "qFieldDefs": ["=Hour(INCLUSAO_DATA_TIME)"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [QUANTIDADE_MERCADORIA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const h7 = obj7.result.qReturn.qHandle;
                const lay7 = await send("GetLayout", h7, []);
                const tot7 = lay7.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsD7 = await fetchAllRows(h7, tot7, 4, 1500);

                // 5. Histórico por Dia e Canal (Mês Atual e Mês Anterior)
                const objHist = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_hist_canais_dia" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["TIPO_VENDA_DESCRICAO"] } },
                            { "qDef": { "qFieldDefs": ["INCLUSAO_DATA"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 500, "qWidth": 3 }],
                        "qSuppressZero": true
                    }
                }]);
                const hHist = objHist.result.qReturn.qHandle;
                const layHist = await send("GetLayout", hHist, []);
                const totHist = layHist.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsHistDia = await fetchAllRows(hHist, totHist, 3, 500);

                // 6. Grupos de Produtos
                const objG = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_grupos" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["TIPO_VENDA_DESCRICAO"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Grupo"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 500, "qWidth": 5 }],
                        "qSuppressZero": true
                    }
                }]);
                const hG = objG.result.qReturn.qHandle;
                const layG = await send("GetLayout", hG, []);
                resData.rowsGrupos = await fetchAllRows(hG, layG.result.qLayout.qHyperCube.qSize.qcy, 5, 500);

                // 7. Subgrupos
                const objSub = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_subgrupos" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Desc_Grupo"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Subgrupo"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 5 }],
                        "qSuppressZero": true
                    }
                }]);
                const hSub = objSub.result.qReturn.qHandle;
                const laySub = await send("GetLayout", hSub, []);
                resData.rowsSubgrupos = await fetchAllRows(hSub, laySub.result.qLayout.qHyperCube.qSize.qcy, 5, 1500);

                // 8. Laboratórios
                const objLab = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_labs" },
                    "qHyperCubeDef": {
                        "qDimensions": [{ "qDef": { "qFieldDefs": ["Laboratorio"] } }],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hLab = objLab.result.qReturn.qHandle;
                const layLab = await send("GetLayout", hLab, []);
                resData.rowsLabs = await fetchAllRows(hLab, layLab.result.qLayout.qHyperCube.qSize.qcy, 4, 1500);

                // 9. Linhas
                const objLin = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_linhas" },
                    "qHyperCubeDef": {
                        "qDimensions": [{ "qDef": { "qFieldDefs": ["Desc_Linha"] } }],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hLin = objLin.result.qReturn.qHandle;
                const layLin = await send("GetLayout", hLin, []);
                resData.rowsLinhas = await fetchAllRows(hLin, layLin.result.qLayout.qHyperCube.qSize.qcy, 4, 1500);

                // 10. Top SKUs
                const objSKU = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_top_skus" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { 
                                "qDef": { 
                                    "qFieldDefs": ["Produto_ID"],
                                    "qSortCriterias": [{
                                        "qSortByExpression": -1,
                                        "qExpression": { "qv": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M]) + Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` }
                                    }]
                                } 
                            },
                            { "qDef": { "qFieldDefs": ["Desc_Produto"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": "Sum({1} [Qt_Estoque])" } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 6 }],
                        "qSuppressZero": true
                    }
                }]);
                const hSKU = objSKU.result.qReturn.qHandle;
                const laySKU = await send("GetLayout", hSKU, []);
                const totSKU = laySKU.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsSKUs = await fetchAllRows(hSKU, Math.min(3000, totSKU), 6, 1500);

                // 11. Regional UFs
                const objUF = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_uf" },
                    "qHyperCubeDef": {
                        "qDimensions": [{ "qDef": { "qFieldDefs": ["UF"] } }],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 10, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hUF = objUF.result.qReturn.qHandle;
                const layUF = await send("GetLayout", hUF, []);
                resData.rowsUF = await fetchAllRows(hUF, layUF.result.qLayout.qHyperCube.qSize.qcy, 4, 10);

                // 12. Regional Filiais
                const objFil = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_filiais" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Filial_ID"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Filial"] } },
                            { "qDef": { "qFieldDefs": ["UF"] } },
                            { "qDef": { "qFieldDefs": ["Coordenador"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": "Sum({1} [Qt_Estoque])" } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 8 }],
                        "qSuppressZero": true
                    }
                }]);
                const hFil = objFil.result.qReturn.qHandle;
                const layFil = await send("GetLayout", hFil, []);
                resData.rowsFiliais = await fetchAllRows(hFil, layFil.result.qLayout.qHyperCube.qSize.qcy, 8, 1500);

                ws.close();
                resolve(resData);
            } catch(e) {
                ws.close();
                resolve({ error: String(e) });
            }
        };
        setTimeout(() => { ws.close(); resolve({ error: 'timeout' }); }, 50000);
    });
};"""

async def test_full_extract():
    t0 = time.time()
    dt_now = datetime.now()
    dt_hoje = dt_now.strftime("%d/%m/%Y")
    dt_ontem = (dt_now - timedelta(days=1)).strftime("%d/%m/%Y")
    dt_d7 = (dt_now - timedelta(days=7)).strftime("%d/%m/%Y")
    CHANNELS = "'APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'E-commerce', 'Figital'"
    
    print(f"Iniciando teste de extração Qlik Cloud para Hoje={dt_hoje}, Ontem={dt_ontem}, D-7={dt_d7}...")

    replacements = {
        "%%APP_ID%%": APP_ID,
        "%%CHANNELS%%": CHANNELS,
        "%%D_HOJE%%": dt_hoje,
        "%%D_ONTEM%%": dt_ontem,
        "%%D_D7%%": dt_d7,
        "%%DIA_HOJE%%": f"{dt_now.day:02d}",
        "%%DIA_ONTEM%%": f"{(dt_now - timedelta(days=1)).day:02d}",
        "%%DIA_D7%%": f"{(dt_now - timedelta(days=7)).day:02d}",
        "%%ANO_MES_HOJE%%": dt_now.strftime('%Y-%m'),
        "%%ANO_MES_ONTEM%%": (dt_now - timedelta(days=1)).strftime('%Y-%m'),
        "%%ANO_MES_D7%%": (dt_now - timedelta(days=7)).strftime('%Y-%m')
    }

    js_code = JS_TEMPLATE
    for k, v in replacements.items():
        js_code = js_code.replace(k, v)

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        c = await b.new_context(storage_state=STORAGE_STATE, ignore_https_errors=True)
        page = await c.new_page()
        await page.goto(f"https://{QLIK_CLOUD_HOST}/analytics/home", timeout=60000)
        await page.wait_for_timeout(3000)
        
        data = await page.evaluate(js_code)
        await b.close()

    elapsed = time.time() - t0
    if 'error' in data:
        print(f"❌ Erro na extração: {data['error']}")
        return None
    
    print(f"\n✅ EXTRAÇÃO QLIK CLOUD FINALIZADA EM {elapsed:.1f}s!")
    print(f"   maxDataHora: {data.get('maxDataHora')} | maxHora: {data.get('maxHora')}")
    print(f"   Linhas Hoje: {len(data.get('rowsHoje', []))} (Sample: {data.get('rowsHoje', [None])[0]})")
    print(f"   Linhas Ontem: {len(data.get('rowsOntem', []))}")
    print(f"   Linhas D-7: {len(data.get('rowsD7', []))}")
    print(f"   Histórico: {len(data.get('rowsHistDia', []))}")
    print(f"   Grupos: {len(data.get('rowsGrupos', []))}")
    print(f"   Subgrupos: {len(data.get('rowsSubgrupos', []))}")
    print(f"   Labs: {len(data.get('rowsLabs', []))}")
    print(f"   Linhas: {len(data.get('rowsLinhas', []))}")
    print(f"   SKUs: {len(data.get('rowsSKUs', []))}")
    print(f"   UFs: {len(data.get('rowsUF', []))} -> {data.get('rowsUF')}")
    print(f"   Filiais: {len(data.get('rowsFiliais', []))}")
    
    return data

if __name__ == '__main__':
    asyncio.run(test_full_extract())
