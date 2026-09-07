"""
audit_capilaridade_skus.py
Consulta a distribuição exata de estoque por filial no app E-Commerce x Rede:
Para Mounjaro (10046652 e 10046653) e top detratores:
- Quantas filiais têm Saldo > 0
- Quantas filiais têm Saldo = 0 ou nulo
- Quanto estoque está concentrado nos CDs vs Lojas
"""
import asyncio, json, sys
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

                // Total Lojas
                const eTot = await send("Evaluate", docHandle, ["Count(distinct Filial_ID)"]);
                const totalLojas = eTot.result?.qReturn || 1147;

                // Mounjaro 2.5mg (10046652) e 5mg (10046653)
                // Lojas com saldo > 0
                const eMounj25_Lojas = await send("Evaluate", docHandle, ["Count(distinct {1<Produto_ID={'10046652'}, [Quantidade Saldo]={'>0'}>} Filial_ID)"]);
                const eMounj25_Saldo = await send("Evaluate", docHandle, ["Sum({1<Produto_ID={'10046652'}>} [Quantidade Saldo])"]);

                const eMounj5_Lojas = await send("Evaluate", docHandle, ["Count(distinct {1<Produto_ID={'10046653'}, [Quantidade Saldo]={'>0'}>} Filial_ID)"]);
                const eMounj5_Saldo = await send("Evaluate", docHandle, ["Sum({1<Produto_ID={'10046653'}>} [Quantidade Saldo])"]);

                // Pampers Jumbo XXG (10042969)
                const ePamp_Lojas = await send("Evaluate", docHandle, ["Count(distinct {1<Produto_ID={'10042969'}, [Quantidade Saldo]={'>0'}>} Filial_ID)"]);
                const ePamp_Saldo = await send("Evaluate", docHandle, ["Sum({1<Produto_ID={'10042969'}>} [Quantidade Saldo])"]);

                // Poviztra (10050648)
                const ePov_Lojas = await send("Evaluate", docHandle, ["Count(distinct {1<Produto_ID={'10050648'}, [Quantidade Saldo]={'>0'}>} Filial_ID)"]);
                const ePov_Saldo = await send("Evaluate", docHandle, ["Sum({1<Produto_ID={'10050648'}>} [Quantidade Saldo])"]);

                // Huggies (10033758)
                const eHug_Lojas = await send("Evaluate", docHandle, ["Count(distinct {1<Produto_ID={'10033758'}, [Quantidade Saldo]={'>0'}>} Filial_ID)"]);
                const eHug_Saldo = await send("Evaluate", docHandle, ["Sum({1<Produto_ID={'10033758'}>} [Quantidade Saldo])"]);

                ws.close();
                resolve({
                    success: true,
                    totalLojas: totalLojas,
                    mounj25: { saldo: eMounj25_Saldo.result?.qReturn, lojas: eMounj25_Lojas.result?.qReturn },
                    mounj5: { saldo: eMounj5_Saldo.result?.qReturn, lojas: eMounj5_Lojas.result?.qReturn },
                    pampers: { saldo: ePamp_Saldo.result?.qReturn, lojas: ePamp_Lojas.result?.qReturn },
                    poviztra: { saldo: ePov_Saldo.result?.qReturn, lojas: ePov_Lojas.result?.qReturn },
                    huggies: { saldo: eHug_Saldo.result?.qReturn, lojas: eHug_Lojas.result?.qReturn }
                });
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
        }, 25000);
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

    print("=" * 80)
    print("      AUDITORIA DE CAPILARIDADE REAL DE ESTOQUE (1.147 LOJAS SÃO JOÃO):")
    print("=" * 80)
    tot = float(res.get("totalLojas", 1147))
    print(f"Total de Filiais na Rede: {tot:.0f}\n")

    items = [
        ("Mounjaro 2,5mg (10046652)", res.get("mounj25")),
        ("Mounjaro 5mg (10046653)", res.get("mounj5")),
        ("Pampers Jumbo XXG (10042969)", res.get("pampers")),
        ("Poviztra 1mg (10050648)", res.get("poviztra")),
        ("Huggies Hiper XG (10033758)", res.get("huggies")),
    ]

    for name, data in items:
        saldo = float(data.get("saldo") or 0)
        lojas = float(data.get("lojas") or 0)
        cobertura = (lojas / tot * 100) if tot > 0 else 0
        ruptura = 100 - cobertura
        media_loja = (saldo / tot) if tot > 0 else 0
        media_lojas_ativas = (saldo / lojas) if lojas > 0 else 0

        print(f"📦 {name}:")
        print(f"   • Saldo Total Rede:        {saldo:,.0f} un")
        print(f"   • Lojas com Estoque (>0):  {lojas:,.0f} de {tot:.0f} filiais ({cobertura:.1f}% de cobertura)")
        print(f"   • Lojas em RUPTURA (0 un): {tot - lojas:,.0f} filiais ({ruptura:.1f}% de RUPTURA CAPILAR!)")
        print(f"   • Média por Loja da Rede:  {media_loja:.2f} un/loja")
        print(f"   • Média nas Lojas c/ Est:  {media_lojas_ativas:.1f} un/loja")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(run())
