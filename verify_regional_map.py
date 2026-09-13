import asyncio, sys, os
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots_regional")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def test_regional():
    print("Iniciando verificação do Mapa Interativo e Aba Regional...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 1100})
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"PAGE ERROR: {err}"))
        page.on("console", lambda msg: print(f"   [Browser] {msg.text}") if "error" in msg.type.lower() else None)

        await page.goto("http://127.0.0.1:3000", timeout=30000)
        await page.wait_for_timeout(2000)

        # Clica na aba Regional
        print("Alternando para a aba Regional...")
        await page.click("#tab-btn-regional")
        await page.wait_for_timeout(3000)

        # Verifica se o container está visível
        is_visible = await page.is_visible("#view-regional-container")
        print(f"Aba Regional visível: {is_visible}")

        # Verifica se o mapa Leaflet foi inicializado
        map_classes = await page.evaluate("() => document.getElementById('regional-leaflet-map')?.className")
        print(f"Classes do container do mapa: {map_classes}")
        is_leaflet_ready = "leaflet-container" in (map_classes or "")
        print(f"Leaflet inicializado com sucesso: {is_leaflet_ready}")

        # Screenshot 0: Topo dos KPIs e Cards dos Estados
        print("Capturando visão geral do topo (KPIs e Estados)...")
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        ss0 = os.path.join(SCREENSHOT_DIR, "0_regional_kpis_topo.png")
        await page.screenshot(path=ss0, full_page=False)
        print(f"Screenshot 0 salva: {ss0}")

        # Screenshot 1: Mapa com Lojas Físicas no centro
        print("Rolando e capturando Mapa Interativo no Modo Lojas...")
        await page.evaluate("window.scrollTo(0, 500)")
        await page.wait_for_timeout(1500)
        ss1 = os.path.join(SCREENSHOT_DIR, "1_regional_map_lojas.png")
        await page.screenshot(path=ss1, full_page=False)
        print(f"Screenshot 1 salva: {ss1}")

        # Testa modo Polos Municipais
        print("Testando alternância para Modo Polos Municipais...")
        await page.click("#btn-map-mode-municipios")
        await page.wait_for_timeout(2000)
        ss2 = os.path.join(SCREENSHOT_DIR, "2_regional_map_municipios.png")
        await page.screenshot(path=ss2, full_page=False)
        print(f"Screenshot 2 salva: {ss2}")

        # Rola até a seção inferior (Top Municípios e Tabela)
        print("Rolando para a seção de ranking e tabela...")
        await page.evaluate("window.scrollTo(0, 1150)")
        await page.wait_for_timeout(1500)
        ss3 = os.path.join(SCREENSHOT_DIR, "3_regional_split_table.png")
        await page.screenshot(path=ss3, full_page=False)
        print(f"Screenshot 3 salva: {ss3}")

        # Testa clique em um município do ranking
        print("Testando clique em Passo Fundo no ranking...")
        await page.evaluate("() => zoomToCity('Passo Fundo')")
        await page.wait_for_timeout(2500)
        await page.evaluate("window.scrollTo(0, 500)")
        await page.wait_for_timeout(1000)
        ss4 = os.path.join(SCREENSHOT_DIR, "4_zoom_passo_fundo.png")
        await page.screenshot(path=ss4, full_page=False)
        print(f"Screenshot 4 salva: {ss4}")

        # Testa Tema Escuro
        print("Testando modo Dark...")
        await page.evaluate("() => toggleTheme()")
        await page.wait_for_timeout(2000)
        ss5 = os.path.join(SCREENSHOT_DIR, "5_regional_dark_mode.png")
        await page.screenshot(path=ss5, full_page=False)
        print(f"Screenshot 5 salva: {ss5}")

        # Restaura tema claro
        await page.evaluate("() => toggleTheme()")

        print("\nErros reportados na página:")
        if errors:
            for e in errors:
                print(f"❌ {e}")
        else:
            print("✅ ZERO ERROS! Execução perfeita.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_regional())
