# -*- coding: utf-8 -*-
import json
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
JSON_PATH = os.path.join(DATA_DIR, "intraday_monitor.json")
EXCEL_PATH = os.path.join(DATA_DIR, "Top_50_Detratores_Canais_Digitais.xlsx")

def generate_excel_top50():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    corte_str = meta.get("corte_timestamp", "08/09/2026 09:54:12")
    corte_hora = meta.get("corte_hora", "09:54")
    
    skus_all = data.get("detratores_alavancadores", {}).get("skus", {}).get("all", [])
    detratores = [s for s in skus_all if (s.get("gap_d7_rs") or 0) < 0]
    detratores_sorted = sorted(detratores, key=lambda x: (x.get("gap_d7_rs") or 0))[:50]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Top 50 Detratores"
    ws.views.sheetView[0].showGridLines = True

    # Paleta de Cores
    header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid") # Navy Blue
    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    
    title_font = Font(name="Segoe UI", size=14, bold=True, color="1A365D")
    sub_font = Font(name="Segoe UI", size=9.5, italic=True, color="4A5568")
    
    regular_font = Font(name="Segoe UI", size=9.5)
    bold_font = Font(name="Segoe UI", size=9.5, bold=True)
    red_font = Font(name="Segoe UI", size=9.5, bold=True, color="C53030")
    green_font = Font(name="Segoe UI", size=9.5, bold=True, color="22543D")
    blue_mono_font = Font(name="Consolas", size=10, bold=True, color="2B6CB0")
    
    zebra_fill = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    total_fill = PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )
    total_border = Border(
        left=Side(style='thin', color='CBD5E0'),
        right=Side(style='thin', color='CBD5E0'),
        top=Side(style='thin', color='4A5568'),
        bottom=Side(style='double', color='1A365D')
    )

    # 1. Título e Metadados
    ws["A1"] = "FARMÁCIAS SÃO JOÃO — RELATÓRIO EXECUTIVO: TOP 50 DETRATORES DE VENDAS"
    ws["A1"].font = title_font
    
    ws["A2"] = f"Canais Digitais (App, Site, Marketplace) • Horário de Corte: {corte_str} ({corte_hora}) • Tríade Estoque x Preço x Demanda"
    ws["A2"].font = sub_font

    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[3].height = 10

    # 2. Cabeçalho das Colunas
    headers = [
        "Ranking", "Código SKU", "Produto / Descrição", "Hoje Realizado",
        "Esperado D-7", "GAP vs D-7 (R$)", "GAP vs D-7 (%)", "Estoque Rede",
        "Densidade (un/lj)", "Causa-Raiz Diagnóstico", "Preço São João",
        "Menor Concorrente", "Preço Concorrência", "Spread (%)", "Status Concorrência", "Classificação"
    ]

    header_row = 4
    ws.row_dimensions[header_row].height = 26
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # 3. Preenchimento dos Dados
    start_row = 5
    for idx, item in enumerate(detratores_sorted, 1):
        r = start_row + idx - 1
        ws.row_dimensions[r].height = 20
        fill = zebra_fill if idx % 2 == 0 else white_fill

        saldo = item.get("saldo") or 0
        un_loja = item.get("un_por_loja") if item.get("un_por_loja") is not None else (saldo / 1147)
        gap_rs = item.get("gap_d7_rs") or 0.0
        gap_pct = (item.get("gap_d7_pct") or 0.0) / 100.0

        causa_raw = item.get("causa_tipo") or ""
        causa_desc = "Ruptura Logística"
        if causa_raw == "DUPLO_DETRATOR":
            causa_desc = "⚠️ Duplo Detrator"
        elif causa_raw == "PRECO_DESALINHADO":
            causa_desc = "🏷️ Preço Desalinhado"
        elif causa_raw in ("DEMANDA_COMERCIAL", "ABASTECIDO"):
            causa_desc = "📉 Demanda Normal"
        elif causa_raw in ("RUPTURA_LOGISTICA", "RUPTURA_ZERO", "RUPTURA_CAPILAR", "ESTOQUE_RESTRITO"):
            causa_desc = "🚨 Ruptura Logística"

        preco_sj = item.get("nosso_preco")
        rede_conc = (item.get("menor_concorrente_rede") or "").upper().replace("FARMACIAS", "").replace("PRECO", "PREÇO ")
        preco_conc = item.get("menor_concorrente_preco")
        spread_pct = (item.get("spread_pct") / 100.0) if item.get("spread_pct") is not None else None

        status_conc = "Não Monitorado"
        if item.get("precifica_monitorado"):
            if item.get("preco_status") == "MAIS_CARO":
                status_conc = "São João Mais Cara"
            elif item.get("preco_status") == "MAIS_BARATO":
                status_conc = "Líder de Preço"
            elif item.get("preco_status") == "EMPATADO":
                status_conc = "Preço Alinhado"

        row_data = [
            (idx, Alignment(horizontal="center"), bold_font, None),
            (str(item.get("sku_id", "")), Alignment(horizontal="center"), blue_mono_font, "@"),
            (item.get("nome", ""), Alignment(horizontal="left"), bold_font, None),
            (item.get("hoje", 0.0), Alignment(horizontal="right"), regular_font, '"R$" #,##0.00'),
            (item.get("d7_exp_corte", 0.0), Alignment(horizontal="right"), regular_font, '"R$" #,##0.00'),
            (gap_rs, Alignment(horizontal="right"), red_font, '"R$" #,##0.00;[Red]-"R$" #,##0.00'),
            (gap_pct, Alignment(horizontal="right"), red_font, '0.0%'),
            (saldo, Alignment(horizontal="right"), regular_font, '#,##0'),
            (un_loja, Alignment(horizontal="right"), bold_font if un_loja < 1.5 else regular_font, '0.00'),
            (causa_desc, Alignment(horizontal="center"), bold_font, None),
            (preco_sj if preco_sj is not None else "", Alignment(horizontal="right"), regular_font, '"R$" #,##0.00' if preco_sj else None),
            (rede_conc, Alignment(horizontal="center"), regular_font, None),
            (preco_conc if preco_conc is not None else "", Alignment(horizontal="right"), regular_font, '"R$" #,##0.00' if preco_conc else None),
            (spread_pct if spread_pct is not None else "", Alignment(horizontal="right"), red_font if (spread_pct or 0) > 0 else green_font, '+0.0%;-0.0%;"0.0%"' if spread_pct is not None else None),
            (status_conc, Alignment(horizontal="center"), regular_font, None),
            (item.get("status", ""), Alignment(horizontal="center"), regular_font, None)
        ]

        for col_i, (val, align, font_style, num_fmt) in enumerate(row_data, 1):
            c = ws.cell(row=r, column=col_i, value=val)
            c.alignment = align
            c.font = font_style
            c.fill = fill
            c.border = thin_border
            if num_fmt:
                c.number_format = num_fmt

    # 4. Linha de Totalização
    tot_r = start_row + len(detratores_sorted)
    ws.row_dimensions[tot_r].height = 24
    
    c_tot_lbl = ws.cell(row=tot_r, column=1, value="TOTAL TOP 50")
    c_tot_lbl.alignment = Alignment(horizontal="center")
    c_tot_lbl.font = Font(name="Segoe UI", size=10, bold=True, color="1A365D")
    c_tot_lbl.fill = total_fill
    c_tot_lbl.border = total_border

    # Mescla A até C no Total
    ws.merge_cells(start_row=tot_r, start_column=1, end_row=tot_r, end_column=3)
    for c_i in range(1, 4):
        ws.cell(row=tot_r, column=c_i).fill = total_fill
        ws.cell(row=tot_r, column=c_i).border = total_border

    # Fórmulas de Soma
    # D: Hoje
    c_d = ws.cell(row=tot_r, column=4, value=f"=SUM(D{start_row}:D{tot_r-1})")
    c_d.number_format = '"R$" #,##0.00'
    # E: Esperado D-7
    c_e = ws.cell(row=tot_r, column=5, value=f"=SUM(E{start_row}:E{tot_r-1})")
    c_e.number_format = '"R$" #,##0.00'
    # F: GAP vs D-7 (R$)
    c_f = ws.cell(row=tot_r, column=6, value=f"=SUM(F{start_row}:F{tot_r-1})")
    c_f.number_format = '"R$" #,##0.00;[Red]-"R$" #,##0.00'
    # G: GAP (%)
    c_g = ws.cell(row=tot_r, column=7, value=f"=(D{tot_r}-E{tot_r})/E{tot_r}")
    c_g.number_format = '0.0%'
    # H: Estoque Rede
    c_h = ws.cell(row=tot_r, column=8, value=f"=SUM(H{start_row}:H{tot_r-1})")
    c_h.number_format = '#,##0'

    for c_i in range(4, 17):
        cell = ws.cell(row=tot_r, column=c_i)
        cell.fill = total_fill
        cell.border = total_border
        cell.font = Font(name="Segoe UI", size=10, bold=True)
        if c_i not in (4, 5, 6, 7, 8):
            cell.value = ""

    c_f.font = Font(name="Segoe UI", size=10, bold=True, color="C53030")
    c_g.font = Font(name="Segoe UI", size=10, bold=True, color="C53030")

    # 5. Ajuste automático das larguras das colunas
    col_widths = {
        1: 10,  # Ranking
        2: 15,  # Código SKU
        3: 42,  # Produto
        4: 17,  # Hoje
        5: 17,  # Esperado D-7
        6: 18,  # GAP R$
        7: 15,  # GAP %
        8: 15,  # Estoque
        9: 17,  # Densidade
        10: 24, # Causa-Raiz
        11: 16, # Preço SJ
        12: 18, # Concorrente
        13: 18, # Preço Conc
        14: 14, # Spread %
        15: 22, # Status Conc
        16: 20  # Classificação
    }

    for col_i, w in col_widths.items():
        ws.column_dimensions[get_column_letter(col_i)].width = w

    wb.save(EXCEL_PATH)
    print(f"[SUCESSO] Planilha Excel gerada: {EXCEL_PATH} ({len(detratores_sorted)} SKUs formatados)")

if __name__ == "__main__":
    generate_excel_top50()
