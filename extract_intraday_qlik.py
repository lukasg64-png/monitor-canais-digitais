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
LOCK_FILE = os.path.join(DATA_DIR, 'sync.lock')

def is_pid_running(pid):
    try:
        import subprocess
        res = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True)
        return str(pid) in res.stdout
    except Exception:
        return False

def acquire_lock(timeout_sec=300):
    for _ in range(6):
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                lock_pid = data.get('pid')
                lock_time = data.get('time', 0)
                if time.time() - lock_time < timeout_sec and lock_pid and is_pid_running(lock_pid):
                    time.sleep(2.5)
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
                print(f"⚠️ Sincronização já em execução no processo PID {lock_pid}. Ignorando chamada concorrente.")
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
        let isResolved = false;
        console.log('[WS] Iniciando conexao WebSocket:', wsUrl);
        const ws = new WebSocket(wsUrl);
        let msgId = 1;
        const pending = {};

        function send(method, handle, params) {
            return new Promise((res, rej) => {
                const id = msgId++;
                pending[id] = { res, rej, method, t0: performance.now() };
                console.log(`[WS Send] #${id} ${method} handle=${handle}`);
                ws.send(JSON.stringify({ "jsonrpc": "2.0", "id": id, "method": method, "handle": handle, "params": params }));
            });
        }

        async function fetchAllHyperCubeRows(objHandle, totalRows, qWidth, pageSize, name = "Cube") {
            let rows = [];
            let top = 0;
            const t0 = performance.now();
            const effPageSize = Math.min(pageSize, 1500);
            while (top < totalRows) {
                const height = Math.min(effPageSize, totalRows - top);
                const pageRes = await send("GetHyperCubeData", objHandle, ["/qHyperCubeDef", [{ "qTop": top, "qLeft": 0, "qHeight": height, "qWidth": qWidth }]]);
                const matrix = pageRes.result.qDataPages[0]?.qMatrix || [];
                if (matrix.length === 0) break;
                matrix.forEach(r => rows.push(r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText)));
                top += matrix.length;
            }
            console.log(`[Qlik] ${name}: ${rows.length}/${totalRows} em ${(performance.now() - t0).toFixed(0)}ms`);
            return rows;
        }

        ws.onopen = async () => {
            try {
                console.log('[WS] Aberto com sucesso! Chamando OpenDoc...');
                const openRes = await send("OpenDoc", -1, [appId]);
                const docHandle = openRes.result.qReturn.qHandle;
                console.log(`[WS] OpenDoc conectado, docHandle=${docHandle}`);
                const resData = {};

                // 1. Timestamp mais recente do dia atual
                const evalDataHora = await send("Evaluate", docHandle, [`MaxString({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} DataHora)`]);
                resData.maxDataHora = evalDataHora.result.qReturn;

                const evalHora = await send("Evaluate", docHandle, [`Time(Frac(Max({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} Hora)), 'hh:mm')`]);
                resData.maxHora = evalHora.result.qReturn;

                const evalDate = await send("Evaluate", docHandle, [`Date(Floor(Max({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} Hora)), 'DD/MM/YYYY')`]);
                resData.maxDate = evalDate.result.qReturn;
                
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
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hH = cH.result.qReturn.qHandle;
                const lH = await send("GetLayout", hH, []);
                const totH = lH.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsHoje = await fetchAllHyperCubeRows(hH, totH, 4, 1500, "Hoje");

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
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hO = cO.result.qReturn.qHandle;
                const lO = await send("GetLayout", hO, []);
                const totO = lO.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsOntem = await fetchAllHyperCubeRows(hO, totO, 4, 1500, "Ontem");

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
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const h7 = c7.result.qReturn.qHandle;
                const l7 = await send("GetLayout", h7, []);
                const tot7 = l7.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsD7 = await fetchAllHyperCubeRows(h7, tot7, 4, 1500, "D7");

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
                resData.rowsSubgrupos = await fetchAllHyperCubeRows(hSub, totSub, 5, 1500, "Subgrupos");

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
                resData.rowsLabs = await fetchAllHyperCubeRows(hLabs, totLabs, 4, 1500, "Labs");

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
                resData.rowsLinhas = await fetchAllHyperCubeRows(hLin, totLin, 4, 1500, "Linhas");

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
                resData.rowsSKUs = await fetchAllHyperCubeRows(hSKU, Math.min(5000, totSKU), 6, 1500, "SKUs");

                // 11. Estados (UF Filial)
                const cUF = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_uf" },
                    "qHyperCubeDef": {
                        "qDimensions": [{ "qDef": { "qFieldDefs": ["UF Filial"] } }],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 10, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hUF = cUF.result.qReturn.qHandle;
                const lUF = await send("GetLayout", hUF, []);
                resData.rowsUF = (lUF.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText));

                // 12. Diretorias
                const cDir = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_diretor" },
                    "qHyperCubeDef": {
                        "qDimensions": [{ "qDef": { "qFieldDefs": ["Diretor"] } }],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 20, "qWidth": 4 }],
                        "qSuppressZero": true
                    }
                }]);
                const hDir = cDir.result.qReturn.qHandle;
                const lDir = await send("GetLayout", hDir, []);
                resData.rowsDir = (lDir.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText));

                // 13. Coordenações
                const cCoord = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_coord" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Coordenador"] } },
                            { "qDef": { "qFieldDefs": ["UF Filial"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 60, "qWidth": 5 }],
                        "qSuppressZero": true
                    }
                }]);
                const hCoord = cCoord.result.qReturn.qHandle;
                const lCoord = await send("GetLayout", hCoord, []);
                resData.rowsCoord = (lCoord.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || []).map(r => r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText));

                // 14. Filiais (Top Lojas por Faturamento Digital)
                const cFil = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_filiais" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { 
                                "qDef": { 
                                    "qFieldDefs": ["Filial_ID"],
                                    "qSortCriterias": [{
                                        "qSortByExpression": -1,
                                        "qExpression": { "qv": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida]) + Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` }
                                    }]
                                } 
                            },
                            { "qDef": { "qFieldDefs": ["Desc_Filial"] } },
                            { "qDef": { "qFieldDefs": ["UF Filial"] } },
                            { "qDef": { "qFieldDefs": ["Coordenador"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_HOJE%%'}, Dia={'%%DIA_HOJE%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_ONTEM%%'}, Dia={'%%DIA_ONTEM%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } },
                            { "qDef": { "qDef": `Sum({1<[Ano-Mes]={'%%ANO_MES_D7%%'}, Dia={'%%DIA_D7%%'}, [Canal]={${CHANNELS}}>} [Receita Líquida])` } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 250, "qWidth": 7 }],
                        "qSuppressZero": true
                    }
                }]);
                const hFil = cFil.result.qReturn.qHandle;
                const lFil = await send("GetLayout", hFil, []);
                const totFil = lFil.result.qLayout.qHyperCube.qSize.qcy;
                resData.rowsFiliais = await fetchAllHyperCubeRows(hFil, totFil, 7, 1000, "Filiais");

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

                isResolved = true;
                resolve(resData);
            } catch (e) {
                console.error("[Qlik Error in onopen]", e);
                ws.close();
                reject(new Error(e.message || String(e)));
            }
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.method === "OnMaxParallelSessionsExceeded") {
                console.error("[Qlik WS] Limite de sessões simultâneas atingido (OnMaxParallelSessionsExceeded)");
                try { ws.close(); } catch(e) {}
                reject(new Error("OnMaxParallelSessionsExceeded: Limite de sessões simultâneas atingido no Qlik Sense"));
                return;
            }
            if (msg.params && msg.params.severity === "fatal") {
                console.error("[Qlik WS Fatal]", JSON.stringify(msg.params));
                try { ws.close(); } catch(e) {}
                reject(new Error(`Qlik Fatal: ${msg.params.message || "Erro fatal no Qlik"}`));
                return;
            }
            if (msg.id && pending[msg.id]) {
                const { res, rej, method, t0 } = pending[msg.id];
                delete pending[msg.id];
                const dt = (performance.now() - t0).toFixed(0);
                if (msg.error) {
                    console.error(`[WS Err] #${msg.id} ${method} em ${dt}ms:`, JSON.stringify(msg.error));
                    rej(new Error(JSON.stringify(msg.error)));
                } else {
                    console.log(`[WS OK] #${msg.id} ${method} em ${dt}ms`);
                    res(msg);
                }
            } else if (msg.method) {
                console.log(`[WS Push] ${msg.method}`);
            }
        };

        ws.onerror = (e) => {
            console.error("[Qlik WS Error Event]", e);
        };

        ws.onclose = (e) => {
            console.log(`[Qlik WS Close Event] code=${e.code} reason=${e.reason}`);
            if (!isResolved && e.code !== 1000) {
                reject(new Error(`WebSocket fechado prematuramente: code=${e.code} reason=${e.reason}`));
            }
        };

        setTimeout(() => {
            try { ws.close(); } catch(e) {}
            if (!isResolved) {
                console.warn("[Qlik WS Timeout] Limite de 600s atingido no WebSocket.");
                resolve(null);
            }
        }, 600000);
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

def check_qlik_connection(timeout_sec=10.0):
    """Verifica se o Qlik Sense Enterprise responde antes de instanciar o navegador"""
    import urllib.request
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    test_url = SHEET_URL
    try:
        req = urllib.request.Request(test_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=timeout_sec) as r:
            return True, "OK"
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            return True, "OK"
        return False, str(e)

async def fetch_intraday_data(target_dt=None):
    if not acquire_lock():
        return None

    try:
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

        print("0/4 Verificando conectividade de rede com Qlik Sense...", flush=True)
        is_online, err_msg = check_qlik_connection(timeout_sec=10.0)
        if not is_online:
            print(f"❌ AVISO CRÍTICO: Não foi possível conectar a {QLIK_URL} ({err_msg})", flush=True)
            print("💡 DICA: Se estiver fora do escritório, conecte a VPN corporativa FSJ-VPN (FortiClient)!", flush=True)
            raise ConnectionError(
                f"Servidor Qlik Sense ({QLIK_URL}) inacessível. A VPN FSJ-VPN (FortiClient) está desconectada ou a rede corporativa está instável."
            )

        async with async_playwright() as p:
            print("1/4 Conectando ao Qlik Sense Enterprise...", flush=True)
            browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
            try:
                context = await browser.new_context(
                    ignore_https_errors=True,
                    http_credentials={'username': USERNAME, 'password': PASSWORD},
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                page.on("console", lambda msg: print(f"   [Qlik] {msg.text}", flush=True))
                await page.goto(SHEET_URL, timeout=90000)
                try:
                    await page.wait_for_selector('.qv-panel-sheet', timeout=30000)
                except Exception:
                    await page.wait_for_timeout(4000)

                print("2/4 Sessão autenticada! Executando consultas no QIX Engine via WebSocket...", flush=True)
                js_script = JS_TEMPLATE
                for k, v in replacements.items():
                    js_script = js_script.replace(k, v)

                raw_data = await page.evaluate(js_script)
            finally:
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
        print(f"   Regional: {len(raw_data.get('rowsUF', []))} UFs | {len(raw_data.get('rowsDir', []))} Diretorias | {len(raw_data.get('rowsCoord', []))} Coordenações | {len(raw_data.get('rowsFiliais', []))} Filiais")
        print("=" * 75)
        return raw_data
    finally:
        release_lock()

if __name__ == '__main__':
    res = asyncio.run(fetch_intraday_data())
    if res is None:
        if os.path.exists(RAW_FILE) and (time.time() - os.path.getmtime(RAW_FILE) < 180):
            print("ℹ️ Dados brutos atualizados recentemente por processo concorrente. Prosseguindo.")
            sys.exit(0)
        else:
            print("❌ Extração não pôde ser executada (bloqueio concorrente ou erro). Abortando ciclo.")
            sys.exit(1)
