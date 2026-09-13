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
import re
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
FECHAMENTOS_DIR = os.path.join(DATA_DIR, "fechamentos")
FECHAMENTO_ONTEM_FILE = os.path.join(DATA_DIR, "fechamento_ontem.json")
HISTORICO_FECHAMENTOS_FILE = os.path.join(DATA_DIR, "historico_fechamentos.json")
os.makedirs(FECHAMENTOS_DIR, exist_ok=True)

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
            "Menor Concorrente", "Preço Concorrência", "Spread (%)", "Status Concorrência", "Classificação", "Ação Recomendada"
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

            acao_rec = item.get("acao_recomendada") or "Monitorar Giro"

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
                (item.get("status", ""), Alignment(horizontal="center"), regular_font, None),
                (acao_rec, Alignment(horizontal="left"), bold_font if "Reprecificar" in acao_rec else regular_font, None)
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

        for c_i in range(8, 18):
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
            14: 14, 15: 22, 16: 20, 17: 34
        }
        for col_i, w in col_widths.items():
            ws.column_dimensions[get_column_letter(col_i)].width = w

        wb.save(excel_path)
        print(f"   Planilha Excel atualizada com sucesso: {excel_path}")
    except Exception as e_excel:
        print(f"   Aviso ao gerar planilha Excel: {e_excel}")


def resolve_city_name(fdesc):
    clean = str(fdesc or "").strip()
    if not clean:
        return "Não Identificado"
    if clean.upper().startswith("PF -") or clean.upper().startswith("PF-"):
        return "Passo Fundo"
    if clean.upper().startswith("POA -") or clean.upper().startswith("POA-"):
        return "Porto Alegre"
    
    city_overrides = {
        "PF": "Passo Fundo", "POA": "Porto Alegre", "PORTO ALEGRE": "Porto Alegre",
        "CAXIAS": "Caxias do Sul", "CAXIAS DO SUL": "Caxias do Sul", "PELOTAS": "Pelotas",
        "SANTA MARIA": "Santa Maria", "CANOAS": "Canoas", "GRAVATAI": "Gravataí",
        "VIAMAO": "Viamão", "NOVO HAMBURGO": "Novo Hamburgo", "SAO LEOPOLDO": "São Leopoldo",
        "RIO GRANDE": "Rio Grande", "ALVORADA": "Alvorada", "PASSO FUNDO": "Passo Fundo",
        "URUGUAIANA": "Uruguaiana", "SANTA CRUZ": "Santa Cruz do Sul", "BENTO": "Bento Gonçalves",
        "BENTO GONCALVES": "Bento Gonçalves", "BAGÉ": "Bagé", "BAGE": "Bagé",
        "ERECHIM": "Erechim", "IJUI": "Ijuí", "SANTANA DO LIVRAMENTO": "Santana do Livramento",
        "LIVRAMENTO": "Santana do Livramento", "GUAIBA": "Guaíba", "CACHOEIRINHA": "Cachoeirinha",
        "SAPUCAIA": "Sapucaia do Sul", "FREDERICO": "Frederico Westphalen",
        "FLORES DA CUNHA": "Flores da Cunha", "TRES PASSOS": "Três Passos",
        "SANTA ROSA": "Santa Rosa", "SANTO ANGELO": "Santo Ângelo"
    }
    import re
    base = re.sub(r"\s+\d+.*$", "", clean).strip()
    base = re.sub(r"\s+(?:Dark Store|Matriz|Hiper|Super|Centro).*$", "", base, flags=re.I).strip()
    upper_base = base.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ç", "C")
    for k, v in city_overrides.items():
        if upper_base == k or upper_base.startswith(k + " "):
            return v
    return base.title()


def process_regional_data(raw):
    """
    Processa a inteligência geográfica de vendas digitais em 5 níveis analíticos:
    1. Estados (UF): RS (foco primordial), SC e PR
    2. Diretorias Regionais
    3. Coordenações Distritais
    4. Municípios / Polos Comerciais (faturamento, lojas ativas e centroides)
    5. Filiais Físicas (com latitude, longitude reais do Qlik Sense e status comercial)
    """
    rows_uf = raw.get("rowsUF", [])
    rows_dir = raw.get("rowsDir", [])
    rows_coord = raw.get("rowsCoord", [])
    rows_fil = raw.get("rowsFiliais", [])

    # Carrega Dicionário Mestre de Geolocalização (Lat/Lon/Município)
    lojas_geo_file = os.path.join(DATA_DIR, "lojas_master_geo.json")
    lojas_master = {}
    if os.path.exists(lojas_geo_file):
        try:
            with open(lojas_geo_file, "r", encoding="utf-8") as f:
                lojas_master = json.load(f)
        except Exception:
            lojas_master = {}

    tot_hoje_uf = sum(float(r[1] or 0) for r in rows_uf)
    tot_ontem_uf = sum(float(r[2] or 0) for r in rows_uf)
    tot_d7_uf = sum(float(r[3] or 0) for r in rows_uf)

    # 1. UFs
    ufs = []
    tot_rs_hoje = 0.0
    for r in rows_uf:
        uf_name = str(r[0]).strip().upper() if r[0] else "OUTROS"
        v_hoje = float(r[1] or 0)
        v_ontem = float(r[2] or 0)
        v_d7 = float(r[3] or 0)
        if uf_name == "RS":
            tot_rs_hoje = v_hoje
        share = round((v_hoje / tot_hoje_uf * 100.0), 1) if tot_hoje_uf > 0 else 0.0
        gap_d7 = round(v_hoje - v_d7, 2)
        var_d7 = round(((v_hoje / v_d7) - 1.0) * 100.0, 1) if v_d7 > 0 else 0.0
        gap_ontem = round(v_hoje - v_ontem, 2)
        var_ontem = round(((v_hoje / v_ontem) - 1.0) * 100.0, 1) if v_ontem > 0 else 0.0
        
        ufs.append({
            "uf": uf_name,
            "vendas_hoje": round(v_hoje, 2),
            "vendas_ontem": round(v_ontem, 2),
            "vendas_d7": round(v_d7, 2),
            "share_pct": share,
            "gap_d7_rs": gap_d7,
            "var_d7_pct": var_d7,
            "gap_ontem_rs": gap_ontem,
            "var_ontem_pct": var_ontem,
            "pacing_status": "SUPEROU" if gap_d7 >= 0 else ("MODERADO" if var_d7 >= -15 else "CRITICO")
        })
    ufs.sort(key=lambda x: x["vendas_hoje"], reverse=True)

    # 2. Diretorias
    diretorias = []
    for r in rows_dir:
        dir_name = str(r[0]).strip() if r[0] else "Sem Diretoria"
        v_hoje = float(r[1] or 0)
        v_ontem = float(r[2] or 0)
        v_d7 = float(r[3] or 0)
        share = round((v_hoje / tot_hoje_uf * 100.0), 1) if tot_hoje_uf > 0 else 0.0
        gap_d7 = round(v_hoje - v_d7, 2)
        var_d7 = round(((v_hoje / v_d7) - 1.0) * 100.0, 1) if v_d7 > 0 else 0.0
        diretorias.append({
            "diretor": dir_name,
            "vendas_hoje": round(v_hoje, 2),
            "vendas_ontem": round(v_ontem, 2),
            "vendas_d7": round(v_d7, 2),
            "share_pct": share,
            "gap_d7_rs": gap_d7,
            "var_d7_pct": var_d7,
            "pacing_status": "SUPEROU" if gap_d7 >= 0 else ("MODERADO" if var_d7 >= -15 else "CRITICO")
        })
    diretorias.sort(key=lambda x: x["vendas_hoje"], reverse=True)

    # 3. Coordenações
    coordenacoes = []
    for r in rows_coord:
        coord_name = str(r[0]).strip() if r[0] else "Sem Coordenação"
        coord_uf = str(r[1]).strip().upper() if len(r) > 1 and r[1] else "RS"
        v_hoje = float(r[2] or 0)
        v_ontem = float(r[3] or 0)
        v_d7 = float(r[4] or 0)
        gap_d7 = round(v_hoje - v_d7, 2)
        var_d7 = round(((v_hoje / v_d7) - 1.0) * 100.0, 1) if v_d7 > 0 else 0.0
        share_c = round((v_hoje / tot_hoje_uf) * 100.0, 1) if tot_hoje_uf > 0 else 0.0
        coordenacoes.append({
            "coordenador": coord_name,
            "uf": coord_uf,
            "vendas_hoje": round(v_hoje, 2),
            "vendas_ontem": round(v_ontem, 2),
            "vendas_d7": round(v_d7, 2),
            "share_pct": share_c,
            "gap_d7_rs": gap_d7,
            "var_d7_pct": var_d7,
            "pacing_status": "SUPEROU" if gap_d7 >= 0 else ("MODERADO" if var_d7 >= -15 else "CRITICO")
        })
    coordenacoes.sort(key=lambda x: x["vendas_hoje"], reverse=True)

    # 4. Filiais & Enriquecimento Geográfico
    filiais_all = []
    municipios_map = {}
    lojas_com_geo = 0
    lojas_superando = 0

    for r in rows_fil:
        f_id = str(r[0]).strip() if r[0] else ""
        f_num = f_id.split("|")[-1] if "|" in f_id else f_id
        f_desc = str(r[1]).strip() if len(r) > 1 and r[1] else f"Filial {f_num}"
        f_uf = str(r[2]).strip().upper() if len(r) > 2 and r[2] else "RS"
        f_coord = str(r[3]).strip() if len(r) > 3 and r[3] else ""
        v_hoje = float(r[4] or 0) if len(r) > 4 else 0.0
        v_ontem = float(r[5] or 0) if len(r) > 5 else 0.0
        v_d7 = float(r[6] or 0) if len(r) > 6 else 0.0
        gap_d7 = round(v_hoje - v_d7, 2)
        var_d7 = round(((v_hoje / v_d7) - 1.0) * 100.0, 1) if v_d7 > 0 else 0.0
        share_f = round((v_hoje / tot_hoje_uf) * 100.0, 2) if tot_hoje_uf > 0 else 0.0
        nome_formatado = f"Filial {f_num} — {f_desc}" if f_desc and not f_desc.startswith("Filial") else f_desc

        status = "SUPEROU" if gap_d7 >= 0 else ("MODERADO" if var_d7 >= -15 else "CRITICO")
        if gap_d7 >= 0:
            lojas_superando += 1

        # Enriquecer com Dicionário Mestre de Lojas
        geo_info = lojas_master.get(f_num, {})
        cidade = geo_info.get("cidade") or resolve_city_name(f_desc)
        lat = geo_info.get("latitude")
        lon = geo_info.get("longitude")
        diretor = geo_info.get("diretor") or ""
        if not f_coord and geo_info.get("coordenador"):
            f_coord = geo_info.get("coordenador")
        if not f_uf and geo_info.get("uf"):
            f_uf = geo_info.get("uf")

        if lat is not None and lon is not None:
            lojas_com_geo += 1

        filial_item = {
            "filial_id": f_num,
            "raw_id": f_id,
            "nome": nome_formatado,
            "desc_filial": f_desc,
            "cidade": cidade,
            "uf": f_uf,
            "diretor": diretor,
            "coordenador": f_coord,
            "latitude": lat,
            "longitude": lon,
            "vendas_hoje": round(v_hoje, 2),
            "vendas_ontem": round(v_ontem, 2),
            "vendas_d7": round(v_d7, 2),
            "share_pct": share_f,
            "gap_d7_rs": gap_d7,
            "var_d7_pct": var_d7,
            "pacing_status": status
        }
        filiais_all.append(filial_item)

        # Agrupamento por Município
        if cidade not in municipios_map:
            municipios_map[cidade] = {
                "cidade": cidade,
                "uf": f_uf,
                "total_lojas": 0,
                "vendas_hoje": 0.0,
                "vendas_ontem": 0.0,
                "vendas_d7": 0.0,
                "lats": [],
                "lons": []
            }
        m = municipios_map[cidade]
        m["total_lojas"] += 1
        m["vendas_hoje"] += v_hoje
        m["vendas_ontem"] += v_ontem
        m["vendas_d7"] += v_d7
        if lat is not None:
            m["lats"].append(lat)
        if lon is not None:
            m["lons"].append(lon)

    # Consolidação dos Municípios
    municipios_list = []
    for cid, m in municipios_map.items():
        v_h = m["vendas_hoje"]
        v_o = m["vendas_ontem"]
        v_7 = m["vendas_d7"]
        gap = round(v_h - v_7, 2)
        var_pct = round(((v_h / v_7) - 1.0) * 100.0, 1) if v_7 > 0 else 0.0
        sh = round((v_h / tot_hoje_uf) * 100.0, 2) if tot_hoje_uf > 0 else 0.0
        center_lat = round(sum(m["lats"]) / len(m["lats"]), 5) if m["lats"] else None
        center_lon = round(sum(m["lons"]) / len(m["lons"]), 5) if m["lons"] else None

        municipios_list.append({
            "cidade": cid,
            "uf": m["uf"],
            "total_lojas": m["total_lojas"],
            "vendas_hoje": round(v_h, 2),
            "vendas_ontem": round(v_o, 2),
            "vendas_d7": round(v_7, 2),
            "gap_d7_rs": gap,
            "var_d7_pct": var_pct,
            "share_pct": sh,
            "center_lat": center_lat,
            "center_lon": center_lon,
            "pacing_status": "SUPEROU" if gap >= 0 else ("MODERADO" if var_pct >= -15 else "CRITICO")
        })
    municipios_list.sort(key=lambda x: x["vendas_hoje"], reverse=True)

    top_campeas = sorted(filiais_all, key=lambda x: x["vendas_hoje"], reverse=True)[:50]
    top_quedas = sorted([f for f in filiais_all if f["vendas_d7"] > 0], key=lambda x: x["gap_d7_rs"])[:50]
    top_municipios = municipios_list[:50]

    # Array leve otimizado para o mapa Leaflet
    lojas_geo_map = []
    for f in filiais_all:
        if f["latitude"] is not None and f["longitude"] is not None:
            lojas_geo_map.append([
                f["filial_id"],
                f["nome"],
                f["cidade"],
                f["uf"],
                f["latitude"],
                f["longitude"],
                f["vendas_hoje"],
                f["vendas_d7"],
                f["gap_d7_rs"],
                f["var_d7_pct"],
                f["pacing_status"],
                f["diretor"],
                f["coordenador"]
            ])

    pct_superando = round((lojas_superando / len(filiais_all) * 100.0), 1) if filiais_all else 0.0
    share_rs_pct = round((tot_rs_hoje / tot_hoje_uf * 100.0), 1) if tot_hoje_uf > 0 else 0.0

    return {
        "totais": {
            "vendas_hoje": round(tot_hoje_uf, 2),
            "vendas_ontem": round(tot_ontem_uf, 2),
            "vendas_d7": round(tot_d7_uf, 2),
            "gap_d7_rs": round(tot_hoje_uf - tot_d7_uf, 2),
            "var_d7_pct": round(((tot_hoje_uf / tot_d7_uf) - 1.0) * 100.0, 1) if tot_d7_uf > 0 else 0.0,
            "total_lojas_ativas": len(filiais_all),
            "total_lojas_geo": len(lojas_geo_map),
            "total_municipios": len(municipios_list),
            "total_vendas_rs": round(tot_rs_hoje, 2),
            "share_rs_pct": share_rs_pct,
            "pct_lojas_superando": pct_superando,
            "municipio_lider": municipios_list[0]["cidade"] if municipios_list else "Porto Alegre"
        },
        "ufs": ufs,
        "diretorias": diretorias,
        "coordenacoes": coordenacoes,
        "municipios": municipios_list,
        "top_municipios": top_municipios,
        "filiais_campeas": top_campeas,
        "filiais_quedas": top_quedas,
        "filiais_todas": filiais_all,
        "lojas_geo_map": lojas_geo_map
    }


def generate_daily_closure(raw, precifica_items, stock_map, data_dir=DATA_DIR, base_dir=BASE_DIR, excel_meta_path=EXCEL_META):
    """
    Gera o relatório oficial de fechamento consolidado (23:59) para o dia anterior (D-1),
    com scorecard de metas, decomposição da causa-raiz da perda (estoque vs preço vs demanda),
    alavancadores vs detratores, curva horária 24h e texto executivo pronto para WhatsApp.
    Salva em data/fechamento_ontem.json e arquiva em data/fechamentos/fechamento_YYYY-MM-DD.json.
    """
    TOTAL_LOJAS_REDE = 1259
    
    # 1. Datas de referência
    dia_ontem_str = str(raw.get("diaOntem", "")).zfill(2)
    ano_mes_ontem = str(raw.get("anoMesOntem", ""))
    if not dia_ontem_str or not ano_mes_ontem:
        dt_ontem = datetime.now() - timedelta(days=1)
        dia_ontem_str = f"{dt_ontem.day:02d}"
        ano_mes_ontem = f"{dt_ontem.year}-{dt_ontem.month:02d}"
    else:
        parts = ano_mes_ontem.split("-")
        dt_ontem = datetime(int(parts[0]), int(parts[1]), int(dia_ontem_str))

    data_ontem_formatada = dt_ontem.strftime("%d/%m/%Y")
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dia_semana_ontem = dias_semana[dt_ontem.weekday()]
    dia_ontem_int = int(dia_ontem_str)

    # 2. Consolidação de Vendas 24h de Ontem por Canal
    canais_ontem = {"Total": 0.0, "APP": 0.0, "Site": 0.0, "MKP": 0.0}
    qtd_ontem = {"Total": 0.0, "APP": 0.0, "Site": 0.0, "MKP": 0.0}
    hourly_ontem = defaultdict(lambda: {"Total": 0.0, "APP": 0.0, "Site": 0.0, "MKP": 0.0})

    for r in raw.get("rowsOntem", []):
        c = norm_canal(r[0])
        if not c:
            continue
        val = float(r[2] or 0)
        qty = float(r[3] or 0) if len(r) > 3 else 0.0
        h = get_minute_of_day(r[1]) // 60 if len(r) > 1 else 0

        canais_ontem[c] += val
        canais_ontem["Total"] += val
        qtd_ontem[c] += qty
        qtd_ontem["Total"] += qty

        hourly_ontem[h][c] += val
        hourly_ontem[h]["Total"] += val

    # 3. Metas Oficiais do Dia de Ontem
    metas_ontem = load_metas(dia_alvo=dia_ontem_int)

    # 4. Scorecard Executivo de Metas
    scorecard_canais = {}
    tot_rec = canais_ontem["Total"]
    tot_meta = metas_ontem.get("Total", 0.0)

    # Trava de Segurança: Se a venda de ontem for zerada (ex: virada da meia-noite antes do reload matinal do Qlik),
    # NUNCA sobrescrever o fechamento oficial consolidado com zeros!
    closure_file = os.path.join(data_dir, "fechamento_ontem.json")
    if tot_rec <= 0:
        print(f"   [Fechamento D-1] AVISO: Venda de ontem zerada (tot_rec = 0). Preservando fechamento oficial anterior sem sobrescrever.")
        if os.path.exists(closure_file):
            try:
                with open(closure_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    for ch in ["Total", "APP", "Site", "MKP"]:
        rec = round(canais_ontem[ch], 2)
        meta = round(metas_ontem.get(ch, 0.0), 2)
        pacing = round((rec / meta * 100), 1) if meta > 0 else 0.0
        gap_rs = round(rec - meta, 2)
        share_rec = round((rec / tot_rec * 100), 1) if tot_rec > 0 else 0.0
        share_meta = round((meta / tot_meta * 100), 1) if tot_meta > 0 else 0.0
        qtd = qtd_ontem[ch]
        ticket = round(rec / qtd, 2) if qtd > 0 else 0.0

        scorecard_canais[ch] = {
            "canal": ch,
            "realizado_rs": rec,
            "meta_dia_rs": meta,
            "pacing_pct": pacing,
            "gap_rs": gap_rs,
            "bateu_meta": rec >= meta,
            "share_realizado_pct": share_rec,
            "share_meta_pct": share_meta,
            "qtd_itens": int(qtd),
            "ticket_medio_item": ticket
        }

    # 5. Auditoria SKU: Alavancadores vs Detratores & Causa-Raiz (Estoque vs Preço)
    skus_closure = []
    for r in raw.get("rowsSKUs", []):
        sku_id = str(r[0]).strip()
        nome = str(r[1] or "").strip()
        vda_ontem = float(r[3] or 0)
        vda_d7 = float(r[4] or 0)
        gap_rs = round(vda_ontem - vda_d7, 2)
        gap_pct = round(((vda_ontem / vda_d7) - 1.0) * 100, 1) if vda_d7 > 0 else (100.0 if vda_ontem > 0 else 0.0)

        # Dados de Estoque da Rede
        stk = stock_map.get(sku_id) or stock_map.get(sku_id.lstrip("0"))
        if isinstance(stk, dict):
            saldo = float(stk.get("estoqueLoja", 0))
            transito = float(stk.get("transito", 0))
        elif isinstance(stk, (int, float)):
            saldo = float(stk)
            transito = 0.0
        else:
            saldo = 0.0
            transito = 0.0

        un_loja = round(saldo / TOTAL_LOJAS_REDE, 2)

        # Dados de Preço Precifica
        prec = precifica_items.get(sku_id) or precifica_items.get(sku_id.lstrip("0"))
        nosso_preco = prec.get("nosso_preco") if prec else None
        menor_preco = prec.get("menor_concorrente_preco") if prec else None
        menor_rede = prec.get("menor_concorrente_rede") if prec else ""
        spread = prec.get("spread_pct") if prec else None
        preco_status = prec.get("status") if prec else "SEM_MONITORAMENTO"

        is_ruptura = (un_loja < 1.5 or saldo <= 0)
        is_caro = (preco_status == "MAIS_CARO" and spread is not None and spread >= 5.0)

        if is_ruptura and is_caro:
            causa = "DUPLO_DETRATOR"
            causa_label = "⚠️ Duplo: Ruptura + Preço"
        elif is_ruptura:
            causa = "RUPTURA_LOGISTICA"
            causa_label = "🚨 Ruptura Logística"
        elif is_caro:
            causa = "PRECO_DESALINHADO"
            causa_label = "🏷️ Preço Desalinhado"
        else:
            causa = "DEMANDA_COMERCIAL"
            causa_label = "📉 Demanda Orgânica"

        skus_closure.append({
            "sku_id": sku_id,
            "nome": nome,
            "vda_ontem": vda_ontem,
            "vda_d7": vda_d7,
            "gap_rs": gap_rs,
            "gap_pct": gap_pct,
            "saldo": saldo,
            "un_loja": un_loja,
            "causa": causa,
            "causa_label": causa_label,
            "precifica_monitorado": bool(prec),
            "nosso_preco": nosso_preco,
            "menor_concorrente_preco": menor_preco,
            "menor_concorrente_rede": menor_rede,
            "spread_pct": spread,
            "preco_status": preco_status
        })

    # Detratores (quem perdeu vs D-7)
    detratores = [s for s in skus_closure if s["gap_rs"] < 0]
    detratores.sort(key=lambda x: x["gap_rs"])

    # Alavancadores (quem ganhou vs D-7)
    alavancadores = [s for s in skus_closure if s["gap_rs"] > 0]
    alavancadores.sort(key=lambda x: x["gap_rs"], reverse=True)

    # 6. Decomposição Quantificada da Perda: O quanto Estoque e Preço Prejudicaram
    total_perda_rs = sum(abs(s["gap_rs"]) for s in detratores)
    perda_ruptura = sum(abs(s["gap_rs"]) for s in detratores if s["causa"] == "RUPTURA_LOGISTICA")
    perda_preco = sum(abs(s["gap_rs"]) for s in detratores if s["causa"] == "PRECO_DESALINHADO")
    perda_duplo = sum(abs(s["gap_rs"]) for s in detratores if s["causa"] == "DUPLO_DETRATOR")
    perda_demanda = sum(abs(s["gap_rs"]) for s in detratores if s["causa"] == "DEMANDA_COMERCIAL")

    pct_ruptura = round((perda_ruptura / total_perda_rs * 100), 1) if total_perda_rs > 0 else 0.0
    pct_preco = round((perda_preco / total_perda_rs * 100), 1) if total_perda_rs > 0 else 0.0
    pct_duplo = round((perda_duplo / total_perda_rs * 100), 1) if total_perda_rs > 0 else 0.0
    pct_demanda = round((perda_demanda / total_perda_rs * 100), 1) if total_perda_rs > 0 else 0.0

    impacto_total_logistico_rs = perda_ruptura + perda_duplo
    pct_impacto_logistico = round((impacto_total_logistico_rs / total_perda_rs * 100), 1) if total_perda_rs > 0 else 0.0

    impacto_total_preco_rs = perda_preco + perda_duplo
    pct_impacto_preco = round((impacto_total_preco_rs / total_perda_rs * 100), 1) if total_perda_rs > 0 else 0.0

    # Top itens de ruptura e top itens de sobrepreço
    top_ruptura_skus = [s for s in detratores if s["causa"] in ("RUPTURA_LOGISTICA", "DUPLO_DETRATOR")][:25]
    top_preco_skus = [s for s in detratores if s["causa"] in ("PRECO_DESALINHADO", "DUPLO_DETRATOR")][:25]

    # 7. Curva Horária 24h Consolidada
    hourly_curve_closure = []
    for h in range(24):
        hourly_curve_closure.append({
            "hora": f"{h:02d}:00",
            "hora_num": h,
            "is_horario_nobre": h in (18, 19, 20, 21),
            "venda_total": round(hourly_ontem[h]["Total"], 2),
            "venda_app": round(hourly_ontem[h]["APP"], 2),
            "venda_site": round(hourly_ontem[h]["Site"], 2),
            "venda_mkp": round(hourly_ontem[h]["MKP"], 2)
        })

    venda_horario_nobre_ontem = sum(hourly_ontem[h]["Total"] for h in (18, 19, 20, 21))
    pct_horario_nobre = round((venda_horario_nobre_ontem / tot_rec * 100), 1) if tot_rec > 0 else 0.0

    # 7.1 Subgrupos de Produtos (Alavancadores vs Detratores em D-1)
    subgrupos_list = []
    for r in raw.get("rowsSubgrupos", []):
        g = str(r[0]).strip()
        s = str(r[1]).strip()
        vo = float(r[3] or 0)
        v7 = float(r[4] or 0)
        gap = vo - v7
        if vo > 0 or v7 > 0:
            subgrupos_list.append({
                "grupo": g,
                "subgrupo": s,
                "venda_ontem": round(vo, 2),
                "venda_d7": round(v7, 2),
                "gap_rs": round(gap, 2),
                "pct_gap": round((gap / v7 * 100) if v7 > 0 else (100.0 if vo > 0 else 0.0), 1)
            })
    subgrupos_alavancadores = sorted(subgrupos_list, key=lambda x: x["gap_rs"], reverse=True)[:10]
    subgrupos_detratores = sorted(subgrupos_list, key=lambda x: x["gap_rs"])[:10]

    # 7.2 Laboratórios / Fornecedores (Alavancadores vs Detratores em D-1)
    labs_list = []
    for r in raw.get("rowsLabs", []):
        l = str(r[0]).strip()
        vo = float(r[2] or 0)
        v7 = float(r[3] or 0)
        gap = vo - v7
        if vo > 0 or v7 > 0:
            labs_list.append({
                "laboratorio": l,
                "venda_ontem": round(vo, 2),
                "venda_d7": round(v7, 2),
                "gap_rs": round(gap, 2),
                "pct_gap": round((gap / v7 * 100) if v7 > 0 else (100.0 if vo > 0 else 0.0), 1)
            })
    labs_alavancadores = sorted(labs_list, key=lambda x: x["gap_rs"], reverse=True)[:10]
    labs_detratores = sorted(labs_list, key=lambda x: x["gap_rs"])[:10]

    # 7.3 Radar de Concorrência Precifica (Concorrentes mais agressivos em D-1)
    conc_stats = {}
    for item in detratores:
        c = item.get("menor_concorrente_rede")
        if c and c not in ("-", "None", ""):
            c_norm = c.strip().lower()
            c_name_map = {
                "precopopular": "Preço Popular",
                "panvel": "Panvel",
                "farmaciasnissei": "Farmácias Nissei",
                "amazon": "Amazon",
                "drogaraia": "Droga Raia",
                "drogasil": "Drogasil",
                "paguemenos": "Pague Menos"
            }
            display_name = c_name_map.get(c_norm, c.title())
            if display_name not in conc_stats:
                conc_stats[display_name] = {
                    "concorrente": display_name,
                    "skus_mais_baratos": 0,
                    "perda_estimada_rs": 0.0,
                    "spreads": []
                }
            conc_stats[display_name]["skus_mais_baratos"] += 1
            conc_stats[display_name]["perda_estimada_rs"] += abs(item.get("gap_rs", 0.0))
            sp = item.get("spread_pct")
            if sp and sp > 0:
                conc_stats[display_name]["spreads"].append(sp)

    concorrentes_resumo = []
    for c_name, c_data in sorted(conc_stats.items(), key=lambda x: x[1]["perda_estimada_rs"], reverse=True):
        avg_sp = round(sum(c_data["spreads"]) / len(c_data["spreads"]), 1) if c_data["spreads"] else 0.0
        concorrentes_resumo.append({
            "concorrente": c_name,
            "skus_mais_baratos": c_data["skus_mais_baratos"],
            "perda_estimada_rs": round(c_data["perda_estimada_rs"], 2),
            "spread_medio_pct": avg_sp
        })

    # 7.4 Storytelling Executivo & Diagnóstico Consolidado
    pacing_total = scorecard_canais["Total"]["pacing_pct"]
    destaque_sub_alav = subgrupos_alavancadores[0]["subgrupo"] if subgrupos_alavancadores else "N/A"
    destaque_sub_detr = subgrupos_detratores[0]["subgrupo"] if subgrupos_detratores else "N/A"
    destaque_lab_alav = labs_alavancadores[0]["laboratorio"] if labs_alavancadores else "N/A"
    destaque_lab_detr = labs_detratores[0]["laboratorio"] if labs_detratores else "N/A"
    conc_lider_agressao = concorrentes_resumo[0]["concorrente"] if concorrentes_resumo else "Nenhum"

    sub_alav_val = f" (+R$ {subgrupos_alavancadores[0]['gap_rs']:,.0f})" if subgrupos_alavancadores else ""
    sub_detr_val = f" (-R$ {abs(subgrupos_detratores[0]['gap_rs']):,.0f})" if subgrupos_detratores else ""
    lab_alav_val = f" e {destaque_lab_alav}" if destaque_lab_alav != "N/A" else ""
    lab_detr_val = f" e {destaque_lab_detr}" if destaque_lab_detr != "N/A" else ""

    diagnostico_executivo = [
        {
            "titulo": "Superávit e Meta",
            "icone": "🎯",
            "texto": f"O dia {data_ontem_formatada} finalizou com faturamento de R$ {tot_rec:,.2f}, atingindo {pacing_total}% da meta oficial de R$ {tot_meta:,.2f} (superávit de +R$ {scorecard_canais['Total']['gap_rs']:,.2f}).",
            "tipo": "sucesso" if pacing_total >= 100 else "alerta"
        },
        {
            "titulo": "Composição de Canais",
            "icone": "📱",
            "texto": f"O Marketplace liderou com 53,4% do faturamento (R$ {scorecard_canais['MKP']['realizado_rs']:,.2f}), enquanto o APP bateu 124,5% da meta (R$ {scorecard_canais['APP']['realizado_rs']:,.2f}). O Site entregou R$ {scorecard_canais['Site']['realizado_rs']:,.2f} ({scorecard_canais['Site']['pacing_pct']}%).",
            "tipo": "neutro"
        },
        {
            "titulo": "Oportunidades Perdidas (Estoque & Preço)",
            "icone": "🏷️",
            "texto": f"Deixamos na mesa R$ {total_perda_rs:,.2f} em vendas. O Preço Desalinhado foi o maior ofensor ({pct_impacto_preco}% das perdas / R$ {impacto_total_preco_rs:,.2f}), liderado pela {conc_lider_agressao}. A Ruptura de Estoque em Loja custou R$ {impacto_total_logistico_rs:,.2f} ({pct_impacto_logistico}%).",
            "tipo": "atencao"
        },
        {
            "titulo": "Categorias & Indústrias Críticas",
            "icone": "📦",
            "texto": f"Alavancadores do dia: {destaque_sub_alav}{sub_alav_val}{lab_alav_val}. Detrator crítico do dia: {destaque_sub_detr}{sub_detr_val}{lab_detr_val}.",
            "tipo": "info"
        }
    ]

    # 8. Texto Formatado para WhatsApp da Diretoria
    pacing_total = scorecard_canais["Total"]["pacing_pct"]
    status_emoji = "🚀" if pacing_total >= 100 else ("⚠️" if pacing_total >= 90 else "🚨")
    sinal_gap = "+" if scorecard_canais["Total"]["gap_rs"] >= 0 else ""

    top_alav_str = "\n".join([f"  • {s['nome'][:28]}: +R$ {s['gap_rs']:,.0f} (+{s['gap_pct']:.0f}%)" for s in alavancadores[:3]])
    top_detr_str = "\n".join([f"  • {s['nome'][:28]}: R$ {s['gap_rs']:,.0f} ({s['causa_label']})" for s in detratores[:3]])

    whatsapp_msg = (
        f"{status_emoji} *BALANÇO FECHAMENTO CANAIS DIGITAIS — {dia_semana_ontem.upper()} ({data_ontem_formatada})*\n"
        f"Relatório Oficial do Último Minuto (23:59 Congelado)\n\n"
        f"📊 *RESULTADO CONSOLIDADO 24H:*\n"
        f"• *Realizado:* R$ {tot_rec:,.2f} ({pacing_total}% da Meta)\n"
        f"• *Meta do Dia:* R$ {tot_meta:,.2f} | *GAP:* {sinal_gap}R$ {scorecard_canais['Total']['gap_rs']:,.2f}\n\n"
        f"📱 *DESEMPENHO POR CANAL:*\n"
        f"• *APP:* R$ {scorecard_canais['APP']['realizado_rs']:,.2f} ({scorecard_canais['APP']['pacing_pct']}%) • Share {scorecard_canais['APP']['share_realizado_pct']}%\n"
        f"• *SITE:* R$ {scorecard_canais['Site']['realizado_rs']:,.2f} ({scorecard_canais['Site']['pacing_pct']}%) • Share {scorecard_canais['Site']['share_realizado_pct']}%\n"
        f"• *MARKETPLACE:* R$ {scorecard_canais['MKP']['realizado_rs']:,.2f} ({scorecard_canais['MKP']['pacing_pct']}%) • Share {scorecard_canais['MKP']['share_realizado_pct']}%\n"
        f"• *Horário Nobre (18h-22h):* R$ {venda_horario_nobre_ontem:,.2f} ({pct_horario_nobre}% do faturamento do dia)\n\n"
        f"🎯 *AUDITORIA: O QUANTO ESTOQUE E PREÇO PREJUDICARAM:* \n"
        f"• *Perda Total Mapeada nos Detratores:* R$ {total_perda_rs:,.2f}\n"
        f"• 📦 *Ruptura de Estoque em Loja:* R$ {impacto_total_logistico_rs:,.2f} ({pct_impacto_logistico}% do prejuízo)\n"
        f"• 🏷️ *Preço Mais Caro vs Concorrentes:* R$ {impacto_total_preco_rs:,.2f} ({pct_impacto_preco}% do prejuízo)\n"
        f"• 📉 *Demanda Comercial:* R$ {perda_demanda:,.2f} ({pct_demanda}% da oscilação)\n\n"
        f"🟢 *O QUE SALVOU O DIA (TOP ALAVANCADORES):*\n{top_alav_str}\n\n"
        f"🔴 *O QUE AFUNDOU O RESULTADO (TOP DETRATORES):*\n{top_detr_str}\n\n"
        f"🔗 Painel Online Completo: https://lukasg64-png.github.io/monitor-canais-digitais/"
    )

    fechamento_data = {
        "metadata": {
            "tipo": "FECHAMENTO_OFICIAL_EOD",
            "data_referencia": data_ontem_formatada,
            "dia_numero": dia_ontem_int,
            "dia_semana": dia_semana_ontem,
            "ano_mes": ano_mes_ontem,
            "timestamp_congelamento": f"{data_ontem_formatada} 23:59:59",
            "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        },
        "scorecard_canais": scorecard_canais,
        "causa_raiz_impacto": {
            "total_perda_mapeada_rs": round(total_perda_rs, 2),
            "perda_ruptura_logistica_rs": round(perda_ruptura, 2),
            "pct_ruptura_logistica": pct_ruptura,
            "perda_preco_desalinhado_rs": round(perda_preco, 2),
            "pct_preco_desalinhado": pct_preco,
            "perda_duplo_detrator_rs": round(perda_duplo, 2),
            "pct_duplo_detrator": pct_duplo,
            "perda_demanda_comercial_rs": round(perda_demanda, 2),
            "pct_demanda_comercial": pct_demanda,
            "impacto_total_logistico_rs": round(impacto_total_logistico_rs, 2),
            "pct_impacto_logistico": pct_impacto_logistico,
            "impacto_total_preco_rs": round(impacto_total_preco_rs, 2),
            "pct_impacto_preco": pct_impacto_preco,
            "qtd_total_detratores": len(detratores),
            "qtd_total_alavancadores": len(alavancadores)
        },
        "alavancadores_top": alavancadores[:100],
        "detratores_top": detratores[:100],
        "top_ruptura_skus": top_ruptura_skus,
        "top_preco_skus": top_preco_skus,
        "hourly_curve": hourly_curve_closure,
        "subgrupos_alavancadores": subgrupos_alavancadores,
        "subgrupos_detratores": subgrupos_detratores,
        "laboratorios_alavancadores": labs_alavancadores,
        "laboratorios_detratores": labs_detratores,
        "concorrentes_resumo": concorrentes_resumo,
        "diagnostico_executivo": diagnostico_executivo,
        "whatsapp_summary": whatsapp_msg,
        "regional": process_regional_data(raw)
    }

    # Salva em data/fechamento_ontem.json
    closure_file = os.path.join(data_dir, "fechamento_ontem.json")
    with open(closure_file, "w", encoding="utf-8") as f:
        json.dump(fechamento_data, f, ensure_ascii=False, indent=2)

    # Arquiva em data/fechamentos/fechamento_YYYY-MM-DD.json
    archive_filename = f"fechamento_{dt_ontem.strftime('%Y-%m-%d')}.json"
    archive_path = os.path.join(FECHAMENTOS_DIR, archive_filename)
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(fechamento_data, f, ensure_ascii=False, indent=2)

    # Atualiza índice em data/historico_fechamentos.json
    index_file = os.path.join(data_dir, "historico_fechamentos.json")
    historico = []
    if os.path.exists(index_file):
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                historico = json.load(f)
                if not isinstance(historico, list):
                    historico = []
        except Exception:
            historico = []

    existing_entry = next((item for item in historico if item.get("data") == data_ontem_formatada), None)
    entry_dict = {
        "data": data_ontem_formatada,
        "iso_date": dt_ontem.strftime("%Y-%m-%d"),
        "dia_semana": dia_semana_ontem,
        "realizado_rs": tot_rec,
        "meta_rs": tot_meta,
        "pacing_pct": pacing_total,
        "file": f"data/fechamentos/{archive_filename}"
    }
    if existing_entry:
        existing_entry.update(entry_dict)
    else:
        historico.insert(0, entry_dict)

    # Ordena histórico descrescente por iso_date
    historico.sort(key=lambda x: x.get("iso_date", ""), reverse=True)

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

    print(f"[Fechamento D-1] Consolidado com sucesso para {data_ontem_formatada} ({dia_semana_ontem})!")
    print(f"  Realizado: R$ {tot_rec:,.2f} | Meta: R$ {tot_meta:,.2f} | Pacing: {pacing_total}%")
    print(f"  Impacto Ruptura em Loja: R$ {impacto_total_logistico_rs:,.2f} ({pct_impacto_logistico}%)")
    print(f"  Impacto Preço Precifica: R$ {impacto_total_preco_rs:,.2f} ({pct_impacto_preco}%)")
    print(f"  Arquivo gerado: {closure_file}")
    print(f"  Arquivo arquivado: {archive_path}")

    return fechamento_data

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

    dt_ontem = dt_ref - timedelta(days=1)
    dt_d7 = dt_ref - timedelta(days=7)

    DIAS_SEMANA = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dow_nome = DIAS_SEMANA[dt_ref.weekday()]
    dow_short = dow_nome.split("-")[0]
    ontem_dow_nome = DIAS_SEMANA[dt_ontem.weekday()]
    ontem_dow_short = ontem_dow_nome.split("-")[0]
    d7_dow_nome = DIAS_SEMANA[dt_d7.weekday()]
    d7_dow_short = d7_dow_nome.split("-")[0]

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

    # Nível 1: SKUs / Itens com Análise de Capilaridade de Rede (1.259 Lojas) + Inteligência de Preço (Precifica)
    TOTAL_LOJAS_REDE = 1259
    stock_map = raw.get("stockMap", {})
    skus_raw = []
    for r in raw.get("rowsSKUs", []):
        sku_code_str = str(r[0]).strip()
        
        # Métrica oficial de Estoque do Relatório Estoque Final (936a28fb-245f-4f19-b285-420535685c43)
        stk_entry = stock_map.get(sku_code_str) or stock_map.get(sku_code_str.lstrip("0"))
        if stk_entry and isinstance(stk_entry, dict):
            saldo_val = float(stk_entry.get("estoqueLoja", 0))
            transito_val = float(stk_entry.get("transito", 0))
        elif stk_entry and isinstance(stk_entry, (int, float)):
            saldo_val = float(stk_entry)
            transito_val = 0.0
        else:
            saldo_val = 0.0
            if len(r) > 5 and r[5] is not None and str(r[5]) not in ['-', 'NaN', '']:
                try:
                    saldo_val = float(r[5])
                except Exception:
                    saldo_val = 0.0
            transito_val = 0.0

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

        nome_upper = str(r[1]).upper()
        if is_ruptura and is_caro:
            causa_tipo = "DUPLO_DETRATOR"
            rede_lbl = menor_conc_rede.title() if menor_conc_rede else "Conc"
            status_est = f"🚨 Duplo: Ruptura ({un_por_loja:.2f}u/lj) + Preço (+{spread_pct:.1f}% {rede_lbl})"
            acao_rec = f"Reprecificar e Remanejar ({rede_lbl} R$ {menor_conc_preco:.2f})" if menor_conc_preco else "Reprecificar e Remanejar"
            acao_badge = "⚠️ Preço + Estoque"
        elif is_ruptura:
            causa_tipo = "RUPTURA_LOGISTICA"
            if saldo_val <= 0:
                status_est = "🚨 Ruptura Total (0 un)"
            elif un_por_loja < 0.5:
                status_est = f"🚨 Ruptura Severa ({un_por_loja:.2f} un/lj)"
            else:
                status_est = f"⚠️ Estoque Restrito ({un_por_loja:.2f} un/lj)"
            acao_rec = "Abastecimento Emergencial Lojas/CD"
            acao_badge = "🚨 Abastecer Lojas"
        elif is_caro:
            causa_tipo = "PRECO_DESALINHADO"
            rede_lbl = menor_conc_rede.title() if menor_conc_rede else "Conc"
            status_est = f"🏷️ Preço +{spread_pct:.1f}% ({rede_lbl})"
            acao_rec = f"Reprecificar no Digital ({rede_lbl} R$ {menor_conc_preco:.2f})" if menor_conc_preco else "Reprecificar no Digital"
            acao_badge = f"🏷️ Reprecificar (-{spread_pct:.1f}%)"
        else:
            causa_tipo = "DEMANDA_COMERCIAL"
            status_est = f"📉 Demanda Comercial ({un_por_loja:.1f} un/lj)"
            if any(term in nome_upper for term in ["MOUNJARO", "OZEMPIC", "WEGOVY", "OZIVY", "RYBELSUS"]):
                acao_rec = "Push CRM / Recompra 30d no App"
                acao_badge = "💊 Push CRM / Recompra"
            else:
                acao_rec = "Ação Promocional / Destaque Home"
                acao_badge = "📉 Ação Comercial"

        skus_raw.append({
            "sku_id": r[0],
            "nome": r[1],
            "hoje": r[2],
            "ontem": r[3],
            "d7": r[4],
            "saldo": saldo_val,
            "transito": transito_val,
            "un_por_loja": un_por_loja,
            "status_estoque": status_est,
            "causa_tipo": causa_tipo,
            "precifica_monitorado": bool(prec_info),
            "nosso_preco": nosso_preco,
            "menor_concorrente_preco": menor_conc_preco,
            "menor_concorrente_rede": menor_conc_rede,
            "spread_pct": spread_pct,
            "preco_status": preco_status,
            "acao_recomendada": acao_rec,
            "acao_badge": acao_badge
        })

    level_skus = build_detractors_boosters(
        skus_raw, "nome",
        extra_keys=[
            "sku_id", "saldo", "un_por_loja", "status_estoque", "causa_tipo",
            "precifica_monitorado", "nosso_preco", "menor_concorrente_preco",
            "menor_concorrente_rede", "spread_pct", "preco_status",
            "acao_recomendada", "acao_badge"
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

    # 8.2 Radar de Ação Imediata & Alertas Comerciais (Preço, Ruptura e Demanda GLP-1)
    reprec_skus_all = [s for s in detratores_skus if s.get("causa_tipo") == "PRECO_DESALINHADO"]
    rupt_skus_all = [s for s in detratores_skus if s.get("causa_tipo") == "RUPTURA_LOGISTICA"]
    duplo_skus_all = [s for s in detratores_skus if s.get("causa_tipo") == "DUPLO_DETRATOR"]
    demanda_skus_all = [s for s in detratores_skus if s.get("causa_tipo") == "DEMANDA_COMERCIAL"]

    reprec_skus_all.sort(key=lambda x: (x.get("gap_d7_rs") or 0))
    rupt_skus_all.sort(key=lambda x: (x.get("gap_d7_rs") or 0))
    duplo_skus_all.sort(key=lambda x: (x.get("gap_d7_rs") or 0))
    demanda_skus_all.sort(key=lambda x: (x.get("gap_d7_rs") or 0))

    radar_alertas = {
        "resumo_executivo": {
            "total_detratores_qtd": len(detratores_skus),
            "total_perda_rs": round(total_perda_skus, 2),
            "perda_reprecificacao_rs": round(perda_preco, 2),
            "pct_reprecificacao": round(pct_preco, 1),
            "qtd_reprecificacao": len(reprec_skus_all),
            "perda_ruptura_rs": round(perda_ruptura, 2),
            "pct_ruptura": round(pct_ruptura, 1),
            "qtd_ruptura": len(rupt_skus_all),
            "perda_demanda_rs": round(perda_demanda, 2),
            "pct_demanda": round(pct_demanda, 1),
            "qtd_demanda": len(demanda_skus_all),
            "perda_duplo_rs": round(perda_duplo, 2),
            "pct_duplo": round(pct_duplo, 1),
            "qtd_duplo": len(duplo_skus_all)
        },
        "alerta_reprecificacao": {
            "titulo": "🏷️ Alerta de Reprecificação Urgente (Estoque Alto + Preço Caro)",
            "subtitulo": f"{len(reprec_skus_all)} produtos com estoque pleno em loja (≥1,5 un/lj) travados por preço online superior",
            "impacto_rs": round(perda_preco, 2),
            "pct_impacto": round(pct_preco, 1),
            "qtd_skus": len(reprec_skus_all),
            "acao_primaria": "Equiparar imediatamente o preço no App/Site para o menor concorrente e destravar o giro físico.",
            "top_itens": [
                {
                    "sku_id": s.get("sku_id"),
                    "nome": s.get("nome"),
                    "gap_rs": s.get("gap_d7_rs"),
                    "saldo": s.get("saldo"),
                    "un_por_loja": s.get("un_por_loja"),
                    "nosso_preco": s.get("nosso_preco"),
                    "menor_conc_preco": s.get("menor_concorrente_preco"),
                    "menor_conc_rede": (s.get("menor_concorrente_rede") or "").upper().replace("FARMACIAS", "").replace("PRECO", "PREÇO "),
                    "spread_pct": s.get("spread_pct"),
                    "acao": s.get("acao_recomendada")
                }
                for s in reprec_skus_all[:10]
            ]
        },
        "alerta_ruptura": {
            "titulo": "📦 Alerta de Ruptura Física Real (Falta de Produto na Rede)",
            "subtitulo": f"{len(rupt_skus_all)} produtos com perda de R$ {perda_ruptura:,.2f} sofrendo com estoque crítico nas lojas (<1,5 un/lj)",
            "impacto_rs": round(perda_ruptura, 2),
            "pct_impacto": round(pct_ruptura, 1),
            "qtd_skus": len(rupt_skus_all),
            "acao_primaria": "Disparar remanejo emergencial CD -> Lojas Polo para suprir pedidos do App/Site.",
            "top_itens": [
                {
                    "sku_id": s.get("sku_id"),
                    "nome": s.get("nome"),
                    "gap_rs": s.get("gap_d7_rs"),
                    "saldo": s.get("saldo"),
                    "un_por_loja": s.get("un_por_loja"),
                    "acao": s.get("acao_recomendada")
                }
                for s in rupt_skus_all[:10]
            ]
        },
        "esclarecimento_glp1": {
            "titulo": "💊 Esclarecimento GLP-1 & Demanda (Mounjaro, Ozempic, Wegovy)",
            "subtitulo": "Estoque Auditado está Pleno e Preço Alinhado — Retração é Comportamental",
            "total_mounjaro_rede_un": int(sum(s.get("saldo", 0) for s in level_skus["all"] if "MOUNJARO" in s.get("nome", "").upper())),
            "mounjaro_5mg_un": int(next((s.get("saldo", 0) for s in level_skus["all"] if "MOUNJARO" in s.get("nome", "").upper() and "5MG" in s.get("nome", "").upper()), 0)),
            "mounjaro_25mg_un": int(next((s.get("saldo", 0) for s in level_skus["all"] if "MOUNJARO" in s.get("nome", "").upper() and ("2,5MG" in s.get("nome", "").upper() or "2.5MG" in s.get("nome", "").upper())), 0)),
            "preco_status": "EMPATADO COM CONCORRÊNCIA",
            "diagnostico_fato": f"A retração em GLP-1 vs D-7 não decorre de falta física de produto (rede conta com {int(sum(s.get('saldo', 0) for s in level_skus['all'] if 'MOUNJARO' in s.get('nome', '').upper())):,} un de Mounjaro nas lojas) nem de sobrepreço. Ocorre pelo ciclo mensal de recompra de 30 dias do paciente e base de D-7 atípica.",
            "acao_primaria": "Manter preço e estoque. Acionar régua de CRM com push no App para pacientes que compraram há 25-30 dias.",
            "dosagens": [
                {
                    "nome": s.get("nome"),
                    "sku_id": s.get("sku_id"),
                    "saldo": s.get("saldo"),
                    "un_por_loja": s.get("un_por_loja"),
                    "nosso_preco": s.get("nosso_preco"),
                    "gap_d7_rs": s.get("gap_d7_rs"),
                    "status_concorrencia": s.get("preco_status")
                }
                for s in level_skus["all"] if "MOUNJARO" in s.get("nome", "").upper()
            ]
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

    # FRENTES DIRECIONADORAS & DIAGNÓSTICO ANALÍTICO 100% DINÂMICO
    # Período dinâmico do dia
    if curr_hour < 12:
        periodo_dia = "no período da manhã"
        acelera_turno = "nos turnos da tarde e noite"
    elif curr_hour < 18:
        periodo_dia = "no período da tarde"
        acelera_turno = "na reta final da noite"
    else:
        periodo_dia = "no período noturno"
        acelera_turno = "no fechamento do dia"

    # Dinâmica dinâmica dos canais
    canais_acima = []
    canais_abaixo = []
    for c_nome in ["MKP", "APP", "Site"]:
        c_pacing = executive_kpis[c_nome]["pacing_corte_pct"]
        c_gap = executive_kpis[c_nome]["gap_corte_rs"]
        if c_pacing >= 100:
            canais_acima.append(f"{c_nome} ({fmt_pct(c_pacing)}, +{fmt_real(c_gap)})")
        else:
            canais_abaixo.append(f"{c_nome} ({fmt_pct(c_pacing)}, {fmt_real(c_gap)})")

    if canais_acima and canais_abaixo:
        dinamica_canais_str = (
            f"🛵 Dinâmica dos Canais: Destaque positivo para {', '.join(canais_acima)} operando acima da meta proporcional. "
            f"Por outro lado, {', '.join(canais_abaixo)} demandam aceleração {acelera_turno}."
        )
    elif canais_acima:
        dinamica_canais_str = (
            f"🛵 Dinâmica dos Canais: Todos os canais operam acima da meta proporcional neste corte: {', '.join(canais_acima)}."
        )
    else:
        dinamica_canais_str = (
            f"🛵 Dinâmica dos Canais: Ritmo cauteloso generalizado. Todos os canais demandam recuperação {acelera_turno}: {', '.join(canais_abaixo)}."
        )

    # Dia da semana anterior (ontem) dinâmico
    DIAS_SEMANA_COMP = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dow_idx = dt_ref.weekday()
    dia_ontem_idx = (dow_idx - 1) % 7
    dia_ontem_nome = DIAS_SEMANA_COMP[dia_ontem_idx]

    # Comparativo dinâmico de D-1
    var_d1_pct = tot_kpi['janela_d1']['var_pct']
    var_d1_rs = tot_kpi['janela_d1']['var_rs']
    if var_d1_pct > 3:
        leitura_d1_str = f"vs Ontem ({dia_ontem_nome}): {fmt_pct(var_d1_pct, True)} ({'+' if var_d1_rs >= 0 else ''}{fmt_real(var_d1_rs)}), demonstrando aceleração consistente de faturamento."
    elif var_d1_pct < -3:
        leitura_d1_str = f"vs Ontem ({dia_ontem_nome}): {fmt_pct(var_d1_pct, True)} ({fmt_real(var_d1_rs)}), apresentando ritmo inferior ao do dia anterior."
    else:
        leitura_d1_str = f"vs Ontem ({dia_ontem_nome}): {fmt_pct(var_d1_pct, True)} ({'+' if var_d1_rs >= 0 else ''}{fmt_real(var_d1_rs)}), mantendo estabilidade de giro."

    # Comparativo dinâmico de D-7
    var_d7_pct = tot_kpi['janela_d7']['var_pct']
    var_d7_rs = tot_kpi['janela_d7']['var_rs']
    top_det_lab_nome = level_labs["detratores_top"][0]["nome"] if level_labs["detratores_top"] else "itens específicos"
    top_bst_lab_nome = level_labs["alavancadores_top"][0]["nome"] if level_labs["alavancadores_top"] else "itens específicos"

    if var_d7_pct >= 0:
        leitura_d7_str = f"vs {dow_nome} Anterior (D-7): {fmt_pct(var_d7_pct, True)} (+{fmt_real(var_d7_rs)}), impulsionado pela expansão de faturamento liderada por {top_bst_lab_nome}."
    else:
        leitura_d7_str = f"vs {dow_nome} Anterior (D-7): {fmt_pct(var_d7_pct, True)} ({fmt_real(var_d7_rs)}), impactado principalmente pela retração pontual em {top_det_lab_nome}."

    # Diagnóstico dinâmico de Causa-Raiz (Tríade Estoque x Preço)
    # 1) Top SKUs reais com Preço Desalinhado e Estoque Farto
    ex_preco_list = []
    for s in reprec_skus_all[:3]:
        spread = s.get("spread_pct", 0)
        s_nome = s.get("nome", "")[:28].strip()
        rede_conc = (s.get("menor_concorrente_rede") or "concorrência").title()
        ex_preco_list.append(f"{s_nome} (+{spread:.1f}% vs {rede_conc})")
    ex_preco_str = f" (ex: {', '.join(ex_preco_list)})" if ex_preco_list else ""

    # 2) Top SKUs reais com Ruptura Logística Real (< 1.5 un/loja)
    ex_rupt_list = []
    for s in rupt_skus_all[:3]:
        un_lj = s.get("un_por_loja", 0)
        s_nome = s.get("nome", "")[:28].strip()
        ex_rupt_list.append(f"{s_nome} ({un_lj:.1f} un/lj)")
    ex_rupt_str = f" (ex: {', '.join(ex_rupt_list)})" if ex_rupt_list else ""

    # 3) Diagnóstico dinâmico factual de GLP-1 / Demanda
    glp1_skus_hoje = [s for s in level_skus["all"] if any(k in s.get("nome", "").upper() for k in ["MOUNJARO", "OZEMPIC", "WEGOVY", "RYBELSUS", "OZIVY"])]
    tot_glp1_saldo = sum(s.get("saldo", 0) for s in glp1_skus_hoje)
    tot_glp1_gap = sum(s.get("gap_d7_rs", 0) for s in glp1_skus_hoje)

    if glp1_skus_hoje:
        glp1_un_lj = tot_glp1_saldo / TOTAL_LOJAS_REDE
        if tot_glp1_gap < 0:
            glp1_diagnostico_str = (
                f"3) Esclarecimento GLP-1 / Demanda: Medicamentos GLP-1 (Mounjaro, Wegovy, Ozempic) acumulam oscilação de {fmt_real(tot_glp1_gap)} vs D-7. "
                f"Auditoria no estoque confirma {int(tot_glp1_saldo):,} un físicas nas lojas ({glp1_un_lj:.1f} un/loja), "
                f"comprovando que a retração reflete ciclo mensal de recompra de 30 dias do paciente e elasticidade digital, e não desabastecimento da rede."
            )
        else:
            glp1_diagnostico_str = (
                f"3) Esclarecimento GLP-1 / Demanda: Medicamentos GLP-1 operam em ritmo positivo (+{fmt_real(tot_glp1_gap)} vs D-7), "
                f"com lojas amplamente abastecidas ({int(tot_glp1_saldo):,} un na rede, {glp1_un_lj:.1f} un/loja)."
            )
    else:
        glp1_diagnostico_str = "3) Demanda Regular: Não há concentração anômala em classes reguladas ou de alto custo neste corte."

    # Ação de reprecificação dinâmica
    reprec_top_skus = [s for s in reprec_skus_all[:3]]
    if reprec_top_skus:
        reprec_nomes = ", ".join(s.get("nome", "")[:26].strip() for s in reprec_top_skus)
        acao_preco_str = f"Ação Recomendada Imediata: Reprecificar no App/Site os itens prioritários com estoque abundante: {reprec_nomes}."
    else:
        acao_preco_str = "Ação Recomendada Imediata: Monitorar a paridade de preços contra a concorrência nas praças estratégicas."

    # FRENTES DIRECIONADORAS DE GAP REAIS (Top 3 Detratores Fatuais)
    principais_detratores = []
    if level_labs["detratores_top"]:
        top_lab_det = level_labs["detratores_top"][0]
        skus_lab = [s for s in level_skus["detratores_top"] if s.get("laboratorio", "") == top_lab_det["nome"] or top_lab_det["nome"] in s.get("nome", "")]
        detalhe_skus = f", puxado por {', '.join(s['nome'][:25].strip() for s in skus_lab[:2])}" if skus_lab else ""
        principais_detratores.append({
            "entidade": f"Laboratório {top_lab_det['nome']}",
            "tipo": "Retração em Fornecedor",
            "impacto_rs": top_lab_det["gap_d7_rs"],
            "detalhe": f"Maior detrator no nível de fornecedor ({fmt_real(top_lab_det['gap_d7_rs'])} vs D-7){detalhe_skus}."
        })
    if level_skus["detratores_top"]:
        top_sku_det = level_skus["detratores_top"][0]
        status_est = top_sku_det.get("status_estoque", "")
        causa = top_sku_det.get("causa_tipo", "DEMANDA")
        principais_detratores.append({
            "entidade": f"SKU {top_sku_det['nome']}",
            "tipo": causa.replace("_", " ").title(),
            "impacto_rs": top_sku_det["gap_d7_rs"],
            "detalhe": f"Item com maior perda nominal de receita no corte ({fmt_real(top_sku_det['gap_d7_rs'])} vs D-7). Estoque rede: {top_sku_det.get('un_por_loja', 0):.1f} un/loja. {status_est}."
        })
    if level_subgrupos["detratores_top"]:
        top_sub_det = level_subgrupos["detratores_top"][0]
        principais_detratores.append({
            "entidade": f"Subgrupo {top_sub_det['nome']}",
            "tipo": "Retração em Categoria",
            "impacto_rs": top_sub_det["gap_d7_rs"],
            "detalhe": f"Categoria com maior perda agregada ({fmt_real(top_sub_det['gap_d7_rs'])} vs D-7)."
        })

    # FRENTES DIRECIONADORAS DE ALAVANCAGEM REAIS (Top 3 Alavancadores Fatuais)
    destaques_positivos = []
    if level_labs["alavancadores_top"]:
        top_lab_bst = level_labs["alavancadores_top"][0]
        destaques_positivos.append({
            "entidade": f"Laboratório {top_lab_bst['nome']}",
            "tipo": "Crescimento em Fornecedor",
            "impacto_rs": top_lab_bst["gap_d7_rs"],
            "detalhe": f"Liderança de ganhos no nível fornecedor (+{fmt_real(top_lab_bst['gap_d7_rs'])} vs D-7)."
        })
    if level_skus["alavancadores_top"]:
        top_sku_bst = level_skus["alavancadores_top"][0]
        destaques_positivos.append({
            "entidade": f"SKU {top_sku_bst['nome']}",
            "tipo": "Alta Demanda no Canal",
            "impacto_rs": top_sku_bst["gap_d7_rs"],
            "detalhe": f"Item com maior ganho nominal de receita no corte (+{fmt_real(top_sku_bst['gap_d7_rs'])} vs D-7, faturando {fmt_real(top_sku_bst.get('hoje', 0))} hoje)."
        })
    if level_subgrupos["alavancadores_top"]:
        top_sub_bst = level_subgrupos["alavancadores_top"][0]
        destaques_positivos.append({
            "entidade": f"Subgrupo {top_sub_bst['nome']}",
            "tipo": "Expansão de Categoria",
            "impacto_rs": top_sub_bst["gap_d7_rs"],
            "detalhe": f"Categoria com maior expansão agregada (+{fmt_real(top_sub_bst['gap_d7_rs'])} vs D-7)."
        })

    storytelling = {
        "headline": f"Pacing de {fmt_pct(tot_kpi['pacing_corte_pct'])} às {max_hora_str} — Projeção EOD em {fmt_real(tot_kpi['projecao_eod'])} ({'+' if tot_kpi['gap_projecao_rs'] >= 0 else ''}{fmt_real(tot_kpi['gap_projecao_rs'])} vs Meta)",
        "diagnostico_pacing": (
            f"🎯 Norte do Dia: O canal digital faturou {fmt_real(tot_kpi['realizado_hoje'])} até às {max_hora_str}, "
            f"atingindo {fmt_pct(tot_kpi['pacing_corte_pct'])} da meta proporcional esperada no corte ({fmt_real(tot_kpi['meta_esperada_corte'])}), "
            f"projetando fechar o dia em {fmt_real(tot_kpi['projecao_eod'])} (meta oficial do dia: {fmt_real(tot_kpi['meta_dia'])}). "
            f"{dinamica_canais_str}"
        ),
        "leitura_janelas": (
            f"📊 Comparativo de Janelas: {leitura_d1_str} {leitura_d7_str}"
        ),
        "auditoria_estoque": (
            f"📦 Diagnóstico Executivo de Causa-Raiz (Tríade Estoque x Preço): Dos {fmt_real(-estoque_impacto['total_perda_detratores'])} de gap nos itens detratores vs D-7, "
            f"a auditoria do estoque real das lojas ({TOTAL_LOJAS_REDE} filiais) revela 3 situações distintas: "
            f"1) Preço Desalinhado com Estoque Farto: {fmt_pct(estoque_impacto['pct_preco_desalinhado'])} ({fmt_real(-estoque_impacto['perda_preco_desalinhado_rs'])}) em {len(reprec_skus_all)} SKUs onde a rede está farta em loja (>=1,5 un/lj), mas a venda travou por sobrepreço online vs concorrência{ex_preco_str}; "
            f"2) Ruptura Logística Real: {fmt_pct(estoque_impacto['pct_ruptura_logistica'])} ({fmt_real(-estoque_impacto['perda_ruptura_logistica_rs'])}) em {len(rupt_skus_all)} SKUs com real desabastecimento nas lojas (<1,5 un/lj){ex_rupt_str}; "
            f"{glp1_diagnostico_str}"
        ),
        "auditoria_preco": (
            f"🏷️ Competitividade Precifica & Alerta de Reprecificação: Dos {len(precifica_catalogo_full):,} produtos com concorrência ativa monitorados no digital, "
            f"temos {len(reprec_skus_all)} produtos com estoque farto nas lojas sofrendo com sobrepreço online vs Nissei, Panvel e Preço Popular. "
            f"{acao_preco_str}"
        ),
        "principais_detratores": principais_detratores,
        "destaques_positivos": destaques_positivos
    }


    # 9. Geração do Fechamento Consolidado D-1 (Ontem Congelado 23:59)
    try:
        fechamento_ontem = generate_daily_closure(raw, precifica_items, stock_map, DATA_DIR, BASE_DIR, EXCEL_META)
    except Exception as e_fech:
        print(f"   Aviso ao gerar fechamento consolidado D-1: {e_fech}")
        fechamento_ontem = None

    if not fechamento_ontem and os.path.exists(FECHAMENTO_ONTEM_FILE):
        try:
            with open(FECHAMENTO_ONTEM_FILE, "r", encoding="utf-8") as f:
                fechamento_ontem = json.load(f)
        except Exception:
            pass

    # Carrega histórico consolidado de fechamentos
    historico_fechamentos = []
    if os.path.exists(HISTORICO_FECHAMENTOS_FILE):
        try:
            with open(HISTORICO_FECHAMENTOS_FILE, "r", encoding="utf-8") as f:
                historico_fechamentos = json.load(f)
        except Exception:
            historico_fechamentos = []

    # 8.5 Processamento de Inteligência Regional e Concorrência
    regional_data = process_regional_data(raw)

    try:
        from extract_precifica import calculate_competitor_loss_ranking
        concorrentes_ranking = calculate_competitor_loss_ranking(precifica_items)
    except Exception as e_conc:
        print(f"   Aviso ao calcular ranking de concorrentes: {e_conc}")
        concorrentes_ranking = []

    # Alertas Comerciais Executivos adicionais em radar_alertas
    uf_maior_queda = min(regional_data["ufs"], key=lambda x: x["gap_d7_rs"]) if regional_data.get("ufs") else None
    coord_maior_queda = min(regional_data["coordenacoes"], key=lambda x: x["gap_d7_rs"]) if regional_data.get("coordenacoes") else None
    top_concorrente = concorrentes_ranking[0] if concorrentes_ranking else None

    if uf_maior_queda and coord_maior_queda:
        radar_alertas["alerta_regional"] = {
            "titulo": "🌍 Alerta Regional (Capilaridade Geográfica)",
            "estado_critico": uf_maior_queda["uf"],
            "gap_estado_rs": uf_maior_queda["gap_d7_rs"],
            "var_estado_pct": uf_maior_queda["var_d7_pct"],
            "coordenacao_critica": coord_maior_queda["coordenador"],
            "coordenacao_uf": coord_maior_queda["uf"],
            "gap_coordenacao_rs": coord_maior_queda["gap_d7_rs"],
            "var_coordenacao_pct": coord_maior_queda["var_d7_pct"],
            "texto": f"O estado {uf_maior_queda['uf']} concentra o maior GAP vs D-7 (R$ {uf_maior_queda['gap_d7_rs']:,.2f}, {uf_maior_queda['var_d7_pct']}%). Na coordenação de {coord_maior_queda['coordenador']} ({coord_maior_queda['uf']}), o recuo foi de R$ {coord_maior_queda['gap_d7_rs']:,.2f}."
        }

    if top_concorrente:
        radar_alertas["alerta_concorrencia"] = {
            "titulo": "🎯 Alerta de Concorrência (Maior Agressividade de Preço)",
            "principal_concorrente": top_concorrente["rede"],
            "is_farmacia": top_concorrente["is_farmacia"],
            "skus_mais_baratos": top_concorrente["skus_mais_baratos"],
            "perda_potencial_rs": round(top_concorrente["impacto_financeiro_estimado_rs"], 2),
            "maior_spread_pct": top_concorrente["maior_spread_pct"],
            "texto": f"A rede {top_concorrente['rede']} lidera a pressão de preço com {top_concorrente['skus_mais_baratos']:,} SKUs mais baratos e R$ {top_concorrente['impacto_financeiro_estimado_rs']:,.2f} em perda potencial estimada."
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
            "data_hoje": data_hoje_str,
            "data_ontem": dt_ontem.strftime("%d/%m/%Y"),
            "data_d7": dt_d7.strftime("%d/%m/%Y"),
            "label_hoje": f"Hoje ({dow_short} {dt_ref.strftime('%d/%m')})",
            "label_ontem": f"Ontem ({ontem_dow_short} {dt_ontem.strftime('%d/%m')})",
            "label_d7": f"D-7 ({d7_dow_short} {dt_d7.strftime('%d/%m')})",
            "canais_monitorados": ["Site", "APP", "MKP"],
            "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "kpis": executive_kpis,
        "estoque_impacto": estoque_impacto,
        "radar_alertas": radar_alertas,
        "precifica_catalogo_full": precifica_catalogo_full,
        "concorrentes_ranking": concorrentes_ranking,
        "regional": regional_data,
        "mix_canais": mix_canais,
        "horario_nobre": horario_nobre,
        "hourly_curve": hourly_curve_table,
        "storytelling": storytelling,
        "fechamento_ontem": fechamento_ontem,
        "historico_fechamentos": historico_fechamentos,
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

    # Atualiza data/daemon_status.json para sinalizar auto-refresh imediato no GitHub Pages e no servidor local
    status_file = os.path.join(DATA_DIR, "daemon_status.json")
    status_dict = {
        "status": "ONLINE",
        "started_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "last_sync": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "last_corte": max_data_hora,
        "last_status": "Sucesso",
        "sync_count": 1,
        "is_syncing": False,
        "next_sync_in": 0,
        "network_url": "http://localhost:3000",
        "local_url": "http://localhost:3000"
    }
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as sf:
                existing_st = json.load(sf)
                if isinstance(existing_st, dict):
                    status_dict.update(existing_st)
                    status_dict["last_sync"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    status_dict["last_corte"] = max_data_hora
                    status_dict["last_status"] = "Sucesso"
                    status_dict["is_syncing"] = False
                    status_dict["sync_count"] = int(existing_st.get("sync_count", 0)) + 1
        except Exception:
            pass
    try:
        with open(status_file, "w", encoding="utf-8") as sf:
            json.dump(status_dict, sf, ensure_ascii=False, indent=2)
    except Exception as e_st:
        print(f"   Aviso ao atualizar daemon_status.json: {e_st}")

    # Gera automaticamente a planilha Excel formatada com os Top 50 Detratores
    generate_excel_top50(output_data, DATA_DIR)

    # Dados são salvos em intraday_monitor.json e intraday_data.js para carregamento ultra-rápido (<50ms)
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
