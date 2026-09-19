"""
extract_intraday_qlik.py — Extração de Dados Online / Intraday dos Canais Digitais
via Qlik Cloud SaaS (fsj.us.qlikcloud.com) com alta performance (<20s) e
atualização a cada 30 minutos.

App: Indicadores de Vendas (dc8160b3-bafe-4040-a42e-4916ee9c463c)
Canais: APP, APP Tele Entrega, SITE, SITE Tele Entrega, iFood, E-commerce e Figital
Extrai com precisão:
1. Timestamp mais recente do dia atual (maxHora, maxDataHora)
2. Vendas Canal x Hora de Hoje, Ontem (D-1) e D-7 (mesmo dia da semana passada)
3. Histórico dos canais para cálculo da Curva Científica e Média 7D
4. Detratores e Propulsores por Grupo, Subgrupo, Laboratório, Linha e Top SKUs
5. Dados Territoriais e Organizacionais: UFs, Distritais, Coordenações e Filiais
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
LOCK_FILE = os.path.join(DATA_DIR, 'sync.lock')

QLIK_CLOUD_HOST = "fsj.us.qlikcloud.com"
STORAGE_STATE = r"c:\Users\lucas.alves6\OneDrive - Farmácias São João\Documentos\ANTIGRAVITI\Acompanhamento Categorias Digital\data\qlik_cloud_storage_state.json"
APP_ID = "dc8160b3-bafe-4040-a42e-4916ee9c463c"  # Indicadores de Vendas (Qlik Cloud)

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"

CHANNELS = "'APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'E-commerce', 'Figital'"

def is_pid_running(pid):
    try:
        import subprocess
        res = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True)
        return str(pid) in res.stdout
    except Exception:
        return False

def acquire_lock(timeout_sec=300):
    for attempt in range(35):
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                lock_pid = data.get('pid')
                lock_time = data.get('time', 0)
                if time.time() - lock_time < timeout_sec and lock_pid and is_pid_running(lock_pid):
                    time.sleep(2.0)
                    continue
            except Exception:
                pass
        break
    else:
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                lock_pid = data.get('pid')
                print(f"⚠️ Sincronização em execução no processo PID {lock_pid}. Aguardou 70s.")
                return False
            except Exception:
                pass
    try:
        with open(LOCK_FILE, 'w', encoding='utf-8') as f:
            json.dump({'pid': os.getpid(), 'time': time.time()}, f)
    except Exception:
        pass
    return True

def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass

JS_TEMPLATE = """async () => {
    const appId = "%%APP_ID%%";
    const CHANNELS = "%%CHANNELS%%";
    const D_HOJE = "%%D_HOJE%%";
    const D_ONTEM = "%%D_ONTEM%%";
    const D_D7 = "%%D_D7%%";
    const AM_HOJE = "%%AM_HOJE%%";
    const AM_ANT = "%%AM_ANT%%";

    const csrfRes = await fetch('/api/v1/csrf-token');
    const csrfToken = csrfRes.headers.get('qlik-csrf-token');
    const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?qlik-csrf-token=${csrfToken}`;

    return new Promise((resolve) => {
        const ws = new WebSocket(wsUrl);
        let id = 1;
        const pend = {};
        const send = (m, h, p) => new Promise((r, j) => { pend[id] = {r, j}; ws.send(JSON.stringify({jsonrpc:'2.0', id: id++, method: m, handle: h, params: p})); });
        ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.id && pend[d.id]) { pend[d.id].r(d); delete pend[d.id]; } };

        async function fetchAllRows(handle, totalRows, width, pageSize = 1500, name = "Cube") {
            let rows = [];
            let top = 0;
            const t0 = performance.now();
            const effPageSize = Math.min(pageSize, Math.floor(10000 / width));
            while (top < totalRows) {
                const h = Math.min(effPageSize, totalRows - top);
                const res = await send("GetHyperCubeData", handle, ["/qHyperCubeDef", [{ "qTop": top, "qLeft": 0, "qHeight": h, "qWidth": width }]]);
                const matrix = res.result.qDataPages[0]?.qMatrix || [];
                if (matrix.length === 0) break;
                matrix.forEach(r => rows.push(r.map(col => col.qNum !== 'NaN' && typeof col.qNum === 'number' ? col.qNum : col.qText)));
                top += matrix.length;
            }
            console.log(`[Qlik Cloud] ${name}: ${rows.length}/${totalRows} em ${(performance.now() - t0).toFixed(0)}ms`);
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
                resData.rowsHoje = await fetchAllRows(hH, layH.result.qLayout.qHyperCube.qSize.qcy, 4, 1500, "Hoje");

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
                resData.rowsOntem = await fetchAllRows(hO, layO.result.qLayout.qHyperCube.qSize.qcy, 4, 1500, "Ontem");

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
                resData.rowsD7 = await fetchAllRows(h7, lay7.result.qLayout.qHyperCube.qSize.qcy, 4, 1500, "D7");

                // 5. Histórico por Dia e Canal (Mês Atual e Mês Anterior)
                const objHist = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_hist_canais_dia" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["TIPO_VENDA_DESCRICAO"] } },
                            { "qDef": { "qFieldDefs": ["DIA"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<ANOMES={'${AM_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<ANOMES={'${AM_ANT}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hHist = objHist.result.qReturn.qHandle;
                const layHist = await send("GetLayout", hHist, []);
                resData.rowsHistDia = await fetchAllRows(hHist, layHist.result.qLayout.qHyperCube.qSize.qcy, 4, 500, "HistDia");

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
                resData.rowsGrupos = await fetchAllRows(hG, layG.result.qLayout.qHyperCube.qSize.qcy, 5, 500, "Grupos");

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
                resData.rowsSubgrupos = await fetchAllRows(hSub, laySub.result.qLayout.qHyperCube.qSize.qcy, 5, 1500, "Subgrupos");

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
                resData.rowsLabs = await fetchAllRows(hLab, layLab.result.qLayout.qHyperCube.qSize.qcy, 4, 1500, "Labs");

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
                resData.rowsLinhas = await fetchAllRows(hLin, layLin.result.qLayout.qHyperCube.qSize.qcy, 4, 1500, "Linhas");

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
                resData.rowsSKUs = await fetchAllRows(hSKU, Math.min(3500, totSKU), 6, 1500, "SKUs");

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
                resData.rowsUF = await fetchAllRows(hUF, layUF.result.qLayout.qHyperCube.qSize.qcy, 4, 10, "UFs");

                // 12. Diretorias / Distritais
                const objDir = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_dir" },
                    "qHyperCubeDef": {
                        "qDimensions": [{ "qDef": { "qFieldDefs": ["Distrital"] } }],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 20, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hDir = objDir.result.qReturn.qHandle;
                const layDir = await send("GetLayout", hDir, []);
                resData.rowsDir = await fetchAllRows(hDir, layDir.result.qLayout.qHyperCube.qSize.qcy, 4, 20, "Diretorias");

                // 13. Coordenações
                const objCoord = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_coord" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Coordenador"] } },
                            { "qDef": { "qFieldDefs": ["UF"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 60, "qWidth": 5 }],
                        "qSuppressZero": true
                    }
                }]);
                const hCoord = objCoord.result.qReturn.qHandle;
                const layCoord = await send("GetLayout", hCoord, []);
                resData.rowsCoord = await fetchAllRows(hCoord, layCoord.result.qLayout.qHyperCube.qSize.qcy, 5, 60, "Coordenações");

                // 14. Regional Filiais (Top Lojas Faturamento Digital)
                const objFil = await send("CreateSessionObject", doc, [{
                    "qInfo": { "qType": "q_filiais" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { 
                                "qDef": { 
                                    "qFieldDefs": ["Filial_ID"],
                                    "qSortCriterias": [{
                                        "qSortByExpression": -1,
                                        "qExpression": { "qv": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M]) + Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` }
                                    }]
                                } 
                            },
                            { "qDef": { "qFieldDefs": ["Desc_Filial"] } },
                            { "qDef": { "qFieldDefs": ["UF"] } },
                            { "qDef": { "qFieldDefs": ["Coordenador"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_ONTEM}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_D7}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [VALOR_VENDA_LIQUIDA_M])` } },
                            { "qDef": { "qDef": "Sum({1} [Qt_Estoque])" } },
                            { "qDef": { "qDef": "Sum({1} [Qt_Estoque]) / 31" } },
                            { "qDef": { "qDef": `Sum({1<INCLUSAO_DATA={'${D_HOJE}'}, TIPO_VENDA_DESCRICAO={${CHANNELS}}>} [QUANTIDADE_MERCADORIA_M])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 800, "qWidth": 10 }],
                        "qSuppressZero": true
                    }
                }]);
                const hFil = objFil.result.qReturn.qHandle;
                const layFil = await send("GetLayout", hFil, []);
                resData.rowsFiliais = await fetchAllRows(hFil, layFil.result.qLayout.qHyperCube.qSize.qcy, 10, 800, "Filiais");

                // Stock map construído diretamente dos SKUs extraídos
                const stockMap = {};
                for (const skuRow of resData.rowsSKUs) {
                    const skuId = String(skuRow[0]);
                    const saldo = Number(skuRow[5]) || 0;
                    stockMap[skuId] = { estoqueLoja: saldo, transito: 0 };
                }
                resData.stockMap = stockMap;

                ws.close();
                resolve(resData);
            } catch(e) {
                ws.close();
                resolve({ error: String(e) });
            }
        };
        setTimeout(() => { ws.close(); resolve({ error: 'timeout (limite de 360s excedido)' }); }, 360000);
    });
};"""

async def fetch_intraday_data():
    t0 = time.time()
    if not acquire_lock():
        return None

    try:
        dt_now = datetime.now()
        dt_hoje = dt_now.strftime("%d/%m/%Y")
        dt_ontem = (dt_now - timedelta(days=1)).strftime("%d/%m/%Y")
        dt_d7 = (dt_now - timedelta(days=7)).strftime("%d/%m/%Y")
        
        am_hoje = f"{dt_now.year}-{dt_now.month}"
        dt_ant = dt_now.replace(day=1) - timedelta(days=1)
        am_ant = f"{dt_ant.year}-{dt_ant.month}"

        print("=" * 75)
        print("  EXTRAÇÃO INTRADAY ONLINE — QLIK CLOUD (FSJ.US.QLIKCLOUD.COM)")
        print(f"  App: Indicadores de Vendas ({APP_ID})")
        print(f"  Data Alvo: {dt_hoje} | Ontem: {dt_ontem} | D-7: {dt_d7}")
        print(f"  Canais Monitorados: {CHANNELS}")
        print("=" * 75)

        replacements = {
            "%%APP_ID%%": APP_ID,
            "%%CHANNELS%%": CHANNELS,
            "%%D_HOJE%%": dt_hoje,
            "%%D_ONTEM%%": dt_ontem,
            "%%D_D7%%": dt_d7,
            "%%AM_HOJE%%": am_hoje,
            "%%AM_ANT%%": am_ant,
            "%%DIA_HOJE%%": f"{dt_now.day}",
            "%%DIA_ONTEM%%": f"{(dt_now - timedelta(days=1)).day}",
            "%%DIA_D7%%": f"{(dt_now - timedelta(days=7)).day}",
            "%%ANO_MES_HOJE%%": dt_now.strftime('%Y-%m'),
            "%%ANO_MES_ONTEM%%": (dt_now - timedelta(days=1)).strftime('%Y-%m'),
            "%%ANO_MES_D7%%": (dt_now - timedelta(days=7)).strftime('%Y-%m')
        }

        js_code = JS_TEMPLATE
        for k, v in replacements.items():
            js_code = js_code.replace(k, v)

        async with async_playwright() as p:
            print("1/4 Conectando ao Qlik Cloud SaaS...", flush=True)
            browser = await p.chromium.launch(
                headless=True,
                args=['--ignore-certificate-errors', '--disable-dev-shm-usage', '--no-sandbox']
            )
            try:
                context = await browser.new_context(
                    storage_state=STORAGE_STATE,
                    ignore_https_errors=True,
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                page.on("console", lambda msg: print(f"   [Qlik Cloud] {msg.text}", flush=True))

                await page.goto(f"https://{QLIK_CLOUD_HOST}/analytics/home", timeout=60000)
                
                # Check SSO login if needed
                try:
                    user_input = await page.wait_for_selector('#username', timeout=5000)
                    if user_input:
                        print("   Efetuando login SSO no Keycloak...", flush=True)
                        await page.fill('#username', USERNAME)
                        await page.fill('#password', PASSWORD)
                        await page.click('#kc-login')
                        await page.wait_for_url(f"**{QLIK_CLOUD_HOST}/analytics/**", timeout=60000)
                        await page.wait_for_timeout(3000)
                        await context.storage_state(path=STORAGE_STATE)
                except Exception:
                    pass

                await page.wait_for_timeout(3000)
                print("2/4 Sessão autenticada! Executando consultas no QIX Engine via WebSocket...", flush=True)
                raw_data = await page.evaluate(js_code)
            finally:
                await browser.close()

        if not raw_data or 'error' in raw_data:
            err_msg = raw_data.get('error') if raw_data else 'Sem dados'
            if os.path.exists(RAW_FILE):
                mtime = os.path.getmtime(RAW_FILE)
                if datetime.fromtimestamp(mtime).date() == dt_now.date():
                    print(f"\n⚠️ Qlik Cloud retornou aviso: {err_msg}")
                    print(f"ℹ️ Utilizando dados brutos existentes em cache de hoje ({datetime.fromtimestamp(mtime).strftime('%H:%M:%S')}) como fallback resiliente.")
                    with open(RAW_FILE, 'r', encoding='utf-8') as f:
                        return json.load(f)
            raise RuntimeError(f"Falha na extração Qlik Cloud: {err_msg}")

        # Salva arquivo bruto
        with open(RAW_FILE, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

        elapsed = time.time() - t0
        print("\n" + "=" * 75)
        print(f"EXTRAÇÃO QLIK CLOUD CONCLUÍDA COM SUCESSO EM {elapsed:.1f}s!")
        print(f"   Arquivo gerado: {RAW_FILE}")
        print(f"   Corte Atual: {raw_data.get('maxDataHora')} (Minuto: {raw_data.get('maxHora')})")
        print(f"   Linhas Hoje: {len(raw_data.get('rowsHoje', []))} | Ontem: {len(raw_data.get('rowsOntem', []))} | D-7: {len(raw_data.get('rowsD7', []))}")
        print(f"   Histórico Dia: {len(raw_data.get('rowsHistDia', []))}")
        print(f"   Grupos: {len(raw_data.get('rowsGrupos', []))} | Subgrupos: {len(raw_data.get('rowsSubgrupos', []))}")
        print(f"   Laboratórios: {len(raw_data.get('rowsLabs', []))} | Linhas: {len(raw_data.get('rowsLinhas', []))} | SKUs: {len(raw_data.get('rowsSKUs', []))}")
        print(f"   Regional: {len(raw_data.get('rowsUF', []))} UFs | {len(raw_data.get('rowsDir', []))} Diretorias | {len(raw_data.get('rowsCoord', []))} Coordenações | {len(raw_data.get('rowsFiliais', []))} Filiais")
        print("=" * 75)
        return raw_data
    finally:
        release_lock()

if __name__ == '__main__':
    res = asyncio.run(fetch_intraday_data())
    if res is None:
        if os.path.exists(RAW_FILE) and (time.time() - os.path.getmtime(RAW_FILE) < 600):
            print("ℹ️ Dados brutos atualizados recentemente por processo concorrente. Prosseguindo.")
            sys.exit(0)
        else:
            print("❌ Extração não pôde ser executada. Abortando ciclo.")
            sys.exit(1)
