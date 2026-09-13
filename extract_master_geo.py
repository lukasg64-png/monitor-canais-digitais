import asyncio, json, os, sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ID = "671fa4f4-eb7d-418f-b4c9-936e87d8011d"
SHEET_ID = "ddd70c77-1a06-40d9-aff2-efa4b6b67b24"
SHEET_URL = f"{QLIK_URL}/sense/app/{APP_ID}/sheet/{SHEET_ID}/state/analysis"

JS_EXTRACT_MASTER_GEO = """async () => {
    function connectApp(appId) {
        return new Promise((resolve, reject) => {
            const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;
            const ws = new WebSocket(wsUrl);
            let msgId = 1;
            const pending = {};

            function send(method, handle, params) {
                return new Promise((res, rej) => {
                    const id = msgId++;
                    pending[id] = { res, rej };
                    ws.send(JSON.stringify({ jsonrpc: "2.0", id, method, handle, params }));
                });
            }

            ws.onmessage = (e) => {
                const m = JSON.parse(e.data);
                if (m.id && pending[m.id]) {
                    const { res, rej } = pending[m.id];
                    delete pending[m.id];
                    if (m.error) rej(new Error(JSON.stringify(m.error)));
                    else res(m);
                }
            };

            ws.onopen = async () => {
                try {
                    const openRes = await send("OpenDoc", -1, [appId]);
                    resolve({ ws, send, docHandle: openRes.result.qReturn.qHandle });
                } catch(err) {
                    ws.close();
                    reject(err);
                }
            };
        });
    }

    async function fetchAll(send, objHandle, totalRows, qWidth) {
        let rows = [];
        let top = 0;
        // Limite estrito do Qlik: height * width <= 9000
        const pageSize = Math.min(800, Math.floor(9000 / qWidth));
        while (top < totalRows) {
            const height = Math.min(pageSize, totalRows - top);
            const pRes = await send("GetHyperCubeData", objHandle, ["/qHyperCubeDef", [{ "qTop": top, "qLeft": 0, "qHeight": height, "qWidth": qWidth }]]);
            const m = pRes.result?.qDataPages[0]?.qMatrix || [];
            if (m.length === 0) break;
            m.forEach(r => rows.push(r.map(c => c.qText)));
            top += m.length;
        }
        return rows;
    }

    const result = { ruptura: [], estoque: [] };

    // 1. Extrair Ruptura (Filial_ID, Desc_Filial, UF, Latitude, Longitude, Diretor, Coordenador)
    try {
        const appR = await connectApp("4c210d43-3ea6-45ea-994f-ced22d3ceb0d");
        const cR = await appR.send("CreateSessionObject", appR.docHandle, [{
            "qInfo": { "qType": "q_ruptura_geo_full" },
            "qHyperCubeDef": {
                "qDimensions": [
                    { "qDef": { "qFieldDefs": ["Filial_ID"] } },
                    { "qDef": { "qFieldDefs": ["Desc_Filial"] } },
                    { "qDef": { "qFieldDefs": ["UF"] } },
                    { "qDef": { "qFieldDefs": ["Latitude"] } },
                    { "qDef": { "qFieldDefs": ["Longitude"] } },
                    { "qDef": { "qFieldDefs": ["Diretor"] } },
                    { "qDef": { "qFieldDefs": ["Coordenador"] } }
                ],
                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 500, "qWidth": 7 }]
            }
        }]);
        const hR = cR.result.qReturn.qHandle;
        const lR = await appR.send("GetLayout", hR, []);
        const totR = lR.result.qLayout.qHyperCube.qSize.qcy;
        result.ruptura = await fetchAll(appR.send, hR, totR, 7);
        appR.ws.close();
    } catch(e) {
        result.err_ruptura = e.message || String(e);
    }

    // 2. Extrair Estoque Final (Desc_Filial, Cidade, UF)
    try {
        const appE = await connectApp("936a28fb-245f-4f19-b285-420535685c43");
        const cE = await appE.send("CreateSessionObject", appE.docHandle, [{
            "qInfo": { "qType": "q_estoque_cidades_full" },
            "qHyperCubeDef": {
                "qDimensions": [
                    { "qDef": { "qFieldDefs": ["Desc_Filial"] } },
                    { "qDef": { "qFieldDefs": ["Cidade"] } },
                    { "qDef": { "qFieldDefs": ["UF"] } }
                ],
                "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 1000, "qWidth": 3 }]
            }
        }]);
        const hE = cE.result.qReturn.qHandle;
        const lE = await appE.send("GetLayout", hE, []);
        const totE = lE.result.qLayout.qHyperCube.qSize.qcy;
        result.estoque = await fetchAll(appE.send, hE, totE, 3);
        appE.ws.close();
    } catch(e) {
        result.err_estoque = e.message || String(e);
    }

    return result;
};"""

async def run():
    print("Iniciando extração do Master Geográfico do Qlik Sense...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD},
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        await page.goto(SHEET_URL, timeout=90000)
        try:
            await page.wait_for_selector('.qv-panel-sheet', timeout=30000)
        except Exception:
            await page.wait_for_timeout(4000)

        print("Executando consulta dos dados mestres de lojas...")
        res = await page.evaluate(JS_EXTRACT_MASTER_GEO)
        await browser.close()

    print(f"Ruptura rows: {len(res.get('ruptura', []))} | Erro: {res.get('err_ruptura')}")
    print(f"Estoque rows: {len(res.get('estoque', []))} | Erro: {res.get('err_estoque')}")

    # Build Master Store Geo Dictionary
    cidade_map = {}
    for r in res.get("estoque", []):
        if len(r) >= 2 and r[0] and r[1]:
            nome_norm = str(r[0]).strip().upper()
            cid = str(r[1]).strip().title()
            cidade_map[nome_norm] = cid

    lojas_master = {}
    import re
    for r in res.get("ruptura", []):
        if len(r) < 5:
            continue
        fid = str(r[0]).strip()
        fnum = fid.split("|")[-1] if "|" in fid else fid
        fdesc = str(r[1]).strip() if r[1] else f"Filial {fnum}"
        uf = str(r[2]).strip().upper() if r[2] else "RS"
        lat_str = str(r[3]).strip().replace("*", "").replace(",", ".") if r[3] else None
        lon_str = str(r[4]).strip().replace("*", "").replace(",", ".") if r[4] else None
        diretor = str(r[5]).strip() if len(r) > 5 and r[5] else ""
        coord = str(r[6]).strip() if len(r) > 6 and r[6] else ""

        try:
            lat = float(lat_str) if lat_str and lat_str not in ("-", "None", "") else None
            lon = float(lon_str) if lon_str and lon_str not in ("-", "None", "") else None
        except Exception:
            lat, lon = None, None

        cidade = cidade_map.get(fdesc.upper(), "")
        if not cidade:
            m = re.match(r"^([A-Za-zÀ-ÿ\s\-]+?)(?:\s+\d+|\s+Dark\s+Store|\s+Matriz|$)", fdesc)
            if m:
                cidade = m.group(1).strip().title()
            else:
                cidade = fdesc

        lojas_master[fnum] = {
            "filial_id": fnum,
            "raw_id": fid,
            "desc_filial": fdesc,
            "uf": uf,
            "cidade": cidade,
            "latitude": lat,
            "longitude": lon,
            "diretor": diretor,
            "coordenador": coord
        }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lojas_master_geo.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(lojas_master, f, ensure_ascii=False, indent=2)

    print(f"✅ Master Geo salvo com sucesso! {len(lojas_master)} lojas mapeadas em {out_path}")
    if lojas_master:
        sample_key = list(lojas_master.keys())[0]
        print(f"Exemplo de loja ({sample_key}): {lojas_master[sample_key]}")

if __name__ == "__main__":
    asyncio.run(run())
