import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ID = "671fa4f4-eb7d-418f-b4c9-936e87d8011d"

JS_QUERY = """async () => {
    const appId = "671fa4f4-eb7d-418f-b4c9-936e87d8011d";
    const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;
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

                // 1. Obter todas as Medidas Mestres (Master Measures) do App
                const cMeasures = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "MeasureList" },
                    "qMeasureListDef": {
                        "qType": "measure",
                        "qData": {
                            "title": "/title",
                            "tags": "/tags",
                            "qMeasure": "/qMeasure"
                        }
                    }
                }]);
                const hM = cMeasures.result.qReturn.qHandle;
                const lM = await send("GetLayout", hM, []);
                const masterMeasures = (lM.result.qLayout.qMeasureList?.qItems || []).map(item => ({
                    id: item.qInfo?.qId,
                    title: item.qMetaDef?.title,
                    expression: item.qData?.qMeasure?.qDef,
                    label: item.qData?.qMeasure?.qLabel
                }));

                // 2. Obter todas as Dimensões Mestres (Master Dimensions)
                const cDims = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "DimensionList" },
                    "qDimensionListDef": {
                        "qType": "dimension",
                        "qData": {
                            "title": "/title",
                            "tags": "/tags",
                            "qDim": "/qDim"
                        }
                    }
                }]);
                const hD = cDims.result.qReturn.qHandle;
                const lD = await send("GetLayout", hD, []);
                const masterDims = (lD.result.qLayout.qDimensionList?.qItems || []).map(item => ({
                    id: item.qInfo?.qId,
                    title: item.qMetaDef?.title,
                    fieldDefs: item.qData?.qDim?.qFieldDefs
                }));

                // 3. Obter todos os campos do modelo de dados
                const tablesRes = await send("GetTablesAndKeys", docHandle, [{}, {}, 0, false, false]);
                const allFields = [];
                for (const t of (tablesRes.result?.qtr || [])) {
                    for (const f of (t.qFields || [])) {
                        allFields.push({ table: t.qName, field: f.qName });
                    }
                }

                // 4. Testar expressões potenciais de 'Estoque' para o Mounjaro 5mg (10046653)
                const evalTests = {};
                
                // Medidas mestres encontradas que tenham "estoque" ou "saldo"
                const stockMeasures = masterMeasures.filter(m => /estoque|saldo|qtd|dispon/i.test(m.title + ' ' + (m.expression || '')));
                
                for (const sm of stockMeasures) {
                    try {
                        const r = await send("Evaluate", docHandle, [`${sm.expression}`]);
                        evalTests[`MasterMeasure_${sm.title}`] = {
                            expression: sm.expression,
                            valueTotal: r.result?.qReturn
                        };
                        // Avalia com Mounjaro 5mg
                        // Se a expressão usa {}, tentar injetar Produto_ID={'10046653'}
                        let exprMounj = sm.expression;
                        if (exprMounj.includes('{')) {
                            exprMounj = exprMounj.replace('{', "{<Produto_ID={'10046653'}>}");
                        } else {
                            exprMounj = `${sm.expression}`;
                        }
                    } catch(e) {
                        evalTests[`MasterMeasure_${sm.title}`] = { error: e.message };
                    }
                }

                // 5. Testar se existe campo 'Estoque' direto ou expressão [Estoque]
                const directTests = [
                    "Sum([Estoque])",
                    "Sum([Quantidade Saldo])",
                    "Sum([Quantidade Estoque])",
                    "Sum([Saldo Estoque])",
                    "Sum({1<Produto_ID={'10046653'}>} [Estoque])",
                    "Sum({1<Produto_ID={'10046653'}>} [Quantidade Saldo])",
                    "Sum({1<Produto_ID={'10046653'}>} [Qt_Estoque])",
                    "Sum({1<Produto_ID={'10046653'}>} [Saldo])"
                ];

                for (const dt of directTests) {
                    try {
                        const r = await send("Evaluate", docHandle, [dt]);
                        evalTests[dt] = r.result?.qReturn;
                    } catch(e) {
                        evalTests[dt] = "ERRO: " + e.message;
                    }
                }

                ws.close();
                resolve({
                    masterMeasures,
                    masterDims,
                    allFields,
                    stockMeasures,
                    evalTests
                });
            } catch (e) {
                ws.close();
                reject(e.message || String(e));
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
    });
}"""

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--ignore-certificate-errors'])
        context = await browser.new_context(
            ignore_https_errors=True,
            http_credentials={'username': USERNAME, 'password': PASSWORD}
        )
        page = await context.new_page()
        await page.goto(f"{QLIK_URL}/sense/app/{APP_ID}", timeout=60000)
        try:
            await page.wait_for_selector('.qv-panel-sheet', timeout=20000)
        except Exception:
            await page.wait_for_timeout(4000)

        res = await page.evaluate(JS_QUERY)
        await browser.close()

    print("=== TODAS AS MEDIDAS MESTRES DO APP (MASTER MEASURES) ===")
    for m in res.get("masterMeasures", []):
        print(f"• Title: {m.get('title')} | Expression: {m.get('expression')} | Label: {m.get('label')}")

    print("\n=== MEDIDAS MESTRES RELACIONADAS A ESTOQUE/SALDO ===")
    for sm in res.get("stockMeasures", []):
        print(f"• Title: {sm.get('title')} | Expression: {sm.get('expression')}")

    print("\n=== TESTES DE EXPRESSÕES DIRETAS ===")
    for k, v in res.get("evalTests", {}).items():
        print(f"  {k} => {v}")

    print("\n=== TODOS OS CAMPOS COM 'ESTOQUE' OU 'SALDO' NO MODELO ===")
    for f in res.get("allFields", []):
        if any(w in f['field'].upper() for w in ['ESTOQUE', 'SALDO', 'QTD', 'QUANT']):
            print(f"  Tabela: {f['table']} | Campo: {f['field']}")

if __name__ == "__main__":
    asyncio.run(run())
