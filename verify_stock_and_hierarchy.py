import asyncio
import os
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots_stock")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def test_stock_and_hierarchy():
    print("Iniciando verificação completa de Estoque & Dupla Hierarquia...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 1100})
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"PAGE ERROR: {err}"))
        page.on("console", lambda msg: print(f"   [Browser] {msg.text}") if "error" in msg.type.lower() else None)

        print("Carregando dashboard em http://127.0.0.1:3000 ...")
        await page.goto("http://127.0.0.1:3000", timeout=30000)
        await page.wait_for_timeout(2500)

        # 1. TESTE DE CLICK-THROUGH: Da Aba Principal para a Aba de Estoque
        print("\n--- 1. TESTE DE CLICK-THROUGH DO RADAR DE ALERTA ---")
        card_ruptura = page.locator(".alerta-card-ruptura")
        await card_ruptura.wait_for(state="visible", timeout=10000)
        print("Card de Ruptura visível na Aba Principal. Clicando no card...")
        await card_ruptura.click()
        await page.wait_for_timeout(2000)

        # Verifica se navegou para a Aba 4
        is_estoque_visible = await page.is_visible("#view-estoque-container")
        print(f"Container #view-estoque-container visível: {is_estoque_visible}")
        assert is_estoque_visible, "Falha: #view-estoque-container não ficou visível após clique no card de ruptura!"

        tab_estoque_btn_active = await page.evaluate("() => document.getElementById('tab-btn-estoque')?.classList.contains('active')")
        print(f"Botão da aba Estoque ativo: {tab_estoque_btn_active}")

        # Valida KPIs do Topo
        val_perda_ruptura = await page.inner_text("#stock-kpi-perda-ruptura")
        val_pct_ruptura = await page.inner_text("#stock-kpi-pct-ruptura")
        val_skus_criticos = await page.inner_text("#stock-kpi-skus-criticos")
        val_lojas_afetadas = await page.inner_text("#stock-kpi-lojas-afetadas")
        print(f"Scorecard Estoque: Perda={val_perda_ruptura} | Pct={val_pct_ruptura} | SKUs={val_skus_criticos} | Lojas={val_lojas_afetadas}")

        # Screenshot 1: Topo da Aba de Estoque & Tríade
        ss1 = os.path.join(SCREENSHOT_DIR, "1_estoque_kpis_triade.png")
        await page.screenshot(path=ss1, full_page=False)
        print(f"Screenshot 1 salva: {ss1}")

        # 2. TESTE DE LOCALIZAÇÃO DO PROBLEMA (Split View Geografia vs Organização)
        print("\n--- 2. TESTE DE LOCALIZAÇÃO DO PROBLEMA (SPLIT VIEW) ---")
        await page.evaluate("window.scrollTo(0, 500)")
        await page.wait_for_timeout(1000)

        # Testa visão por Geografia
        print("Validando visualização por Geografia...")
        await page.click("#btn-stock-hier-geo")
        await page.wait_for_timeout(1000)
        ranking_items_geo = await page.locator("#stock-ranking-list .stock-ranking-item").count()
        print(f"Itens no ranking de Geografia: {ranking_items_geo}")

        # Testa visão por Organização
        print("Alternando para visualização por Organização (Diretoria ➔ Coordenação)...")
        await page.click("#btn-stock-hier-org")
        await page.wait_for_timeout(1500)
        ranking_items_org = await page.locator("#stock-ranking-list .stock-ranking-item").count()
        print(f"Itens no ranking de Organização: {ranking_items_org}")

        detail_title = await page.inner_text("#stock-detail-title")
        print(f"Título do detalhamento selecionado: {detail_title}")

        # Screenshot 2: Painel Onde está o Problema
        ss2 = os.path.join(SCREENSHOT_DIR, "2_estoque_localizacao_problema.png")
        await page.screenshot(path=ss2, full_page=False)
        print(f"Screenshot 2 salva: {ss2}")

        # 3. TESTE DA MATRIZ DE SKUS EM RUPTURA CRÍTICA
        print("\n--- 3. TESTE DA MATRIZ DE SKUS EM RUPTURA CRÍTICA ---")
        await page.evaluate("window.scrollTo(0, 1100)")
        await page.wait_for_timeout(1000)

        skus_rows = await page.locator("#stock-table-tbody tr").count()
        print(f"Linhas na tabela de SKUs em Ruptura: {skus_rows}")

        # Testa busca por SKU
        print("Testando busca na tabela de estoque...")
        await page.fill("#stock-search-input", "Mounjaro")
        await page.wait_for_timeout(800)
        rows_filtered = await page.locator("#stock-table-tbody tr").count()
        print(f"Linhas filtradas por 'Mounjaro': {rows_filtered}")

        # Limpa busca
        await page.fill("#stock-search-input", "")
        await page.wait_for_timeout(500)

        # Screenshot 3: Matriz de SKUs
        ss3 = os.path.join(SCREENSHOT_DIR, "3_estoque_matriz_skus.png")
        await page.screenshot(path=ss3, full_page=False)
        print(f"Screenshot 3 salva: {ss3}")

        # 4. TESTE DA DUPLA HIERARQUIA NA ABA REGIONAL (Aba 3)
        print("\n--- 4. TESTE DA DUPLA HIERARQUIA NA ABA REGIONAL ---")
        await page.click("#tab-btn-regional")
        await page.wait_for_timeout(2000)

        # Testa alternar para Árvore Organizacional
        print("Clicando no botão 'Árvore Organizacional' na Aba Regional...")
        await page.click("#btn-tree-org")
        await page.wait_for_timeout(1500)
        th_nome = await page.inner_text("#th-reg-nome")
        print(f"Cabeçalho da tabela regional após mudar para Org: {th_nome}")

        # Testa alternar de volta para Árvore Geográfica
        print("Clicando no botão 'Árvore Geográfica' na Aba Regional...")
        await page.click("#btn-tree-geo")
        await page.wait_for_timeout(1500)
        th_nome_geo = await page.inner_text("#th-reg-nome")
        print(f"Cabeçalho da tabela regional após mudar para Geo: {th_nome_geo}")

        # Screenshot 4: Dupla Hierarquia Regional
        ss4 = os.path.join(SCREENSHOT_DIR, "4_regional_dupla_hierarquia.png")
        await page.screenshot(path=ss4, full_page=False)
        print(f"Screenshot 4 salva: {ss4}")

        # 5. TESTE EM DARK MODE
        print("\n--- 5. TESTE EM DARK MODE ---")
        await page.click("#tab-btn-estoque")
        await page.wait_for_timeout(1000)
        await page.evaluate("toggleTheme()")
        await page.wait_for_timeout(1500)
        ss5 = os.path.join(SCREENSHOT_DIR, "5_estoque_dark_mode.png")
        await page.screenshot(path=ss5, full_page=False)
        print(f"Screenshot 5 salva (Dark Mode): {ss5}")

        # Reverte tema
        await page.evaluate("toggleTheme()")

        await browser.close()
        print("\n========================================================")
        print(f"TESTES CONCLUÍDOS COM SUCESSO! Total de erros de página: {len(errors)}")
        for e in errors:
            print(f"   [ERRO]: {e}")
        print("========================================================")

if __name__ == "__main__":
    asyncio.run(test_stock_and_hierarchy())
