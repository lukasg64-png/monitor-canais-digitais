"""
test_lojas_ruptura.py
Consulta no app E-Commerce x Rede:
- Total de lojas ativas (Count(distinct Filial_ID))
- Para os principais SKUs:
  - Saldo Total de Estoque (Sum([Quantidade Saldo]))
  - Lojas com Estoque > 0 (Count(distinct if([Quantidade Saldo] > 0, Filial_ID)))
  - Lojas em Ruptura / Saldo <= 0 (Count(distinct if([Quantidade Saldo] <= 0 or IsNull([Quantidade Saldo]), Filial_ID)))
  - Taxa de Ruptura Capilar da Loja (% de lojas sem produto)
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

                // 1. Total de filiais na rede
                const eTotLojas = await send("Evaluate", docHandle, ["Count(distinct Filial_ID)"]);
                const totalLojas = eTotLojas.result?.qReturn || "0";

                // 2. Consulta SKUs com Saldo Total, Lojas com Estoque e Vendas
                const cSKU = await send("CreateSessionObject", docHandle, [{{
                    "qInfo": {{ "qType": "q_skus_lojas_ruptura" }},
                    "qHyperCubeDef": {{
                        "qDimensions": [
                            {{ "qDef": {{ "qFieldDefs": ["Produto_ID"] }} }},
                            {{ "qDef": {{ "qFieldDefs": ["Desc_Produto"] }} }}
                        ],
                        "qMeasures": [
                            {{ "qDef": {{ "qDef": `Sum({{1<[Ano-Mes]={{'2026-09'}}, Dia={{'07'}}, [Canal]={{{CHANNELS}}}>}} [Receita Líquida])` }} }},
                            {{ "qDef": {{ "qDef": `Sum({{1<[Ano-Mes]={{'2026-08'}}, Dia={{'31'}}, [Canal]={{{CHANNELS}}}>}} [Receita Líquida])` }} }},
                            {{ "qDef": {{ "qDef": "Sum({1} [Quantidade Saldo])" }} }},
                            {{ "qDef": {{ "qDef": "Count(distinct {{1<[Quantidade Saldo]={{'>0'}}>}} Filial_ID)" }} }}
                        ],
                        "qInitialDataFetch": [{{ "qTop": 0, "qLeft": 0, "qHeight": 100, "qWidth": 6 }}],
                        "qSuppressZero": true
                    }}
                }}]);

                const hSKU = cSKU.result.qReturn.qHandle;
                const lSKU = await send("GetLayout", hSKU, []);
                const matrix = lSKU.result.qLayout.qHyperCube.qDataPages[0]?.qMatrix || [];
                const rows = matrix.map(r => r.map(c => c.qNum !== 'NaN' && typeof c.qNum === 'number' ? c.qNum : c.qText));

                ws.close();
                resolve({{ success: true, totalLojas: totalLojas, rows: rows }});
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

    print(f"Total de Lojas na base do Qlik: {res.get('totalLojas')}")
    rows = res.get("rows", [])
    tot_lojas = float(res.get('totalLojas', 1200) or 1200)

    print("\n" + "=" * 105)
    print("      AUDITORIA DE RUPTURA CAPILAR: QUANTAS LOJAS TÊM ESTOQUE DO PRODUTO?")
    print("=" * 105)
    for r in rows[:25]:
        v_hoje = float(r[2]) if r[2] not in ['-', None] else 0.0
        v_d7 = float(r[3]) if r[3] not in ['-', None] else 0.0
        saldo = float(r[4]) if r[4] not in ['-', None] else 0.0
        lojas_com_estoque = float(r[5]) if r[5] not in ['-', None] else 0.0
        
        pct_cobertura = (lojas_com_estoque / tot_lojas * 100) if tot_lojas > 0 else 0
        pct_ruptura = 100.0 - pct_cobertura
        un_por_loja = (saldo / lojas_com_estoque) if lojas_com_estoque > 0 else 0

        status_capilar = "🚨 RUPTURA GRAVE (>80% lojas sem)" if pct_ruptura >= 80 else ("⚠️ RUPTURA MÉDIA (>50%)" if pct_ruptura >= 50 else "✅ BOA DISTRIBUIÇÃO")
        print(f"SKU {r[0]:<10} | {str(r[1])[:32]:<32} | Saldo: {saldo:>6.0f} un | Lojas c/ Est: {lojas_com_estoque:>4.0f}/{tot_lojas:.0f} ({pct_cobertura:>4.1f}%) | Ruptura: {pct_ruptura:>4.1f}% | {status_capilar}")

if __name__ == "__main__":
    asyncio.run(run())
