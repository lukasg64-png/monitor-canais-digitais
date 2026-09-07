"""
analyze_stock_impact.py
Consulta todos os SKUs no app E-Commerce x Rede do Qlik Sense, extraindo:
- Produto_ID
- Desc_Produto
- Grupo / Categoria
- Saldo Estoque ([Quantidade Saldo])
- Venda Hoje (07/09/2026)
- Venda D-7 (31/08/2026)
- Quantidade Hoje e Quantidade D-7

Calcula o impacto financeiro exato (em R$) de itens sem estoque ou em estoque crítico!
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ID = "671fa4f4-eb7d-418f-b4c9-936e87d8011d"

JS_QUERY = """async () => {
    const appId = "671fa4f4-eb7d-418f-b4c9-936e87d8011d";
    const wsUrl = `wss://${window.location.host}/app/${encodeURIComponent(appId)}?reloadUri=https://${window.location.host}/`;
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

        ws.onopen = async () => {
            try {
                const openRes = await send("OpenDoc", -1, [appId]);
                const docHandle = openRes.result.qReturn.qHandle;

                // Consulta todos os produtos com venda hoje ou no D-7
                const cObj = await send("CreateSessionObject", docHandle, [{
                    "qInfo": { "qType": "q_stock_impact" },
                    "qHyperCubeDef": {
                        "qDimensions": [
                            { "qDef": { "qFieldDefs": ["Produto_ID"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Produto"] } },
                            { "qDef": { "qFieldDefs": ["Desc_Secao"] } }
                        ],
                        "qMeasures": [
                            { "qDef": { "qDef": "Sum({1} [Quantidade Saldo])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}>} [Receita Líquida])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}>} [Receita Líquida])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-09'}, Dia={'07'}>} [Quantidade Produto])" } },
                            { "qDef": { "qDef": "Sum({1<[Ano-Mes]={'2026-08'}, Dia={'31'}>} [Quantidade Produto])" } }
                        ],
                        "qInitialDataFetch": [{ "qTop": 0, "qLeft": 0, "qHeight": 500, "qWidth": 8 }],
                        "qSuppressZero": false
                    }
                }]);
                const h = cObj.result.qReturn.qHandle;
                const l = await send("GetLayout", h, []);
                const matrix = l.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
                const totalRows = l.result.qLayout.qHyperCube.qSize.qcy;

                // Paginação se houver mais de 500
                let allRows = matrix;
                let fetched = matrix.length;
                while (fetched < Math.min(totalRows, 3000)) {
                    const nextData = await send("GetHyperCubeData", h, ["/qHyperCubeDef", [{
                        "qTop": fetched,
                        "qLeft": 0,
                        "qHeight": 500,
                        "qWidth": 8
                    }]]);
                    const newBatch = nextData.result.qDataPages[0]?.qMatrix || [];
                    if (!newBatch.length) break;
                    allRows = allRows.concat(newBatch);
                    fetched += newBatch.length;
                }

                const rows = allRows.map(r => r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText));

                ws.close();
                resolve({ success: true, total: totalRows, rows: rows });
            } catch (e) {
                ws.close();
                resolve({ success: false, error: e.message || String(e) });
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
            resolve({ success: false, error: "timeout" });
        }, 45000);
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

    if not res.get("success"):
        print("Erro:", res.get("error"))
        return

    rows = res.get("rows", [])
    print(f"Total de SKUs retornados com movimento ou saldo: {len(rows)}")

    # Classificação
    # r[0]: id, r[1]: desc, r[2]: secao, r[3]: saldo, r[4]: v_hoje, r[5]: v_d7, r[6]: q_hoje, r[7]: q_d7
    ruptura_total = [] # saldo <= 0
    saldo_critico = [] # 0 < saldo <= 15
    saldo_regular = [] # saldo > 15

    total_perda_ruptura = 0.0
    total_perda_critico = 0.0
    total_perda_geral = 0.0

    for r in rows:
        def get_col(idx, default=None):
            if idx < len(r) and r[idx] is not None and str(r[idx]) != '-' and str(r[idx]) != 'NaN':
                return r[idx]
            return default

        sku = get_col(0, "")
        desc = get_col(1, "")
        secao = get_col(2, "")
        saldo = float(get_col(3, 0.0))
        v_hoje = float(get_col(4, 0.0))
        v_d7 = float(get_col(5, 0.0))
        q_hoje = float(get_col(6, 0.0))
        q_d7 = float(get_col(7, 0.0))

        gap_venda = v_hoje - v_d7 # se negativo, houve perda vs D-7

        item = {
            "sku": sku,
            "desc": desc,
            "secao": secao,
            "saldo": saldo,
            "v_hoje": v_hoje,
            "v_d7": v_d7,
            "gap": gap_venda
        }

        if gap_venda < 0:
            total_perda_geral += abs(gap_venda)
            if saldo <= 0:
                ruptura_total.append(item)
                total_perda_ruptura += abs(gap_venda)
            elif saldo <= 15:
                saldo_critico.append(item)
                total_perda_critico += abs(gap_venda)
            else:
                saldo_regular.append(item)

    # Ordena maiores perdas
    ruptura_total.sort(key=lambda x: x["gap"])
    saldo_critico.sort(key=lambda x: x["gap"])
    saldo_regular.sort(key=lambda x: x["gap"])

    print("\n" + "=" * 85)
    print("           DIAGNÓSTICO EXECUTIVO DE IMPACTO DE ESTOQUE NA VENDA (HOJE vs D-7)")
    print("=" * 85)
    print(f"Perda Total de Vendas em Produtos em Queda (GAP Negativo vs D-7): R$ {total_perda_geral:,.2f}")
    pct_ruptura = (total_perda_ruptura / total_perda_geral * 100) if total_perda_geral > 0 else 0
    pct_critico = (total_perda_critico / total_perda_geral * 100) if total_perda_geral > 0 else 0
    pct_estoque_total = ((total_perda_ruptura + total_perda_critico) / total_perda_geral * 100) if total_perda_geral > 0 else 0

    print(f"🚨 Perda Direta por RUPTURA TOTAL (Saldo <= 0):     R$ {total_perda_ruptura:,.2f} ({pct_ruptura:.1f}% do gap negativo)")
    print(f"⚠️ Perda por ESTOQUE CRÍTICO (Saldo <= 15 un):     R$ {total_perda_critico:,.2f} ({pct_critico:.1f}% do gap negativo)")
    print(f"🔴 IMPACTO TOTAL DE ESTOQUE/RUPTURA:                R$ {(total_perda_ruptura + total_perda_critico):,.2f} ({pct_estoque_total:.1f}% de toda a retração)")
    print(f"🟢 Perda Comercial em Itens Abastecidos (Saldo > 15): R$ {(total_perda_geral - total_perda_ruptura - total_perda_critico):,.2f}")

    print("\n" + "-" * 85)
    print("TOP ITENS COM RETRAÇÃO E RUPTURA TOTAL (Saldo <= 0):")
    print("-" * 85)
    for it in ruptura_total[:10]:
        print(f"SKU {it['sku']} | {it['desc'][:35]:<35} | {it['secao'][:15]:<15} | Saldo: {it['saldo']:>3.0f} un | Hoje: R$ {it['v_hoje']:>7,.0f} | D-7: R$ {it['v_d7']:>7,.0f} | Perda: R$ {it['gap']:>8,.0f}")

    print("\n" + "-" * 85)
    print("TOP ITENS COM RETRAÇÃO E ESTOQUE CRÍTICO (Saldo <= 15 un):")
    print("-" * 85)
    for it in saldo_critico[:10]:
        print(f"SKU {it['sku']} | {it['desc'][:35]:<35} | {it['secao'][:15]:<15} | Saldo: {it['saldo']:>3.0f} un | Hoje: R$ {it['v_hoje']:>7,.0f} | D-7: R$ {it['v_d7']:>7,.0f} | Perda: R$ {it['gap']:>8,.0f}")

    # Salva resultado em JSON para consumo
    summary = {
        "total_perda_geral": total_perda_geral,
        "total_perda_ruptura": total_perda_ruptura,
        "total_perda_critico": total_perda_critico,
        "impacto_estoque_total": total_perda_ruptura + total_perda_critico,
        "pct_impacto_estoque": pct_estoque_total,
        "top_ruptura": ruptura_total[:15],
        "top_critico": saldo_critico[:15]
    }
    with open("data/stock_impact_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\nResumo salvo em data/stock_impact_summary.json com sucesso!")

if __name__ == "__main__":
    asyncio.run(run())
