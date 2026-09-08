# -*- coding: utf-8 -*-
import os
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = "file:///" + os.path.join(BASE_DIR, "index.html").replace("\\", "/")

def verify_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. Desktop Test (1920x1080)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(HTML_PATH)
        page.wait_for_timeout(2000)
        
        # Scroll to Matrix Table
        matrix_el = page.locator(".matrix-card").first
        matrix_el.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        page.screenshot(path="verify_matrix_default.png")
        print("[OK] Screenshot 1: Matriz de Detratores Default")
        
        # Click on Duplo Detrator Filter
        page.locator("#btn-filtro-duplo").click()
        page.wait_for_timeout(600)
        rows_duplo = page.locator("#table-body-rows tr").count()
        print(f"[OK] Duplo Detrator Rows: {rows_duplo} (esperado 77)")
        page.screenshot(path="verify_matrix_duplo.png")
        
        # Click on Preço Desalinhado Filter
        page.locator("#btn-filtro-preco").click()
        page.wait_for_timeout(600)
        rows_preco = page.locator("#table-body-rows tr").count()
        print(f"[OK] Preço Desalinhado Rows: {rows_preco} (esperado 11)")
        page.screenshot(path="verify_matrix_preco.png")
        
        # Scroll to the new Precifica Table Section
        prec_section = page.locator("#precifica-table-section")
        prec_section.scroll_into_view_if_needed()
        page.wait_for_timeout(800)
        prec_rows = page.locator("#precifica-tbody tr").count()
        showing_text = page.locator("#precifica-showing-info").inner_text()
        print(f"[OK] Precifica Initial Rows: {prec_rows} | Label: {showing_text}")
        page.screenshot(path="verify_precifica_table_top.png")
        
        # Click on "Spread > +30%"
        page.locator("#btn-prec-criticos").click()
        page.wait_for_timeout(500)
        crit_rows = page.locator("#precifica-tbody tr").count()
        crit_label = page.locator("#precifica-showing-info").inner_text()
        print(f"[OK] Precifica Spread > +30% Rows: {crit_rows} | Label: {crit_label}")
        page.screenshot(path="verify_precifica_criticos.png")
        
        # Click on "🏆 Líder São João"
        page.locator("#btn-prec-baratos").click()
        page.wait_for_timeout(500)
        barato_rows = page.locator("#precifica-tbody tr").count()
        barato_label = page.locator("#precifica-showing-info").inner_text()
        print(f"[OK] Precifica Líder SJ Rows: {barato_rows} | Label: {barato_label}")
        page.screenshot(path="verify_precifica_lider.png")
        
        # Reset to ALL and click on Nissei
        page.locator("#btn-prec-all").click()
        page.wait_for_timeout(300)
        page.locator("#btn-prec-rede-nissei").click()
        page.wait_for_timeout(500)
        nissei_rows = page.locator("#precifica-tbody tr").count()
        nissei_label = page.locator("#precifica-showing-info").inner_text()
        print(f"[OK] Precifica Nissei Rows: {nissei_rows} | Label: {nissei_label}")
        page.screenshot(path="verify_precifica_nissei.png")
        
        # 2. Mobile Test (390x844 iPhone 14)
        mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_page.goto(HTML_PATH)
        mobile_page.wait_for_timeout(2000)
        
        # Scroll to Matrix Table on Mobile
        mobile_matrix = mobile_page.locator(".matrix-card").first
        mobile_matrix.scroll_into_view_if_needed()
        mobile_page.wait_for_timeout(500)
        mobile_page.screenshot(path="verify_mobile_matrix.png")
        print("[OK] Screenshot Mobile Matrix")
        
        # Scroll to Precifica Table on Mobile
        mobile_prec = mobile_page.locator("#precifica-table-section")
        mobile_prec.scroll_into_view_if_needed()
        mobile_page.wait_for_timeout(500)
        mobile_page.screenshot(path="verify_mobile_precifica.png")
        print("[OK] Screenshot Mobile Precifica Table")
        
        browser.close()

if __name__ == "__main__":
    verify_dashboard()
