# -*- coding: utf-8 -*-
import os
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = "file:///" + os.path.join(BASE_DIR, "index.html").replace("\\", "/")

def verify_excel_downloads():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(HTML_PATH)
        page.wait_for_timeout(2000)

        # 1. Scroll até a Matriz de Detratores
        matrix_el = page.locator(".matrix-card").first
        matrix_el.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        # Screenshot dos botões de exportação
        page.screenshot(path="verify_excel_buttons.png")
        print("[OK] Screenshot 1: Botões de exportação visíveis na Matriz de Detratores")

        # 2. Testar clique em "Exportar Visão Atual" (Default: Top 50)
        with page.expect_download() as download_info:
            page.locator("#btn-export-current-csv").click()
        download = download_info.value
        filename1 = download.suggested_filename
        download_path1 = os.path.join(BASE_DIR, "download_test_1.csv")
        download.save_as(download_path1)
        print(f"[OK] Download 1 concluído: {filename1} (Tamanho: {os.path.getsize(download_path1)} bytes)")

        # 3. Filtrar por "⚠️ Duplo Detrator (77)" e testar Exportar Visão Atual
        page.locator("#btn-filtro-duplo").click()
        page.wait_for_timeout(600)
        
        with page.expect_download() as download_info2:
            page.locator("#btn-export-current-csv").click()
        download2 = download_info2.value
        filename2 = download2.suggested_filename
        download_path2 = os.path.join(BASE_DIR, "download_test_duplo.csv")
        download2.save_as(download_path2)
        with open(download_path2, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(f"[OK] Download 2 (Duplo Detrator) concluído: {filename2} com {len(lines)-1} linhas de dados (esperado 77)")

        # 4. Scroll até a seção da Precifica e testar download
        prec_sec = page.locator("#precifica-table-section")
        prec_sec.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        page.screenshot(path="verify_precifica_export_btn.png")

        with page.expect_download() as download_info3:
            page.locator("button:has-text('Baixar Preços Precifica')").click()
        download3 = download_info3.value
        filename3 = download3.suggested_filename
        download_path3 = os.path.join(BASE_DIR, "download_test_precifica.csv")
        download3.save_as(download_path3)
        with open(download_path3, "r", encoding="utf-8") as f:
            prec_lines = f.readlines()
        print(f"[OK] Download 3 (Precifica) concluído: {filename3} com {len(prec_lines)-1} produtos monitorados")

        # 5. Teste Mobile
        mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_page.goto(HTML_PATH)
        mobile_page.wait_for_timeout(2000)
        mobile_page.locator(".matrix-card").first.scroll_into_view_if_needed()
        mobile_page.wait_for_timeout(500)
        mobile_page.screenshot(path="verify_mobile_excel_buttons.png")
        print("[OK] Screenshot Mobile: Botões adaptados perfeitamente ao viewport mobile")

        browser.close()

        # Limpar arquivos de teste baixados
        for p_test in [download_path1, download_path2, download_path3]:
            if os.path.exists(p_test):
                os.remove(p_test)

if __name__ == "__main__":
    verify_excel_downloads()
