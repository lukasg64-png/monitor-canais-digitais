"""
test_skus_with_saldo.py
Consulta os Top SKUs com seus valores de Venda Hoje, Ontem, D-7 E o Saldo de Estoque [Quantidade Saldo].
Calcula com precisão o impacto financeiro da falta de estoque nos maiores detratores!
"""
import asyncio, json, sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

USERNAME = "lucas.alves6"
PASSWORD = "Eloise2025*"
QLIK_URL = "https://sense.farmaciassaojoao.com.br"
APP_ID = "671fa4f4-eb7d-418f-b4c9-936e87d8011d"
CHANNELS = "'APP', 'APP Tele Entrega', 'SITE', 'SITE Tele Entrega', 'iFood', 'e_Commerce'"

JS_QUERY = f"""async () => {{
    const appId = "671fa4f4-eb7d-418f-b4c9-936e87d8011d";
    const wsUrl = `wss://${{window.location.host}}/app/${{encodeURIComponent(appId)}}?reloadUri=https://${{window.location.host}}/`;
    const CHANNELS = "{CHANNELS}";

    return new Promise((resolve) => {{
        const ws = new WebSocket(wsUrl);
        let msgId = 1;
        const pending = {{}};

        function send(method, handle, params) {{
            return new Promise((res, rej) => {{
                const id = msgId++;
                pending[id] = {{ res, rej }};
                ws.send(JSON.stringify({{ "jsonrpc": "2.0", "id": id, "method": method, "handle": handle, "params": params }}));
            }});
        }}

        ws.onopen = async () => {{
            try {{
                const openRes = await send("OpenDoc", -1, [appId]);
                const docHandle = openRes.result.qReturn.qHandle;

                const cSKU = await send("CreateSessionObject", docHandle, [{{
                    "qInfo": {{ "qType": "q_top_skus_with_saldo" }},
                    "qHyperCubeDef": {{
                        "qDimensions": [
                            {{ "qDef": {{ "qFieldDefs": ["Produto_ID"] }} }},
                            {{ "qDef": {{ "qFieldDefs": ["Desc_Produto"] }} }}
                        ],
                        "qMeasures": [
                            {{ "qDef": {{ "qDef": `Sum({{1<[Ano-Mes]={{'2026-09'}}, Dia={{'07'}}, [Canal]={{{CHANNELS}}}>}} [Receita Líquida])` }} }},
                            {{ "qDef": {{ "qDef": `Sum({{1<[Ano-Mes]={{'2026-09'}}, Dia={{'06'}}, [Canal]={{{CHANNELS}}}>}} [Receita Líquida])` }} }},
                            {{ "qDef": {{ "qDef": `Sum({{1<[Ano-Mes]={{'2026-08'}}, Dia={{'31'}}, [Canal]={{{CHANNELS}}}>}} [Receita Líquida])` }} }},
                            {{ "qDef": {{ "qDef": `Sum({{1}} [Quantidade Saldo])` }} }}
                        ],
                        "qInitialDataFetch": [{{ "qTop": 0, "qLeft": 0, "qHeight": 1500, "qWidth": 6 }}],
                        "qSuppressZero": true
                    }}
                }}]);

                const hSKU = cSKU.result.qReturn.qHandle;
                const lSKU = await send("GetLayout", hSKU, []);
                const totSKU = lSKU.result.qLayout.qHyperCube.qSize.qcy;

                let allRows = [];
                let top = 0;
                while (top < Math.min(2500, totSKU)) {{
                    const height = Math.min(1000, totSKU - top);
                    const pageRes = await send("GetHyperCubeData", hSKU, ["/qHyperCubeDef", [{{ "qTop": top, "qLeft": 0, "qHeight": height, "qWidth": 6 }}]]);
                    const matrix = pageRes.result.qDataPages[0]?.qMatrix || [];
                    if (matrix.length === 0) break;
                    matrix.forEach(r => allRows.push(r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText)));
                    top += matrix.length;
                }}

                ws.close();
                resolve({{ success: true, total: totSKU, rows: allRows }});
            }} catch (e) {{
                ws.close();
                resolve({{ success: false, error: e.message || String(e) }});
            }}
        }};

        ws.onmessage = (event) => {{
            const msg = JSON.parse(event.data);
            if (msg.id && pending[msg.id]) {{
                const {{ res, rej }} = pending[msg.id];
                delete pending[msg.id];
                if (msg.error) rej(new Error(JSON.stringify(msg.error)));
                else res(msg);
            }}
        }};

        setTimeout(() => {{
            try {{ ws.close(); }} catch(e) {{}}
            resolve({{ success: false, error: "timeout" }});
        }}, 35000);
    }});
}}"""

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
    print(f"Total de SKUs extraídos dos canais digitais: {len(rows)}")

    items = []
    for r in rows:
        def num(val):
            if val is None or val == '-' or val == 'NaN': return 0.0
            try: return float(val)
            except: return 0.0

        sku = str(r[0])
        desc = str(r[1])
        hoje = num(r[2])
        ontem = num(r[3])
        d7 = num(r[4])
        saldo = num(r[5]) if len(r) > 5 else 0.0

        gap_d7 = hoje - d7
        gap_d1 = hoje - ontem

        items.append({
            "sku": sku,
            "desc": desc,
            "hoje": hoje,
            "ontem": ontem,
            "d7": d7,
            "saldo": saldo,
            "gap_d7": gap_d7,
            "gap_d1": gap_d1
        })

    # Ordena maiores detratores vs D-7
    detratores = [it for it in items if it["gap_d7"] < 0]
    detratores.sort(key=lambda x: x["gap_d7"])

    alavancadores = [it for it in items if it["gap_d7"] > 0]
    alavancadores.sort(key=lambda x: x["gap_d7"], reverse=True)

    print("\n" + "=" * 95)
    print("        TOP 20 MAIORES DETRATORES (QUEDA VS D-7) COM SALDO DE ESTOQUE REAL:")
    print("=" * 95)
    
    perda_total_detratores = sum(abs(it["gap_d7"]) for it in detratores)
    perda_ruptura = 0.0 # saldo <= 0
    perda_critico = 0.0 # saldo <= 15
    perda_regular = 0.0 # saldo > 15

    for it in detratores:
        g = abs(it["gap_d7"])
        if it["saldo"] <= 0:
            perda_ruptura += g
        elif it["saldo"] <= 15:
            perda_critico += g
        else:
            perda_regular += g

    for it in detratores[:20]:
        saldo_fmt = f"{int(it['saldo']):,} un".replace(",", ".")
        if it["saldo"] <= 0:
            tag = "🚨 RUPTURA ZERO"
        elif it["saldo"] <= 15:
            tag = "⚠️ CRÍTICO"
        else:
            tag = "✅ ESTOQUE OK"

        print(f"SKU {it['sku']:<10} | {it['desc'][:38]:<38} | Saldo: {saldo_fmt:>9} ({tag:<14}) | Hoje: R$ {it['hoje']:>7,.0f} | D-7: R$ {it['d7']:>7,.0f} | GAP: R$ {it['gap_d7']:>8,.0f}")

    print("\n" + "=" * 95)
    print("                    IMPACTO FINANCEIRO DO ESTOQUE NA VENDA DIGITAL:")
    print("=" * 95)
    pct_rup = (perda_ruptura / perda_total_detratores * 100) if perda_total_detratores else 0
    pct_crit = (perda_critico / perda_total_detratores * 100) if perda_total_detratores else 0
    pct_total_est = ((perda_ruptura + perda_critico) / perda_total_detratores * 100) if perda_total_detratores else 0

    print(f"Perda Total de Vendas nos Itens em Queda vs D-7: R$ {perda_total_detratores:,.2f}")
    print(f"🚨 Perda por RUPTURA TOTAL (Saldo = 0 un):       R$ {perda_ruptura:,.2f} ({pct_rup:.1f}% da perda)")
    print(f"⚠️ Perda por ESTOQUE CRÍTICO (Saldo <= 15 un):    R$ {perda_critico:,.2f} ({pct_crit:.1f}% da perda)")
    print(f"🔴 IMPACTO TOTAL DE ESTOQUE/RUPTURA:              R$ {(perda_ruptura + perda_critico):,.2f} ({pct_total_est:.1f}% da perda)")
    print(f"🟢 Perda Comercial / Demanda (Estoque > 15 un):   R$ {perda_regular:,.2f} ({(100 - pct_total_est):.1f}% da perda)")

    # Salva para uso
    with open("data/stock_impact_analysis.json", "w", encoding="utf-8") as f:
        json.dump({
            "perda_total_detratores": perda_total_detratores,
            "perda_ruptura": perda_ruptura,
            "perda_critico": perda_critico,
            "impacto_estoque_total": perda_ruptura + perda_critico,
            "pct_impacto_estoque": pct_total_est,
            "top_detratores": detratores[:30]
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(run())
