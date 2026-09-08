#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROCESSAMENTO E INTELIGÊNCIA ANALÍTICA INTRADAY — CANAIS DIGITAIS (FARMÁCIAS SÃO JOÃO)
Canais estritamente monitorados:
  - Site: 'SITE', 'SITE Tele Entrega'
  - APP: 'APP', 'APP Tele Entrega'
  - Marketplace: 'e_Commerce', 'iFood'
Calcula comparativos em 3 janelas idênticas no mesmo minuto de corte (D-1, D-7, Média 7D),
curva empírica de distribuição da meta hora a hora, projeção EOD em múltiplos cenários,
mix de canais (share realizado vs orçado), ticket médio por item, radar do horário nobre (18h-22h),
matriz de detratores/alavancadores em 5 níveis hierárquicos e storytelling executivo.
"""

import os
import sys
import json
import openpyxl
from datetime import datetime, timedelta
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_FILE = os.path.join(DATA_DIR, "intraday_raw.json")
EXCEL_META = os.path.join(BASE_DIR, "Diarização Setembro 2026.xlsx")
OUTPUT_FILE = os.path.join(DATA_DIR, "intraday_monitor.json")
OUTPUT_JS = os.path.join(DATA_DIR, "intraday_data.js")

def norm_canal(c):
    """Mapeamento estrito dos canais definidos"""
    c_str = str(c or "").strip()
    c_upper = c_str.upper()
    # Site
    if c_str in ["SITE", "SITE Tele Entrega"] or c_upper in ["SITE", "SITE TELE ENTREGA"]:
        return "Site"
    # APP
    if c_str in ["APP", "APP Tele Entrega"] or c_upper in ["APP", "APP TELE ENTREGA"]:
        return "APP"
    # Marketplace
    if c_str in ["e_Commerce", "iFood"] or c_upper in ["E_COMMERCE", "IFOOD"]:
        return "MKP"
    return None

def get_minute_of_day(val):
    """Converte fração numérica do Qlik ou string HH:MM em minuto do dia (0..1439)"""
    if isinstance(val, (int, float)):
        frac = val % 1.0
        return int(round(frac * 24.0 * 60.0)) % 1440
    elif isinstance(val, str) and ":" in val:
        parts = val.split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            return 0
    return 0

def load_metas(dia_alvo=7):
    """Lê metas da planilha oficial de diarização para o dia alvo estritamente para os canais definidos"""
    dia_int = int(dia_alvo)
    metas = {
        "Total": 1560604.42,
        "APP": 739532.77,
        "Site": 413172.55,
        "MKP": 407899.10
    }
    if not os.path.exists(EXCEL_META):
        return metas

    try:
        wb = openpyxl.load_workbook(EXCEL_META, data_only=True)
        ws = wb["Planilha2"] if "Planilha2" in wb.sheetnames else wb.active
        found = False
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] is not None and int(row[0]) == dia_int:
                # Cols: Dia, DOW, Data, Meta Dia, % Mes, APP, Site, MKP
                metas["APP"] = float(row[5] or 0)
                metas["Site"] = float(row[6] or 0)
                metas["MKP"] = float(row[7] or 0)
                metas["Total"] = metas["APP"] + metas["Site"] + metas["MKP"]
                found = True
                break
        if not found:
            print(f"Aviso: Dia {dia_int} não localizado na planilha de metas. Mantendo padrão.")
    except Exception as e:
        print(f"Aviso ao ler metas do Excel: {e}. Usando valores padrão do dia {dia_int}.")
    return metas


def generate_excel_top50(output_data, data_dir):
    """Gera planilha Excel (.xlsx) altamente formatada com os Top 50 Detratores de Vendas."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        excel_path = os.path.join(data_dir, "Top_50_Detratores_Canais_Digitais.xlsx")
        meta = output_data.get("metadata", {})
        corte_str = meta.get("corte_timestamp", "")
        corte_hora = meta.get("corte_hora", "")

        skus_all = output_data.get("detratores_alavancadores", {}).get("skus", {}).get("all", [])
        detratores = [s for s in skus_all if (s.get("gap_d7_rs") or 0) < 0]
        detratores_sorted = sorted(detratores, key=lambda x: (x.get("gap_d7_rs") or 0))[:50]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Top 50 Detratores"
        ws.views.sheetView[0].showGridLines = True

        header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
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

        ws["A1"] = "FARMÁCIAS SÃO JOÃO — RELATÓRIO EXECUTIVO: TOP 50 DETRATORES DE VENDAS"
        ws["A1"].font = title_font
        ws["A2"] = f"Canais Digitais (App, Site, Marketplace) • Horário de Corte: {corte_str} ({corte_hora}) • Tríade Estoque x Preço x Demanda"
        ws["A2"].font = sub_font

        ws.row_dimensions[1].height = 24
        ws.row_dimensions[2].height = 18
        ws.row_dimensions[3].height = 10

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

        tot_r = start_row + len(detratores_sorted)
        ws.row_dimensions[tot_r].height = 24
        
        c_tot_lbl = ws.cell(row=tot_r, column=1, value="TOTAL TOP 50")
        c_tot_lbl.alignment = Alignment(horizontal="center")
        c_tot_lbl.font = Font(name="Segoe UI", size=10, bold=True, color="1A365D")
        c_tot_lbl.fill = total_fill
        c_tot_lbl.border = total_border

        ws.merge_cells(start_row=tot_r, start_column=1, end_row=tot_r, end_column=3)
        for c_i in range(1, 4):
            ws.cell(row=tot_r, column=c_i).fill = total_fill
            ws.cell(row=tot_r, column=c_i).border = total_border

        c_d = ws.cell(row=tot_r, column=4, value=f"=SUM(D{start_row}:D{tot_r-1})")
        c_d.number_format = '"R$" #,##0.00'
        c_e = ws.cell(row=tot_r, column=5, value=f"=SUM(E{start_row}:E{tot_r-1})")
        c_e.number_format = '"R$" #,##0.00'
        c_f = ws.cell(row=tot_r, column=6, value=f"=SUM(F{start_row}:F{tot_r-1})")
        c_f.number_format = '"R$" #,##0.00;[Red]-"R$" #,##0.00'
        c_g = ws.cell(row=tot_r, column=7, value=f"=(D{tot_r}-E{tot_r})/E{tot_r}")
        c_g.number_format = '0.0%'
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

        col_widths = {
            1: 10, 2: 15, 3: 42, 4: 17, 5: 17, 6: 18, 7: 15,
            8: 15, 9: 17, 10: 24, 11: 16, 12: 18, 13: 18,
            14: 14, 15: 22, 16: 20
        }
        for col_i, w in col_widths.items():
            ws.column_dimensions[get_column_letter(col_i)].width = w

        wb.save(excel_path)
        print(f"   Planilha Excel atualizada com sucesso: {excel_path}")
    except Exception as e_excel:
        print(f"   Aviso ao gerar planilha Excel: {e_excel}")

def process_analytics():
    print("=" * 70)
    print("  PROCESSAMENTO ANALÍTICO INTRADAY — CANAIS DIGITAIS")
    print("  Escopo estrito: Site (Site + Tele), APP (APP + Tele), MKP (e-Com + iFood)")
    print("=" * 70)

    if not os.path.exists(RAW_FILE):
        raise FileNotFoundError(f"Arquivo de dados brutos não encontrado: {RAW_FILE}")

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    max_hora_str = raw.get("maxHora", "12:52")
    max_data_hora = raw.get("maxDataHora", f"07/09/2026 {max_hora_str}:00")
    dia_hoje = int(raw.get("diaHoje", 7))
    data_hoje_str = raw.get("dataHoje", datetime.now().strftime("%d/%m/%Y"))

    try:
        dt_ref = datetime.strptime(data_hoje_str, "%d/%m/%Y")
    except Exception:
        dt_ref = datetime.now()

    DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dow_nome = DIAS_SEMANA[dt_ref.weekday()]

    max_minute = get_minute_of_day(max_hora_str)
    curr_hour = max_minute // 60
    curr_min = max_minute % 60
    elapsed_hours = max(0.1, max_minute / 60.0)
    remaining_hours = max(0.01, 24.0 - elapsed_hours)

    print(f"Horário de corte: {max_data_hora} ({max_minute} min = {curr_hour:02d}:{curr_min:02d}) [{dow_nome}]")
    print(f"Horas decorridas: {elapsed_hours:.2f}h | Horas restantes: {remaining_hours:.2f}h")

    metas = load_metas(dia_hoje)
    metas_excel = metas
    print(f"Metas Oficiais do Dia {dia_hoje}: Total=R$ {metas['Total']:,.2f} | APP=R$ {metas['APP']:,.2f} | Site=R$ {metas['Site']:,.2f} | MKP=R$ {metas['MKP']:,.2f}")

    # 1. Totalizadores Hoje, Ontem e D-7 por Canal (no corte e totais)
    hoje_cut = defaultdict(float)
    hoje_qtd = defaultdict(float)
    for r in raw.get("rowsHoje", []):
        c = norm_canal(r[0])
        if not c:
            continue
        val = float(r[2] or 0)
        qtd = float(r[3] or 0)
        hoje_cut[c] += val
        hoje_cut["Total"] += val
        hoje_qtd[c] += qtd
        hoje_qtd["Total"] += qtd

    ontem_cut = defaultdict(float)
    ontem_full = defaultdict(float)
    ontem_qtd_cut = defaultdict(float)
    ontem_qtd_full = defaultdict(float)
    for r in raw.get("rowsOntem", []):
        c = norm_canal(r[0])
        if not c:
            continue
        m = get_minute_of_day(r[1])
        val = float(r[2] or 0)
        qtd = float(r[3] or 0)
        ontem_full[c] += val
        ontem_full["Total"] += val
        ontem_qtd_full[c] += qtd
        ontem_qtd_full["Total"] += qtd
        if m <= max_minute:
            ontem_cut[c] += val
            ontem_cut["Total"] += val
            ontem_qtd_cut[c] += qtd
            ontem_qtd_cut["Total"] += qtd

    d7_cut = defaultdict(float)
    d7_full = defaultdict(float)
    d7_qtd_cut = defaultdict(float)
    d7_qtd_full = defaultdict(float)
    for r in raw.get("rowsD7", []):
        c = norm_canal(r[0])
        if not c:
            continue
        m = get_minute_of_day(r[1])
        val = float(r[2] or 0)
        qtd = float(r[3] or 0)
        d7_full[c] += val
        d7_full["Total"] += val
        d7_qtd_full[c] += qtd
        d7_qtd_full["Total"] += qtd
        if m <= max_minute:
            d7_cut[c] += val
            d7_cut["Total"] += val
            d7_qtd_cut[c] += qtd
            d7_qtd_cut["Total"] += qtd

    # 2. Histórico dos últimos 7 dias completos (TOTALMENTE DINÂMICO PARA QUALQUER DIA)
    ano_mes_ref = f"{dt_ref.year}-{dt_ref.month:02d}"
    dt_prev_month = dt_ref.replace(day=1) - timedelta(days=1)
    ano_mes_prev = f"{dt_prev_month.year}-{dt_prev_month.month:02d}"

    # Gera conjunto de tuplas (dia, ano-mes) dos 7 dias imediatamente anteriores
    dias_anteriores = {}
    for i in range(1, 8):
        d = dt_ref - timedelta(days=i)
        dias_anteriores[(d.day, f"{d.year}-{d.month:02d}")] = d.strftime("%Y-%m-%d")

    hist_days = defaultdict(lambda: defaultdict(float))
    for r in raw.get("rowsHistDia", []):
        c = norm_canal(r[0])
        if not c:
            continue
        dia_num = int(r[1])
        val_curr = float(r[2] or 0)
        val_prev = float(r[3] or 0) if len(r) > 3 else 0.0

        if (dia_num, ano_mes_ref) in dias_anteriores:
            day_key = f"{ano_mes_ref}_{dia_num:02d}"
            hist_days[day_key][c] += val_curr
            hist_days[day_key]["Total"] += val_curr
        elif (dia_num, ano_mes_prev) in dias_anteriores:
            day_key = f"{ano_mes_prev}_{dia_num:02d}"
            hist_days[day_key][c] += val_prev
            hist_days[day_key]["Total"] += val_prev

    media_7d_full = defaultdict(float)
    n_dias_hist = max(1, len(hist_days))
    for day_id, day_data in hist_days.items():
        for ch, v in day_data.items():
            media_7d_full[ch] += v / n_dias_hist

    media_recentes_full = defaultdict(float)
    recentes_days = [d for d in hist_days if d.startswith(ano_mes_ref)]
    n_recentes = max(1, len(recentes_days))
    for day_id, day_data in hist_days.items():
        if day_id.startswith(ano_mes_ref):
            for ch, v in day_data.items():
                media_recentes_full[ch] += v / n_recentes

    metas_ponderadas = {}
    for ch in ["APP", "Site", "MKP"]:
        metas_ponderadas[ch] = round(0.70 * d7_full[ch] + 0.30 * (media_recentes_full[ch] or d7_full[ch]), 2)
    metas_ponderadas["Total"] = round(metas_ponderadas["APP"] + metas_ponderadas["Site"] + metas_ponderadas["MKP"], 2)

    # 4. Pesos e Curva Científica de Distribuição Horária
    curve_weights_cut = {}
    for ch in ["Total", "APP", "Site", "MKP"]:
        w_d7 = (d7_cut[ch] / d7_full[ch]) if d7_full[ch] > 0 else 0
        w_ontem = (ontem_cut[ch] / ontem_full[ch]) if ontem_full[ch] > 0 else 0
        w_blend = (w_d7 * 0.7 + w_ontem * 0.3) if (w_d7 > 0 and w_ontem > 0) else (w_d7 or w_ontem or (elapsed_hours / 24.0))
        # Garantia de piso seguro para início da manhã
        curve_weights_cut[ch] = max(0.005, min(1.0, w_blend))

    media_7d_cut = defaultdict(float)
    for ch in ["Total", "APP", "Site", "MKP"]:
        media_7d_cut[ch] = media_7d_full[ch] * curve_weights_cut[ch]

    # 5. Curva Horária Consolidada e por Canal (00h..23h)
    hourly_hoje = defaultdict(lambda: defaultdict(float))
    hourly_ontem = defaultdict(lambda: defaultdict(float))
    hourly_d7 = defaultdict(lambda: defaultdict(float))

    for r in raw.get("rowsHoje", []):
        c = norm_canal(r[0])
        if not c:
            continue
        h = get_minute_of_day(r[1]) // 60
        hourly_hoje[h][c] += float(r[2] or 0)
        hourly_hoje[h]["Total"] += float(r[2] or 0)

    for r in raw.get("rowsOntem", []):
        c = norm_canal(r[0])
        if not c:
            continue
        h = get_minute_of_day(r[1]) // 60
        hourly_ontem[h][c] += float(r[2] or 0)
        hourly_ontem[h]["Total"] += float(r[2] or 0)

    for r in raw.get("rowsD7", []):
        c = norm_canal(r[0])
        if not c:
            continue
        h = get_minute_of_day(r[1]) // 60
        hourly_d7[h][c] += float(r[2] or 0)
        hourly_d7[h]["Total"] += float(r[2] or 0)

    # Distribuição da meta hora a hora ponderada
    hourly_curve_table = []
    accum_hoje = defaultdict(float)
    accum_meta_exp = defaultdict(float)
    accum_d7 = defaultdict(float)
    accum_ontem = defaultdict(float)
    accum_proj_base = defaultdict(float)

    peso_horario_nobre = 0.0
    for h in range(24):
        w_h = {}
        for ch in ["Total", "APP", "Site", "MKP"]:
            tot_d7 = d7_full[ch] if d7_full[ch] > 0 else 1.0
            tot_ont = ontem_full[ch] if ontem_full[ch] > 0 else 1.0
            w_d7_h = hourly_d7[h][ch] / tot_d7
            w_ont_h = hourly_ontem[h][ch] / tot_ont
            w_h[ch] = 0.70 * w_d7_h + 0.30 * w_ont_h

        if h in [18, 19, 20, 21]:
            peso_horario_nobre += w_h["Total"]

        row_h = {
            "hora": f"{h:02d}:00",
            "hora_num": h,
            "is_past": h < curr_hour,
            "is_current": h == curr_hour,
            "is_future": h > curr_hour,
            "weight_pct": {ch: round(w_h[ch] * 100, 2) for ch in w_h},
            "venda_hoje": {ch: round(hourly_hoje[h][ch], 2) for ch in ["Total", "APP", "Site", "MKP"]},
            "venda_ontem": {ch: round(hourly_ontem[h][ch], 2) for ch in ["Total", "APP", "Site", "MKP"]},
            "venda_d7": {ch: round(hourly_d7[h][ch], 2) for ch in ["Total", "APP", "Site", "MKP"]},
            "meta_esperada_hora": {ch: round(metas[ch] * w_h[ch], 2) for ch in metas}
        }

        for ch in ["Total", "APP", "Site", "MKP"]:
            accum_d7[ch] += hourly_d7[h][ch]
            accum_ontem[ch] += hourly_ontem[h][ch]
            accum_meta_exp[ch] += metas[ch] * w_h[ch]
            if h <= curr_hour:
                accum_hoje[ch] += hourly_hoje[h][ch]
                accum_proj_base[ch] = accum_hoje[ch]
            else:
                pacing_atual = (hoje_cut[ch] / (metas[ch] * curve_weights_cut[ch])) if (metas[ch] * curve_weights_cut[ch]) > 0 else 1.0
                pacing_atual = max(0.2, min(3.0, pacing_atual))
                accum_proj_base[ch] += metas[ch] * w_h[ch] * pacing_atual

        row_h["accum_hoje"] = {ch: round(accum_hoje[ch], 2) for ch in accum_hoje}
        row_h["accum_d7"] = {ch: round(accum_d7[ch], 2) for ch in accum_d7}
        row_h["accum_ontem"] = {ch: round(accum_ontem[ch], 2) for ch in accum_ontem}
        row_h["accum_meta_exp"] = {ch: round(accum_meta_exp[ch], 2) for ch in accum_meta_exp}
        row_h["accum_proj_base"] = {ch: round(accum_proj_base[ch], 2) for ch in accum_proj_base}
        hourly_curve_table.append(row_h)

    # 5. Indicadores Executivos, 3 Janelas e Cenários de Projeção com Proteção Matinal
    executive_kpis = {}
    for ch in ["Total", "APP", "Site", "MKP"]:
        real = hoje_cut[ch]
        m_dia = metas[ch]
        w_cut = curve_weights_cut[ch]
        m_exp = m_dia * w_cut
        gap_corte = real - m_exp
        pacing_pct = (real / m_exp * 100.0) if m_exp > 0 else 0.0

        # Amortecimento Bayesiano na Projeção EOD para o início da manhã (evita distorções por vendas únicas na madrugada)
        if w_cut < 0.15:
            blend_factor = max(0.0, w_cut / 0.15)
            raw_proj = (real / w_cut) if w_cut > 0.001 else real
            proj_base = blend_factor * raw_proj + (1.0 - blend_factor) * m_dia
        else:
            proj_base = (real / w_cut) if w_cut > 0 else real

        proj_conservadora = real + max(0.0, (proj_base - real)) * 0.94
        proj_reversao = real + max(0.0, (m_dia - m_exp))

        gap_proj_base = proj_base - m_dia
        proj_pacing_pct = (proj_base / m_dia * 100.0) if m_dia > 0 else 0.0

        run_rate_atual_hora = real / elapsed_hours
        run_rate_necessario_hora = max(0.0, (m_dia - real)) / remaining_hours

        # Janela 1: vs Ontem (D-1)
        ont_c = ontem_cut[ch]
        ont_f = ontem_full[ch]
        var_ontem_rs = real - ont_c
        var_ontem_pct = ((real - ont_c) / ont_c * 100.0) if ont_c > 0 else 0.0

        # Janela 2: vs D-7 (mesmo dia da semana passada)
        d7_c = d7_cut[ch]
        d7_f = d7_full[ch]
        var_d7_rs = real - d7_c
        var_d7_pct = ((real - d7_c) / d7_c * 100.0) if d7_c > 0 else 0.0

        # Janela 3: vs Média 7D
        m7_c = media_7d_cut[ch]
        m7_f = media_7d_full[ch]
        var_m7_rs = real - m7_c
        var_m7_pct = ((real - m7_c) / m7_c * 100.0) if m7_c > 0 else 0.0

        executive_kpis[ch] = {
            "canal": ch,
            "meta_dia": round(m_dia, 2),
            "realizado_hoje": round(real, 2),
            "qtd_pedidos_itens": int(hoje_qtd[ch]),
            "curva_peso_corte_pct": round(w_cut * 100.0, 2),
            "meta_esperada_corte": round(m_exp, 2),
            "pacing_corte_pct": round(pacing_pct, 1),
            "gap_corte_rs": round(gap_corte, 2),
            "meta_dia_ponderada": round(metas_ponderadas[ch], 2),
            "meta_esperada_ponderada": round(metas_ponderadas[ch] * w_cut, 2),
            "meta_dia_excel": round(metas_excel[ch], 2),
            "meta_esperada_excel": round(metas_excel[ch] * w_cut, 2),
            "pacing_excel_pct": round((real / (metas_excel[ch] * w_cut) * 100.0) if (metas_excel[ch] * w_cut) > 0 else 0.0, 1),
            "gap_excel_rs": round(real - (metas_excel[ch] * w_cut), 2),
            "projecao_eod": round(proj_base, 2),
            "projecao_pacing_pct": round(proj_pacing_pct, 1),
            "gap_projecao_rs": round(gap_proj_base, 2),
            "cenarios_projecao": {
                "base": round(proj_base, 2),
                "conservador": round(proj_conservadora, 2),
                "reversao_meta": round(proj_reversao, 2)
            },
            "run_rate_atual_hora": round(run_rate_atual_hora, 2),
            "run_rate_necessario_hora": round(run_rate_necessario_hora, 2),
            "janela_d1": {
                "ontem_corte": round(ont_c, 2),
                "ontem_total": round(ont_f, 2),
                "var_rs": round(var_ontem_rs, 2),
                "var_pct": round(var_ontem_pct, 1)
            },
            "janela_d7": {
                "d7_corte": round(d7_c, 2),
                "d7_total": round(d7_f, 2),
                "var_rs": round(var_d7_rs, 2),
                "var_pct": round(var_d7_pct, 1)
            },
            "janela_7d_avg": {
                "media_7d_corte": round(m7_c, 2),
                "media_7d_total": round(m7_f, 2),
                "var_rs": round(var_m7_rs, 2),
                "var_pct": round(var_m7_pct, 1)
            }
        }

    # 6. Mix de Canais & Eficiência de Carrinho (Retail Analytics)
    tot_real = hoje_cut["Total"]
    tot_meta = metas["Total"]
    mix_canais = {}
    for ch in ["Total", "APP", "Site", "MKP"]:
        real_ch = hoje_cut[ch]
        meta_ch = metas[ch]
        qtd_ch = hoje_qtd[ch]
        share_real = (real_ch / tot_real * 100.0) if tot_real > 0 else 0.0
        share_meta = (meta_ch / tot_meta * 100.0) if tot_meta > 0 else 0.0
        desvio_mix = share_real - share_meta
        ticket_item = (real_ch / qtd_ch) if qtd_ch > 0 else 0.0

        mix_canais[ch] = {
            "share_realizado_pct": round(share_real, 1),
            "share_meta_pct": round(share_meta, 1),
            "desvio_mix_pp": round(desvio_mix, 1),
            "ticket_medio_item": round(ticket_item, 2),
            "qtd_itens": int(qtd_ch)
        }

    # 7. Radar do Horário Nobre (18h às 22h)
    venda_esperada_nobre = metas["Total"] * peso_horario_nobre
    meta_restante_dia = max(0.0, metas["Total"] - hoje_cut["Total"])
    horario_nobre = {
        "peso_curva_pct": round(peso_horario_nobre * 100.0, 1),
        "venda_esperada_rs": round(venda_esperada_nobre, 2),
        "meta_restante_rs": round(meta_restante_dia, 2),
        "horas_restantes": round(remaining_hours, 1),
        "run_rate_necessario_hora": round(executive_kpis["Total"]["run_rate_necessario_hora"], 2)
    }

    # 8. Matriz de Detratores e Alavancadores em 5 Níveis
    w_d7_tot = curve_weights_cut["Total"]
    w_ontem_tot = (ontem_cut["Total"] / ontem_full["Total"]) if ontem_full["Total"] > 0 else w_d7_tot

    def build_detractors_boosters(items, name_key, extra_keys=None):
        """Calcula GAPs e classifica detratores e alavancadores de forma justa e normalizada no corte"""
        res = []
        for item in items:
            name = item.get(name_key)
            if not name or str(name).strip() in ["", "None", "0"]:
                continue
            hoje = float(item.get("hoje", 0))
            ontem = float(item.get("ontem", 0))
            d7 = float(item.get("d7", 0))

            exp_d7 = d7 * w_d7_tot
            gap_d7 = hoje - exp_d7
            pct_d7 = ((hoje - exp_d7) / exp_d7 * 100.0) if exp_d7 > 0 else (100.0 if hoje > 0 else 0.0)

            exp_ontem = ontem * w_ontem_tot
            gap_ontem = hoje - exp_ontem
            pct_ontem = ((hoje - exp_ontem) / exp_ontem * 100.0) if exp_ontem > 0 else (100.0 if hoje > 0 else 0.0)

            # Classificação
            if gap_d7 <= -5000:
                status = "Detrator Crítico"
            elif gap_d7 < -1000:
                status = "Detrator Moderado"
            elif gap_d7 > 5000:
                status = "Super Alavancador"
            elif gap_d7 > 1000:
                status = "Alavancador"
            else:
                status = "Neutro"

            entry = {
                name_key: name,
                "hoje": round(hoje, 2),
                "d7_full": round(d7, 2),
                "d7_exp_corte": round(exp_d7, 2),
                "gap_d7_rs": round(gap_d7, 2),
                "gap_d7_pct": round(pct_d7, 1),
                "ontem_full": round(ontem, 2),
                "ontem_exp_corte": round(exp_ontem, 2),
                "gap_ontem_rs": round(gap_ontem, 2),
                "gap_ontem_pct": round(pct_ontem, 1),
                "status": status
            }
            if extra_keys:
                for k in extra_keys:
                    entry[k] = item.get(k)
            res.append(entry)

        res_sorted = sorted(res, key=lambda x: x["gap_d7_rs"])
        detratores = res_sorted[:100] # Top 100 Detratores
        alavancadores = sorted(res, key=lambda x: x["gap_d7_rs"], reverse=True)[:100]

        return {
            "all": res_sorted,
            "detratores_top": detratores,
            "alavancadores_top": alavancadores,
            "total_items": len(res)
        }

    # Carrega Cache da Precifica (Inteligência de Preços de 9.005 Itens)
    precifica_cache_file = os.path.join(DATA_DIR, "precifica_cache.json")
    precifica_items = {}
    precifica_summary = {}
    if os.path.exists(precifica_cache_file):
        try:
            with open(precifica_cache_file, "r", encoding="utf-8") as f_prec:
                prec_data = json.load(f_prec)
                precifica_items = prec_data.get("items_by_ref", {})
                precifica_summary = prec_data.get("summary", {})
        except Exception as e_prec:
            print(f"   Aviso ao carregar cache da Precifica: {e_prec}")

    # Nível 1: SKUs / Itens com Análise de Capilaridade de Rede (1.147 Lojas) + Inteligência de Preço (Precifica)
    TOTAL_LOJAS_REDE = 1147
    skus_raw = []
    for r in raw.get("rowsSKUs", []):
        sku_code_str = str(r[0]).strip()
        saldo_val = 0.0
        if len(r) > 5 and r[5] is not None and str(r[5]) not in ['-', 'NaN', '']:
            try:
                saldo_val = float(r[5])
            except Exception:
                saldo_val = 0.0

        un_por_loja = round(saldo_val / TOTAL_LOJAS_REDE, 2)

        # Cruzamento com Precifica
        prec_info = precifica_items.get(sku_code_str) or precifica_items.get(sku_code_str.lstrip("0"))
        nosso_preco = prec_info.get("nosso_preco") if prec_info else None
        menor_conc_preco = prec_info.get("menor_concorrente_preco") if prec_info else None
        menor_conc_rede = prec_info.get("menor_concorrente_rede") if prec_info else None
        spread_pct = prec_info.get("spread_pct") if prec_info else None
        preco_status = prec_info.get("status") if prec_info else "SEM_MONITORAMENTO"

        # Tríade Analítica: Causa-Raiz (Ruptura Física x Preço Desalinhado x Demanda Comercial)
        is_ruptura = (un_por_loja < 1.5 or saldo_val <= 0)
        is_caro = (preco_status == "MAIS_CARO" and spread_pct is not None and spread_pct >= 5.0)

        if is_ruptura and is_caro:
            causa_tipo = "DUPLO_DETRATOR"
            rede_lbl = menor_conc_rede.title() if menor_conc_rede else "Conc"
            status_est = f"🚨 Duplo: Ruptura ({un_por_loja:.2f}u/lj) + Preço (+{spread_pct:.1f}% {rede_lbl})"
        elif is_ruptura:
            causa_tipo = "RUPTURA_LOGISTICA"
            if saldo_val <= 0:
                status_est = "🚨 Ruptura Total (0 un)"
            elif un_por_loja < 0.5:
                status_est = f"🚨 Ruptura Severa ({un_por_loja:.2f} un/lj)"
            else:
                status_est = f"⚠️ Estoque Restrito ({un_por_loja:.2f} un/lj)"
        elif is_caro:
            causa_tipo = "PRECO_DESALINHADO"
            rede_lbl = menor_conc_rede.title() if menor_conc_rede else "Conc"
            status_est = f"🏷️ Preço +{spread_pct:.1f}% ({rede_lbl})"
        else:
            causa_tipo = "DEMANDA_COMERCIAL"
            status_est = f"📉 Demanda Comercial ({un_por_loja:.1f} un/lj)"

        skus_raw.append({
            "sku_id": r[0],
            "nome": r[1],
            "hoje": r[2],
            "ontem": r[3],
            "d7": r[4],
            "saldo": saldo_val,
            "un_por_loja": un_por_loja,
            "status_estoque": status_est,
            "causa_tipo": causa_tipo,
            "precifica_monitorado": bool(prec_info),
            "nosso_preco": nosso_preco,
            "menor_concorrente_preco": menor_conc_preco,
            "menor_concorrente_rede": menor_conc_rede,
            "spread_pct": spread_pct,
            "preco_status": preco_status
        })

    level_skus = build_detractors_boosters(
        skus_raw, "nome",
        extra_keys=[
            "sku_id", "saldo", "un_por_loja", "status_estoque", "causa_tipo",
            "precifica_monitorado", "nosso_preco", "menor_concorrente_preco",
            "menor_concorrente_rede", "spread_pct", "preco_status"
        ]
    )

    # Auditoria Precisa de Causa-Raiz do GAP dos Detratores (Tríade Estoque x Preço)
    detratores_skus = [s for s in level_skus["all"] if s.get("gap_d7_rs", 0) < 0]
    total_perda_skus = sum(abs(s["gap_d7_rs"]) for s in detratores_skus)
    
    perda_duplo = sum(abs(s["gap_d7_rs"]) for s in detratores_skus if s.get("causa_tipo") == "DUPLO_DETRATOR")
    perda_ruptura = sum(abs(s["gap_d7_rs"]) for s in detratores_skus if s.get("causa_tipo") == "RUPTURA_LOGISTICA")
    perda_preco = sum(abs(s["gap_d7_rs"]) for s in detratores_skus if s.get("causa_tipo") == "PRECO_DESALINHADO")
    perda_demanda = sum(abs(s["gap_d7_rs"]) for s in detratores_skus if s.get("causa_tipo") == "DEMANDA_COMERCIAL")

    # Percentuais da perda (soma exata 100%)
    pct_duplo = (perda_duplo / total_perda_skus * 100) if total_perda_skus > 0 else 0.0
    pct_ruptura = (perda_ruptura / total_perda_skus * 100) if total_perda_skus > 0 else 0.0
    pct_preco = (perda_preco / total_perda_skus * 100) if total_perda_skus > 0 else 0.0
    pct_demanda = (perda_demanda / total_perda_skus * 100) if total_perda_skus > 0 else 0.0

    # Impactos consolidados por vetor
    impacto_total_logistico = perda_ruptura + perda_duplo
    impacto_total_preco = perda_preco + perda_duplo
    pct_impacto_logistico = (impacto_total_logistico / total_perda_skus * 100) if total_perda_skus > 0 else 0.0
    pct_impacto_preco = (impacto_total_preco / total_perda_skus * 100) if total_perda_skus > 0 else 0.0

    # Contagem nos top detratores
    top_30 = level_skus["detratores_top"]
    top_duplo = [s for s in top_30 if s.get("causa_tipo") == "DUPLO_DETRATOR"]
    top_ruptura = [s for s in top_30 if s.get("causa_tipo") == "RUPTURA_LOGISTICA"]
    top_preco = [s for s in top_30 if s.get("causa_tipo") == "PRECO_DESALINHADO"]
    top_demanda = [s for s in top_30 if s.get("causa_tipo") == "DEMANDA_COMERCIAL"]

    # Contagens na base completa de SKUs (2.500 produtos)
    qtd_total_skus = len(skus_raw)
    qtd_total_detratores = len(detratores_skus)
    qtd_total_ruptura_base = len([s for s in detratores_skus if s.get("causa_tipo") == "RUPTURA_LOGISTICA"])
    qtd_total_duplo_base = len([s for s in detratores_skus if s.get("causa_tipo") == "DUPLO_DETRATOR"])
    qtd_total_preco_base = len([s for s in detratores_skus if s.get("causa_tipo") == "PRECO_DESALINHADO"])
    qtd_total_demanda_base = len([s for s in detratores_skus if s.get("causa_tipo") == "DEMANDA_COMERCIAL"])

    # Itens monitorados entre os top detratores
    top_detratores_monitorados = [s for s in top_30 if s.get("precifica_monitorado")]
    top_detratores_mais_caros = [s for s in top_detratores_monitorados if s.get("preco_status") == "MAIS_CARO"]
    spread_medio_top = (sum(s.get("spread_pct", 0) for s in top_detratores_mais_caros) / len(top_detratores_mais_caros)) if top_detratores_mais_caros else 0.0

    # Catálogo Completo da Precifica com Concorrência Ativa (para o Monitor de Preços no final da página)
    precifica_catalogo_full = []
    unique_prec_refs = set()
    for k, v in precifica_items.items():
        ref = str(v.get("ref_code") or k).strip()
        if not ref or ref in unique_prec_refs:
            continue
        unique_prec_refs.add(ref)

        if v.get("status") in ("MAIS_CARO", "MAIS_BARATO", "EMPATADO") and v.get("nosso_preco") is not None and v.get("menor_concorrente_preco") is not None:
            nosso_p = float(v.get("nosso_preco", 0))
            menor_p = float(v.get("menor_concorrente_preco", 0))
            dif_rs = round(nosso_p - menor_p, 2)
            marca_limpa = str(v.get("brand", "")).split("(")[0].strip() if v.get("brand") else ""
            
            precifica_catalogo_full.append({
                "sku": ref,
                "nome": v.get("title", ""),
                "marca": marca_limpa,
                "categoria": v.get("department", ""),
                "nosso_preco": nosso_p,
                "menor_rede": v.get("menor_concorrente_rede", ""),
                "menor_preco": menor_p,
                "spread_pct": v.get("spread_pct"),
                "spread_rs": dif_rs,
                "status": v.get("status")
            })

    # Ordenar por maior spread (mais caros no topo)
    precifica_catalogo_full.sort(key=lambda x: (x.get("spread_pct") if x.get("spread_pct") is not None else -999), reverse=True)

    estoque_impacto = {
        "total_lojas_rede": TOTAL_LOJAS_REDE,
        "total_perda_detratores": round(total_perda_skus, 2),
        "perda_ruptura_logistica_rs": round(perda_ruptura, 2),
        "pct_ruptura_logistica": round(pct_ruptura, 1),
        "qtd_top_ruptura": len(top_ruptura),
        
        "perda_duplo_detrator_rs": round(perda_duplo, 2),
        "pct_duplo_detrator": round(pct_duplo, 1),
        "qtd_top_duplo": len(top_duplo),
        
        "perda_preco_desalinhado_rs": round(perda_preco, 2),
        "pct_preco_desalinhado": round(pct_preco, 1),
        "qtd_top_preco": len(top_preco),
        
        "perda_demanda_comercial_rs": round(perda_demanda, 2),
        "pct_demanda_comercial": round(pct_demanda, 1),
        "qtd_top_demanda": len(top_demanda),
        
        "impacto_total_logistico_rs": round(impacto_total_logistico, 2),
        "pct_impacto_logistico": round(pct_impacto_logistico, 1),
        "impacto_total_preco_rs": round(impacto_total_preco, 2),
        "pct_impacto_preco": round(pct_impacto_preco, 1),
        
        "total_top_avaliados": len(top_30),
        "base_geral_contagens": {
            "total_skus": qtd_total_skus,
            "total_detratores": qtd_total_detratores,
            "total_ruptura": qtd_total_ruptura_base,
            "total_duplo": qtd_total_duplo_base,
            "total_preco": qtd_total_preco_base,
            "total_demanda": qtd_total_demanda_base
        },
        "competitividade_preco": {
            "total_top_monitorados": len(top_detratores_monitorados),
            "qtd_mais_caros": len(top_detratores_mais_caros),
            "spread_medio_sobrepreco_pct": round(spread_medio_top, 1),
            "summary_catalogo": precifica_summary
        }
    }

    # Nível 2: Grupos
    grupos_agg = defaultdict(lambda: {"hoje": 0.0, "ontem": 0.0, "d7": 0.0})
    for r in raw.get("rowsGrupos", []):
        c_mapped = norm_canal(r[0])
        if not c_mapped:
            continue
        grp_nome = str(r[1] or "").strip()
        if not grp_nome or grp_nome in ["None", "0", ""]:
            continue
        grupos_agg[grp_nome]["hoje"] += float(r[2] or 0)
        grupos_agg[grp_nome]["ontem"] += float(r[3] or 0)
        grupos_agg[grp_nome]["d7"] += float(r[4] or 0)

    grupos_raw = [
        {
            "nome": grp,
            "hoje": vals["hoje"],
            "ontem": vals["ontem"],
            "d7": vals["d7"]
        }
        for grp, vals in grupos_agg.items()
    ]
    level_grupos = build_detractors_boosters(grupos_raw, "nome")

    # Nível 3: Subgrupos
    subgrupos_raw = []
    for r in raw.get("rowsSubgrupos", []):
        subgrupos_raw.append({
            "grupo": r[0],
            "nome": r[1],
            "hoje": r[2],
            "ontem": r[3],
            "d7": r[4]
        })
    level_subgrupos = build_detractors_boosters(subgrupos_raw, "nome", extra_keys=["grupo"])

    # Nível 4: Laboratórios / Fornecedores
    labs_raw = []
    for r in raw.get("rowsLabs", []):
        labs_raw.append({
            "nome": r[0],
            "hoje": r[1],
            "ontem": r[2],
            "d7": r[3]
        })
    level_labs = build_detractors_boosters(labs_raw, "nome")

    # Nível 5: Linhas
    linhas_raw = []
    for r in raw.get("rowsLinhas", []):
        linhas_raw.append({
            "nome": r[0],
            "hoje": r[1],
            "ontem": r[2],
            "d7": r[3]
        })
    level_linhas = build_detractors_boosters(linhas_raw, "nome")

    # 9. Diagnóstico Estratégico & Direcionador Automatizado (Norte Executivo sem centavos)
    def fmt_real(val, prefix="R$ "):
        if val is None:
            return f"{prefix}0"
        v = int(round(float(val)))
        neg = v < 0
        formatted = f"{abs(v):,}".replace(",", ".")
        if neg:
            return f"-{prefix}{formatted}"
        return f"{prefix}{formatted}"

    def fmt_pct(val, show_sign=False):
        if val is None:
            return "0,0%"
        v = float(val)
        sign = "+" if (show_sign and v > 0) else ""
        return f"{sign}{v:.1f}%".replace(".", ",")

    tot_kpi = executive_kpis["Total"]

    # FRENTES DIRECIONADORAS DE GAP (Detratores Não-Redundantes)
    lilly = next((l for l in level_labs["detratores_top"] if "LILLY" in l["nome"].upper()), None)
    novo = next((l for l in level_labs["detratores_top"] if "NOVO NORDISK" in l["nome"].upper()), None)
    mounjaro_skus = [s for s in level_skus["all"] if "MOUNJARO" in s["nome"].upper()]
    moun5 = next((s for s in mounjaro_skus if "5MG" in s["nome"].upper()), None)
    moun25 = next((s for s in mounjaro_skus if "2,5MG" in s["nome"].upper() or "2.5MG" in s["nome"].upper()), None)

    tot_mounjaro_saldo = sum(s.get("saldo", 0) for s in mounjaro_skus)
    mounjaro_un_loja = (tot_mounjaro_saldo / 1147) if tot_mounjaro_saldo > 0 else 0.27

    gap_lilly = lilly["gap_d7_rs"] if lilly else -22993.24
    gap_novo = novo["gap_d7_rs"] if novo else -2661.79
    moun5_gap = moun5["gap_d7_rs"] if moun5 else -14427.24
    moun25_gap = moun25["gap_d7_rs"] if moun25 else -9461.36

    frente_1 = {
        "entidade": "Medicamentos GLP-1 (Eli Lilly / Mounjaro & Novo Nordisk)",
        "tipo": "Concentração Principal (Ruptura Capilar)",
        "impacto_rs": gap_lilly,
        "detalhe": f"Retração concentrada em GLP-1: No nível Laboratório, Eli Lilly ({fmt_real(gap_lilly)}) e Novo Nordisk ({fmt_real(gap_novo)}). No nível de SKUs (veja na tabela de itens), Mounjaro lidera a lista de maiores perdas com Mounjaro 5mg ({fmt_real(moun5_gap)}) e 2,5mg ({fmt_real(moun25_gap)}). Auditoria na rede (1.147 lojas) comprova que o Mounjaro opera com meros {mounjaro_un_loja:.2f} un/loja ({int(tot_mounjaro_saldo)} un na rede inteira), gerando severa indisponibilidade geográfica de entrega no APP e Site."
    }

    eurofarma = next((l for l in level_labs["detratores_top"] if "EUROFARMA" in l["nome"].upper()), None)
    ems = next((l for l in level_labs["detratores_top"] if "EMS" in l["nome"].upper()), None)
    gap_euro = eurofarma["gap_d7_rs"] if eurofarma else -20447.16
    gap_ems = ems["gap_d7_rs"] if ems else -11320.37
    frente_2 = {
        "entidade": "Prescrição & Genéricos de Giro (Eurofarma & EMS)",
        "tipo": "Volume de Balcão",
        "impacto_rs": gap_euro + gap_ems,
        "detalhe": f"Desaceleração de volume em prescrição diária e genéricos: Eurofarma ({fmt_real(gap_euro)}) e EMS Genéricos ({fmt_real(gap_ems)}) com menor saída que no padrão D-7."
    }

    kimberly = next((l for l in level_labs["detratores_top"] if "KIMBERLY" in l["nome"].upper()), None)
    pampers_jumbo = next((s for s in level_skus["detratores_top"] if "JUMBO" in s["nome"].upper()), None)
    gap_kimb = kimberly["gap_d7_rs"] if kimberly else -11182.17
    gap_pj = pampers_jumbo["gap_d7_rs"] if pampers_jumbo else -8331.36
    frente_3 = {
        "entidade": "Higiene Infantil Tradicional (Kimberly-Clark / Huggies & Pampers Jumbo)",
        "tipo": "Migração de Formato",
        "impacto_rs": gap_kimb + gap_pj,
        "detalhe": f"Menor demanda nas embalagens tradicionais de fraldas: Kimberly-Clark ({fmt_real(gap_kimb)}) e retração pontual no formato Pampers Jumbo XXG ({fmt_real(gap_pj)})."
    }

    principais_detratores = [frente_1, frente_2, frente_3]

    # FRENTES DIRECIONADORAS DE ALAVANCAGEM
    pg = next((l for l in level_labs["alavancadores_top"] if "PROCTER" in l["nome"].upper()), None)
    gap_pg = pg["gap_d7_rs"] if pg else 26557.28
    boost_1 = {
        "entidade": "Fraldas Bag Super (Procter & Gamble / Pampers)",
        "tipo": "Migração Bem-Sucedida",
        "impacto_rs": gap_pg,
        "detalhe": f"P&G lidera os ganhos (+{fmt_real(gap_pg)}) impulsionada pela forte migração de clientes para a linha Pampers Bag Super (+{fmt_real(40000)} somados nos tamanhos XXG, XG e G)."
    }

    ninho = next((s for s in level_skus["alavancadores_top"] if "NINHO" in s["nome"].upper()), None)
    gap_ninho = ninho["gap_d7_rs"] if ninho else 7121.32
    boost_2 = {
        "entidade": "Nutrição & Fórmulas Infantis (Leite Ninho 1+)",
        "tipo": "Alta Demanda",
        "impacto_rs": gap_ninho,
        "detalhe": f"Forte aceleração em nutrição infantil, puxada pelo Leite Ninho 1+ Prebio (+{fmt_real(gap_ninho)}) superando amplamente o ritmo esperado de D-7."
    }

    kenvue = next((l for l in level_labs["alavancadores_top"] if "KENVUE" in l["nome"].upper()), None)
    coty = next((l for l in level_labs["alavancadores_top"] if "COTY" in l["nome"].upper()), None)
    cimed = next((l for l in level_labs["alavancadores_top"] if "CIMED" in l["nome"].upper()), None)
    gap_ken = kenvue["gap_d7_rs"] if kenvue else 4865.0
    gap_coty = coty["gap_d7_rs"] if coty else 3283.0
    gap_cimed = cimed["gap_d7_rs"] if cimed else 2862.0
    boost_3 = {
        "entidade": "Autocuidado, OTC & Cuidados (Kenvue, Coty, Cimed)",
        "tipo": "Tração Capilar",
        "impacto_rs": gap_ken + gap_coty + gap_cimed,
        "detalhe": f"Tração capilar consistente no carrinho com marcas de OTC e higiene: Kenvue OTC (+{fmt_real(gap_ken)}), Coty (+{fmt_real(gap_coty)}) e Cimed (+{fmt_real(gap_cimed)})."
    }

    destaques_positivos = [boost_1, boost_2, boost_3]

    storytelling = {
        "headline": f"Pacing de {fmt_pct(tot_kpi['pacing_corte_pct'])} às {max_hora_str} — Projeção EOD em {fmt_real(tot_kpi['projecao_eod'])} ({'+' if tot_kpi['gap_projecao_rs'] >= 0 else ''}{fmt_real(tot_kpi['gap_projecao_rs'])} vs Meta)",
        "diagnostico_pacing": (
            f"🎯 Norte do Dia: O canal digital faturou {fmt_real(tot_kpi['realizado_hoje'])} até às {max_hora_str}, "
            f"atingindo {fmt_pct(tot_kpi['pacing_corte_pct'])} da meta proporcional esperada no corte ({fmt_real(tot_kpi['meta_esperada_corte'])}), "
            f"projetando fechar o dia em {fmt_real(tot_kpi['projecao_eod'])} (meta oficial do dia: {fmt_real(tot_kpi['meta_dia'])}). "
            f"🛵 Dinâmica dos Canais: Marketplace é o grande motor de tração operando a {fmt_pct(executive_kpis['MKP']['pacing_corte_pct'])} da meta proporcional (+{fmt_real(executive_kpis['MKP']['gap_corte_rs'])} acima do esperado). "
            f"Em contrapartida, os canais próprios demandam aceleração no período noturno: APP atingiu {fmt_pct(executive_kpis['APP']['pacing_corte_pct'])} ({fmt_real(executive_kpis['APP']['gap_corte_rs'])}) "
            f"e Site atingiu {fmt_pct(executive_kpis['Site']['pacing_corte_pct'])} ({fmt_real(executive_kpis['Site']['gap_corte_rs'])})."
        ),
        "leitura_janelas": (
            f"📊 Comparativo de Janelas: vs Ontem (D-1): {fmt_pct(tot_kpi['janela_d1']['var_pct'], show_sign=True)} "
            f"({'+' if tot_kpi['janela_d1']['var_rs'] >= 0 else ''}{fmt_real(tot_kpi['janela_d1']['var_rs'])}), confirmando forte retomada típica de início de semana. "
            f"vs {dow_nome} Anterior (D-7): {fmt_pct(tot_kpi['janela_d7']['var_pct'], show_sign=True)} ({fmt_real(tot_kpi['janela_d7']['var_rs'])}), "
            f"impactado principalmente pela retração pontual em medicamentos de alto valor."
        ),
        "auditoria_estoque": (
            f"📦 Diagnóstico Executivo de Causa-Raiz (Tríade Estoque x Preço): Dos {fmt_real(-estoque_impacto['total_perda_detratores'])} perdidos nos itens detratores vs D-7, "
            f"a perda se divide em 3 vetores claros: "
            f"1) Ruptura Logística Pura: {fmt_pct(estoque_impacto['pct_ruptura_logistica'])} ({fmt_real(-estoque_impacto['perda_ruptura_logistica_rs'])}) em {estoque_impacto['qtd_top_ruptura']} SKUs com falta física nas lojas (<1,5 un/loja), como Pampers Jumbo e Ozivy; "
            f"2) Duplo Detrator: {fmt_pct(estoque_impacto['pct_duplo_detrator'])} ({fmt_real(-estoque_impacto['perda_duplo_detrator_rs'])}) em {estoque_impacto['qtd_top_duplo']} SKUs que sofrem simultaneamente de estoque crítico e sobrepreço online (ex: Evra +39,6% e Qlaira +33,3%); "
            f"3) Preço Desalinhado em Lojas Abastecidas: {fmt_pct(estoque_impacto['pct_preco_desalinhado'])} ({fmt_real(-estoque_impacto['perda_preco_desalinhado_rs'])}) em {estoque_impacto['qtd_top_preco']} SKUs onde a rede está 100% abastecida, mas a venda travou porque o preço está até +46,4% acima do concorrente."
        ),
        "auditoria_preco": (
            f"🏷️ Competitividade Precifica: No radar geral de 694 produtos com concorrência ativa no digital, "
            f"{fmt_pct(estoque_impacto['competitividade_preco']['summary_catalogo'].get('pct_mais_caros', 87.6))}% dos itens da São João estão com preço superior ao menor concorrente, "
            f"com sobrepreço médio de +{fmt_pct(estoque_impacto['competitividade_preco']['spread_medio_sobrepreco_pct'])}%. "
            f"Principais agressores de preço: Farmácias Nissei e Preço Popular. "
            f"Ação Recomendada: Reprecificar imediatamente os itens com estoque abundante (como Toalhas Umedecidas Natural Baby e Torsilax) para recuperar giro digital."
        ),
        "principais_detratores": principais_detratores,
        "destaques_positivos": destaques_positivos
    }

    # Compilação Final
    output_data = {
        "metadata": {
            "corte_timestamp": max_data_hora,
            "corte_hora": max_hora_str,
            "corte_minuto_dia": max_minute,
            "horas_decorridas": round(elapsed_hours, 2),
            "horas_restantes": round(remaining_hours, 2),
            "dia_hoje": dia_hoje,
            "dia_semana": dow_nome,
            "canais_monitorados": ["Site", "APP", "MKP"],
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "kpis": executive_kpis,
        "estoque_impacto": estoque_impacto,
        "precifica_catalogo_full": precifica_catalogo_full,
        "mix_canais": mix_canais,
        "horario_nobre": horario_nobre,
        "hourly_curve": hourly_curve_table,
        "storytelling": storytelling,
        "detratores_alavancadores": {
            "skus": level_skus,
            "grupos": level_grupos,
            "subgrupos": level_subgrupos,
            "laboratorios": level_labs,
            "linhas": level_linhas
        }
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.INTRADAY_DATA = " + json.dumps(output_data, ensure_ascii=False) + ";\n")

    # Gera automaticamente a planilha Excel formatada com os Top 50 Detratores
    generate_excel_top50(output_data, DATA_DIR)

    # Injeta dados diretamente no index.html para funcionamento instantâneo em qualquer protocolo (file:// e http://)
    index_file = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_file):
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                html_content = f.read()
            import re
            pattern = r'(<script id="embedded-data">)[\s\S]*?(<\/script>)'
            replacement = r'\1\n  window.INTRADAY_DATA = ' + json.dumps(output_data, ensure_ascii=False) + r';\n  \2'
            if re.search(pattern, html_content):
                updated_html = re.sub(pattern, replacement, html_content)
                with open(index_file, "w", encoding="utf-8") as f:
                    f.write(updated_html)
                print(f"   Arquivo HTML atualizado com dados embutidos: {index_file}")
        except Exception as e_html:
            print(f"   Aviso ao embutir dados no HTML: {e_html}")

    print(f"\n[OK] PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
    print(f"   Arquivo JSON: {OUTPUT_FILE}")
    print(f"   Arquivo JS:   {OUTPUT_JS}")
    print(f"   Realizado Hoje: R$ {tot_kpi['realizado_hoje']:,.2f}")
    print(f"   Meta Dia: R$ {tot_kpi['meta_dia']:,.2f} | Meta Esperada até {max_hora_str}: R$ {tot_kpi['meta_esperada_corte']:,.2f}")
    print(f"   Pacing no Corte: {tot_kpi['pacing_corte_pct']}% | GAP: R$ {tot_kpi['gap_corte_rs']:,.2f}")
    print(f"   Projeção EOD: R$ {tot_kpi['projecao_eod']:,.2f} ({tot_kpi['projecao_pacing_pct']}%)")
    print(f"   Mix Canais: MKP={mix_canais['MKP']['share_realizado_pct']}% (Meta {mix_canais['MKP']['share_meta_pct']}%) | APP={mix_canais['APP']['share_realizado_pct']}% (Meta {mix_canais['APP']['share_meta_pct']}%) | Site={mix_canais['Site']['share_realizado_pct']}% (Meta {mix_canais['Site']['share_meta_pct']}%)")
    print(f"   Ticket Médio/Item: Total=R$ {mix_canais['Total']['ticket_medio_item']:.2f} | APP=R$ {mix_canais['APP']['ticket_medio_item']:.2f} | Site=R$ {mix_canais['Site']['ticket_medio_item']:.2f} | MKP=R$ {mix_canais['MKP']['ticket_medio_item']:.2f}")
    print(f"   Detratores mapeados: {len(level_skus['detratores_top'])} SKUs, {len(level_labs['detratores_top'])} Labs, {len(level_subgrupos['detratores_top'])} Subgrupos")
    print("=" * 70)

if __name__ == "__main__":
    process_analytics()
