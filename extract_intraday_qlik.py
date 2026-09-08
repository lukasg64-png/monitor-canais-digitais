"""
extract_intraday_qlik.py — Extração de Dados Online / Intraday dos Canais Digitais
do Qlik Sense Enterprise (sense.farmaciassaojoao.com.br).

App: E-Commerce x Rede (671fa4f4-eb7d-418f-b4c9-936e87d8011d)
Extrai com precisão minuto a minuto:
1. Timestamp mais recente do dia atual (maxHora, maxDataHora)
2. Vendas Canal x Hora de Hoje, Ontem (D-1) e D-7 (mesmo dia da semana passada)
3. Histórico dos canais para cálculo da Curva Científica e Média 7D
4. Detratores e Propulsores por Grupo, Subgrupo, Laboratório, Linha e Top SKUs
Totalmente dinâmico para qualquer dia do mês e do ano sem dados hardcoded.
"""
import os, sys, time, json, asyncio
from datetime import datetime, timedelta

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

                // 1. Timestamp mais recente do dia atual
                const eMaxHora = await send("Evaluate", docHandle, ["MaxString({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}>} Hora)"]);
                const eMaxDataHora = await send("Evaluate", docHandle, ["MaxString({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}>} [Data e Hora])"]);
                const eMaxData = await send("Evaluate", docHandle, ["MaxString({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}>} Data)"]);
                
                resData.maxHora = (eMaxHora.result?.qReturn && eMaxHora.result.qReturn !== '-') ? eMaxHora.result.qReturn : "%%DEFAULT_HORA%%";
                resData.maxDataHora = (eMaxDataHora.result?.qReturn && eMaxDataHora.result.qReturn !== '-') ? eMaxDataHora.result.qReturn : "%%DEFAULT_DATA_HORA%%";
                resData.dataHoje = (eMaxData.result?.qReturn && eMaxData.result.qReturn !== '-') ? eMaxData.result.qReturn : "%%DEFAULT_DATA%%";
                resData.diaHoje = "%%DIA_HOJE%%";
                resData.diaOntem = "%%DIA_ONTEM%%";
                resData.diaD7 = "%%DIA_D7%%";
                resData.anoMesHoje = "%%ANO_MES_HOJE%%";
                resData.anoMesOntem = "%%ANO_MES_ONTEM%%";
                resData.anoMesD7 = "%%ANO_MES_D7%%";

                // 2. Vendas Hoje - Canal x Hora
                const cH = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_hoje_hora" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Canal"] } },
                            { "qDef": { "qFieldDefs": ["Hora"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Quantidade Produto])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 2500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hH = cH.result.qReturn.qHandle;
                const lH = await send("GetLayout", hH, []);
                const totH = lH.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsHoje = await fetchAllHyperCubeRows(hH, totH, 4, 2500);

                // 3. Vendas Ontem (D-1) - Canal x Hora
                const cO = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_ontem_hora" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Canal"] } },
                            { "qDef": { "qFieldDefs": ["Hora"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Quantidade Produto])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 2500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hO = cO.result.qReturn.qHandle;
                const lO = await send("GetLayout", hO, []);
                const totO = lO.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsOntem = await fetchAllHyperCubeRows(hO, totO, 4, 2500);

                // 4. Vendas D-7 - Canal x Hora
                const c7 = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_d7_hora" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Canal"] } },
                            { "qDef": { "qFieldDefs": ["Hora"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Quantidade Produto])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 2500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const h7 = c7.result.qReturn.qHandle;
                const l7 = await send("GetLayout", h7, []);
                const tot7 = l7.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsD7 = await fetchAllHyperCubeRows(h7, tot7, 4, 2500);

                // 5. Histórico por Dia e Canal (Mês Atual e Mês Anterior para Janela Móvel 7D)
                const cHist = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_hist_canais_dia" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Canal"] } },
                            { "qDef": { "qFieldDefs": ["Dia"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ANTERIOR%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
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
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
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
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
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
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
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
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hLin = cLin.result.qReturn.qHandle;
                const lLin = await send("GetLayout", hLin, []);
                const totLin = lLin.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsLinhas = await fetchAllHyperCubeRows(hLin, totLin, 4, 1500);

                // 10. Top SKUs / Itens (Hoje vs Ontem vs D-7 + Saldo de Estoque)
                const cSKU = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_top_skus" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { 
                                "qDef": { 
                                    "qFieldDefs": ["Produto_ID"],
                                    "qSortCriterias": [{
                                        "qSortByExpression": -1,
                                        "qExpression": { "qv": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida]) + Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` }
                                    }]
                                } 
                            },
                            { "qDef": { "qFieldDefs": ["Desc_Produto"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": "Sum({1} [Quantidade Saldo])" } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 6 }],
                        "qSuppressZero": true
                    }
                }]);
                const hSKU = cSKU.result.qReturn.qHandle;
                const lSKU = await send("GetLayout", hSKU, []);
                const totSKU = lSKU.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsSKUs = await fetchAllHyperCubeRows(hSKU, Math.min(5000, totSKU), 6, 1500);

                ws.close();

                // 11. Consulta Oficial de Estoque da Rede no Relatório Estoque Final (936a28fb-245f-4f19-b285-420535685c43)
                try {
                    const appIdEstoque = "936a28fb-245f-4f19-b285-420535685c43";
                    const wsEstoqueUrl = `wss://${window.location.host}/app/${encodeURIComponent(appIdEstoque)}?reloadUri=https://${window.location.host}/`;
                    const stockMap = await new Promise((resStock) => {
                        const wsEst = new WebSocket(wsEstoqueUrl);
                        let idEst = 1;
                        const pendingEst = {};
                        wsEst.onmessage = (e) => {
                            const m = JSON.parse(e.data);
                            if (m.id && pendingEst[m.id]) {
                                const { res, rej } = pendingEst[m.id];
                                delete pendingEst[m.id];
                                if (m.error) rej(m.error);
                                else res(m);
                            }
                        };
                        function sendEst(method, handle, params) {
                            return new Promise((res, rej) => {
                                const mid = idEst++;
                                pendingEst[mid] = { res, rej };
                                wsEst.send(JSON.stringify({ jsonrpc: "2.0", id: mid, method, handle, params }));
                            });
                        }
                        wsEst.onopen = async () => {
                            try {
                                const oEst = await sendEst("OpenDoc", -1, [appIdEstoque]);
                                const docEstHandle = oEst.result.qReturn.qHandle;
                                const cObjEst = await sendEst("CreateSessionObject", docEstHandle, [{
                                    "qInfo": { "qType": "q_estoque_rede" },
                                    "qHyperCubeDef": {
                                        "qDimensions": [{ "qDef": { "qFieldDefs": ["Produto_ID"] } }],
                                        "qMeasures": [
                                            { "qDef": { "qDef": "Sum({1<AnoMes={'%%ANO_MES_HOJE%%'}>} Qt_Estoque)" } },
                                            { "qDef": { "qDef": "Sum({1<AnoMes={'%%ANO_MES_HOJE%%'}>} Qt_Transito_CDLJ)" } }
                                        ],
                                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 2000, "qWidth": 3 }],
                                        "qSuppressZero": true
                                    }
                                }]);
                                const hEst = cObjEst.result.qReturn.qHandle;
                                const lEst = await sendEst("GetLayout", hEst, []);
                                const totEst = lEst.result.qLayout.qHyperCube.qSize.qcy;
                                const pagesEst = lEst.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
                                let allEstRows = [...pagesEst];
                                let curTopEst = 2000;
                                while (curTopEst < totEst) {
                                    const pRes = await sendEst("GetHyperCubeData", hEst, ["/qHyperCubeDef", [{ "qTop": curTopEst, "qLeft": 0, "qHeight": 2000, "qWidth": 3 }]]);
                                    const newP = pRes.result.qDataPages[0]?.qMatrix || [];
                                    allEstRows.push(...newP);
                                    curTopEst += 2000;
                                }
                                wsEst.close();
                                const map = {};
                                for (const row of allEstRows) {
                                    const pId = row[0]?.qText;
                                    if (pId) {
                                        map[pId] = {
                                            estoqueLoja: row[1]?.qNum || 0,
                                            transito: row[2]?.qNum || 0
                                        };
                                    }
                                }
                                resStock(map);
                            } catch(errEst) {
                                try { wsEst.close(); } catch(e) {}
                                resStock({});
                            }
                        };
                        setTimeout(() => { try { wsEst.close(); } catch(e) {}; resStock({}); }, 40000);
                    });
                    resData.stockMap = stockMap;
                } catch(eStock) {
                    resData.stockMap = {};
                }

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
        }, 90000);
    });
};"""

def compute_date_replacements(target_dt=None):
    """Calcula dinamicamente as datas do dia atual, ontem (D-1) e D-7."""
    if target_dt is None:
        target_dt = datetime.now()

    dt_ontem = target_dt - timedelta(days=1)
    dt_d7 = target_dt - timedelta(days=7)
    dt_mes_ant = target_dt.replace(day=1) - timedelta(days=1)

    return {
        "%%DIGITAL_CHANNELS%%": DIGITAL_CHANNELS,
        "%%DIA_HOJE%%": f"{target_dt.day:02d}",
        "%%ANO_MES_HOJE%%": f"{target_dt.year}-{target_dt.month:02d}",
        "%%DEFAULT_DATA%%": target_dt.strftime("%d/%m/%Y"),
        "%%DEFAULT_HORA%%": target_dt.strftime("%H:%M"),
        "%%DEFAULT_DATA_HORA%%": target_dt.strftime("%d/%m/%Y %H:%M:00"),

        "%%DIA_ONTEM%%": f"{dt_ontem.day:02d}",
        "%%ANO_MES_ONTEM%%": f"{dt_ontem.year}-{dt_ontem.month:02d}",

        "%%DIA_D7%%": f"{dt_d7.day:02d}",
        "%%ANO_MES_D7%%": f"{dt_d7.year}-{dt_d7.month:02d}",

        "%%ANO_MES_ANTERIOR%%": f"{dt_mes_ant.year}-{dt_mes_ant.month:02d}"
    }

async def fetch_intraday_data(target_dt=None):
    t0 = time.time()
    if target_dt is None:
        target_dt = datetime.now()

    replacements = compute_date_replacements(target_dt)
    dia_str = replacements["%%DIA_HOJE%%"]
    mes_str = replacements["%%ANO_MES_HOJE%%"]

    print("=" * 75)
    print(f"  EXTRAÇÃO INTRADAY ONLINE — CANAIS DIGITAIS (QLIK SENSE)")
    print(f"  Data Alvo: {dia_str}/{mes_str} | Ontem: {replacements['%%DIA_ONTEM%%']} | D-7: {replacements['%%DIA_D7%%']}")
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
        js_script = JS_TEMPLATE
        for k, v in replacements.items():
            js_script = js_script.replace(k, v)

        raw_data = await page.evaluate(js_script)
        await browser.close()

    if not raw_data:
        raise RuntimeError("Falha ao extrair dados do Qlik Sense (Timeout ou Erro WebSocket)")

    # Salva arquivo bruto
    with open(RAW_FILE, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print("\n" + "=" * 75)
    print(f"EXTRAÇÃO CONCLUÍDA COM SUCESSO EM {elapsed:.1f}s!")
    print(f"   Arquivo gerado: {RAW_FILE}")
    print(f"   Corte Atual: {raw_data.get('maxDataHora')} (Minuto: {raw_data.get('maxHora')})")
    print(f"   Linhas Hoje: {len(raw_data.get('rowsHoje', []))} | Ontem: {len(raw_data.get('rowsOntem', []))} | D-7: {len(raw_data.get('rowsD7', []))}")
    print(f"   Grupos: {len(raw_data.get('rowsGrupos', []))} | Subgrupos: {len(raw_data.get('rowsSubgrupos', []))}")
    print(f"   Laboratórios: {len(raw_data.get('rowsLabs', []))} | Linhas: {len(raw_data.get('rowsLinhas', []))} | SKUs: {len(raw_data.get('rowsSKUs', []))}")
    print("=" * 75)
    return raw_data

if __name__ == '__main__':
    asyncio.run(fetch_intraday_data())
