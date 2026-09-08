# -*- coding: utf-8 -*-
"""
Script de integração da exportação para Excel:
1. Atualiza process_intraday_analytics.py para gerar a planilha nativa Top_50_Detratores_Canais_Digitais.xlsx
   e expandir detratores_top para 50 itens.
2. Atualiza index.html adicionando os botões de download e a função de exportação client-side instantânea.
"""

# ======================================================================
# 1. ATUALIZAR process_intraday_analytics.py
# ======================================================================
with open("process_intraday_analytics.py", "r", encoding="utf-8") as f:
    py_code = f.read()

# Atualiza detratores_top para 50
old_slice = """        res_sorted = sorted(res, key=lambda x: x["gap_d7_rs"])
        detratores = res_sorted[:30]
        alavancadores = sorted(res, key=lambda x: x["gap_d7_rs"], reverse=True)[:30]"""

new_slice = """        res_sorted = sorted(res, key=lambda x: x["gap_d7_rs"])
        detratores = res_sorted[:50] # Top 50 Detratores
        alavancadores = sorted(res, key=lambda x: x["gap_d7_rs"], reverse=True)[:50]"""

if old_slice in py_code:
    py_code = py_code.replace(old_slice, new_slice)
    print("[OK] detratores_top e alavancadores_top expandidos para 50 itens.")

# Adiciona a função generate_excel_top50 em process_intraday_analytics.py
excel_gen_func = '''
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
'''

if "def generate_excel_top50" not in py_code:
    # Insere antes de def process_analytics():
    target_def = "def process_analytics():"
    py_code = py_code.replace(target_def, excel_gen_func + "\n" + target_def)
    print("[OK] Função generate_excel_top50 inserida em process_intraday_analytics.py.")

# Chama generate_excel_top50 ao final de process_analytics
call_excel_target = """    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.INTRADAY_DATA = " + json.dumps(output_data, ensure_ascii=False) + ";\\n")"""

call_excel_replacement = """    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.INTRADAY_DATA = " + json.dumps(output_data, ensure_ascii=False) + ";\\n")

    # Gera automaticamente a planilha Excel formatada com os Top 50 Detratores
    generate_excel_top50(output_data, DATA_DIR)"""

if call_excel_target in py_code:
    py_code = py_code.replace(call_excel_target, call_excel_replacement)
    print("[OK] Chamada de geração do Excel adicionada.")

with open("process_intraday_analytics.py", "w", encoding="utf-8") as f:
    f.write(py_code)

# ======================================================================
# 2. ATUALIZAR index.html
# ======================================================================
with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Atualiza a barra de ações da Matriz de Detratores com os botões de Excel
old_filter_actions = """        <!-- Filter Actions -->
        <div class="filter-actions-group">
          <button class="pill-filter-btn active" id="btn-fil-det" onclick="setMatrixFilter('detratores')">⚠️ Detratores</button>
          <button class="pill-filter-btn" id="btn-fil-bst" onclick="setMatrixFilter('alavancadores')">🚀 Alavancadores</button>
          <button class="pill-filter-btn" id="btn-fil-all" onclick="setMatrixFilter('all')">Todos</button>
          <input type="text" class="apple-search-input" id="search-input" placeholder="Buscar por código ou nome..." oninput="renderMatrixTable()">
        </div>"""

new_filter_actions = """        <!-- Filter Actions -->
        <div class="filter-actions-group" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
          <button class="pill-filter-btn active" id="btn-fil-det" onclick="setMatrixFilter('detratores')">⚠️ Detratores</button>
          <button class="pill-filter-btn" id="btn-fil-bst" onclick="setMatrixFilter('alavancadores')">🚀 Alavancadores</button>
          <button class="pill-filter-btn" id="btn-fil-all" onclick="setMatrixFilter('all')">Todos</button>
          <input type="text" class="apple-search-input" id="search-input" placeholder="Buscar por código ou nome..." oninput="renderMatrixTable()" style="max-width: 250px;">
          
          <!-- Botões de Baixar Excel -->
          <a href="data/Top_50_Detratores_Canais_Digitais.xlsx" download="Top_50_Detratores_Canais_Digitais.xlsx" class="pill-filter-btn" style="background: rgba(48, 209, 88, 0.12); color: var(--apple-green-text); border: 1px solid rgba(48, 209, 88, 0.35); font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; gap: 5px; cursor: pointer;" title="Baixar planilha oficial formatada em Excel (.xlsx) com os Top 50 Detratores">
            📊 Baixar Top 50 (.xlsx)
          </a>
          <button class="pill-filter-btn" id="btn-export-current-csv" onclick="exportCurrentTableToExcel()" style="background: var(--apple-green); color: #fff; border: none; font-weight: 700; display: inline-flex; align-items: center; gap: 5px; cursor: pointer;" title="Exportar a lista atual visível/filtrada para Excel (CSV formatado com acentos)">
            📥 Exportar Visão Atual
          </button>
        </div>"""

if old_filter_actions in html:
    html = html.replace(old_filter_actions, new_filter_actions)
    print("[OK] Botões de download do Excel inseridos na Matriz de Detratores.")

# Adiciona botão de exportar preços na seção da Precifica
old_prec_filters = """          <div style="display: flex; gap: 6px; flex-wrap: wrap;" id="precifica-status-filters">
            <button class="pill-filter-btn active" id="btn-prec-all" onclick="setPrecificaStatusFilter('ALL')">Todos (694)</button>
            <button class="pill-filter-btn" id="btn-prec-caros" onclick="setPrecificaStatusFilter('MAIS_CARO')">🚨 Mais Caros (608)</button>
            <button class="pill-filter-btn" id="btn-prec-criticos" onclick="setPrecificaStatusFilter('CRITICOS_30')">⚠️ Spread > +30% (231)</button>
            <button class="pill-filter-btn" id="btn-prec-baratos" onclick="setPrecificaStatusFilter('MAIS_BARATO')">🏆 Líder São João (46)</button>
            <button class="pill-filter-btn" id="btn-prec-empatados" onclick="setPrecificaStatusFilter('EMPATADO')">⚖️ Empatados (40)</button>
          </div>
        </div>"""

new_prec_filters = """          <div style="display: flex; gap: 6px; flex-wrap: wrap;" id="precifica-status-filters">
            <button class="pill-filter-btn active" id="btn-prec-all" onclick="setPrecificaStatusFilter('ALL')">Todos (694)</button>
            <button class="pill-filter-btn" id="btn-prec-caros" onclick="setPrecificaStatusFilter('MAIS_CARO')">🚨 Mais Caros (608)</button>
            <button class="pill-filter-btn" id="btn-prec-criticos" onclick="setPrecificaStatusFilter('CRITICOS_30')">⚠️ Spread > +30% (231)</button>
            <button class="pill-filter-btn" id="btn-prec-baratos" onclick="setPrecificaStatusFilter('MAIS_BARATO')">🏆 Líder São João (46)</button>
            <button class="pill-filter-btn" id="btn-prec-empatados" onclick="setPrecificaStatusFilter('EMPATADO')">⚖️ Empatados (40)</button>
          </div>

          <button class="pill-filter-btn" onclick="exportPrecificaToExcel()" style="background: rgba(10, 132, 255, 0.12); color: var(--apple-blue); border: 1px solid rgba(10, 132, 255, 0.35); font-weight: 700; display: inline-flex; align-items: center; gap: 5px; cursor: pointer; margin-left: auto;" title="Exportar catálogo filtrado de concorrência Precifica para Excel (CSV formatado)">
            📥 Baixar Preços Precifica (CSV)
          </button>
        </div>"""

if old_prec_filters in html:
    html = html.replace(old_prec_filters, new_prec_filters)
    print("[OK] Botão de exportação da Precifica inserido.")

# Adiciona as funções exportCurrentTableToExcel e exportPrecificaToExcel no script
export_funcs = """
    /* ======================================================================
       FUNÇÕES DE EXPORTAÇÃO NATIVA PARA MICROSOFT EXCEL / CSV PT-BR
       ====================================================================== */
    function exportCurrentTableToExcel() {
      if (!globalData) return;
      const lvlData = globalData.detratores_alavancadores?.[currentLevel] || {};
      let items = [];

      if (currentLevel === 'skus') {
        if (currentCausaFilter !== 'TODOS') {
          const allDetratores = (lvlData.all || []).filter(i => (i.gap_d7_rs || 0) < 0);
          if (currentCausaFilter === 'RUPTURA') {
            items = allDetratores.filter(i => (i.causa_tipo === 'RUPTURA_LOGISTICA' || i.causa_tipo === 'RUPTURA_ZERO' || i.causa_tipo === 'RUPTURA_CAPILAR' || (i.un_por_loja !== undefined && i.un_por_loja < 1.5 && i.causa_tipo !== 'DUPLO_DETRATOR')));
          } else if (currentCausaFilter === 'DUPLO') {
            items = allDetratores.filter(i => i.causa_tipo === 'DUPLO_DETRATOR');
          } else if (currentCausaFilter === 'PRECO') {
            items = allDetratores.filter(i => i.causa_tipo === 'PRECO_DESALINHADO');
          } else if (currentCausaFilter === 'COMERCIAL') {
            items = allDetratores.filter(i => (i.causa_tipo === 'DEMANDA_COMERCIAL' || i.causa_tipo === 'ABASTECIDO'));
          }
          items.sort((a, b) => (a.gap_d7_rs || 0) - (b.gap_d7_rs || 0));
        } else {
          if (currentFilter === 'detratores') items = (lvlData.detratores_top || []).slice(0, 50);
          else if (currentFilter === 'alavancadores') items = (lvlData.alavancadores_top || []).slice(0, 50);
          else items = (lvlData.all || []).slice(0, 100);
        }
      } else {
        if (currentFilter === 'detratores') items = (lvlData.detratores_top || []).slice(0, 50);
        else if (currentFilter === 'alavancadores') items = (lvlData.alavancadores_top || []).slice(0, 50);
        else items = (lvlData.all || []).slice(0, 100);
      }

      const q = (document.getElementById('search-input')?.value || '').toLowerCase().trim();
      if (q) {
        items = items.filter(it => {
          const nome = (it.nome || '').toLowerCase();
          const sku = (it.sku_id ? String(it.sku_id) : '').toLowerCase();
          const grp = (it.grupo || it.canal || '').toLowerCase();
          return nome.includes(q) || sku.includes(q) || grp.includes(q);
        });
      }

      if (items.length === 0) {
        alert('Nenhum dado encontrado para exportação com os filtros atuais.');
        return;
      }

      const headers = [
        "Posicao", "Codigo SKU", "Produto / Descricao", "Hoje Realizado (R$)",
        "Esperado D-7 (R$)", "GAP vs D-7 (R$)", "GAP vs D-7 (%)", "Estoque Rede (un)",
        "Densidade (un/lj)", "Causa-Raiz Diagnostico", "Preco Sao Joao (R$)",
        "Menor Concorrente", "Preco Concorrencia (R$)", "Spread Preco (%)", "Status Concorrencia", "Classificacao"
      ];

      const rows = items.map((it, idx) => {
        const saldo = it.saldo !== undefined && it.saldo !== null ? Number(it.saldo) : 0;
        const unLoja = it.un_por_loja !== undefined && it.un_por_loja !== null ? Number(it.un_por_loja) : (saldo / 1147);
        const gapRs = (it.gap_d7_rs || 0).toFixed(2).replace('.', ',');
        const gapPct = (it.gap_d7_pct || 0).toFixed(1).replace('.', ',') + '%';
        const hoje = (it.hoje || 0).toFixed(2).replace('.', ',');
        const d7Exp = (it.d7_exp_corte || 0).toFixed(2).replace('.', ',');
        const precoSJ = it.nosso_preco ? it.nosso_preco.toFixed(2).replace('.', ',') : '';
        const redeConc = (it.menor_concorrente_rede || '').toUpperCase().replace('FARMACIAS', '').replace('PRECO', 'PREÇO ');
        const precoConc = it.menor_concorrente_preco ? it.menor_concorrente_preco.toFixed(2).replace('.', ',') : '';
        const spreadPct = it.spread_pct !== undefined && it.spread_pct !== null ? it.spread_pct.toFixed(1).replace('.', ',') + '%' : '';

        let causaDesc = 'Demanda Normal';
        if (it.causa_tipo === 'DUPLO_DETRATOR') causaDesc = 'Duplo Detrator';
        else if (it.causa_tipo === 'RUPTURA_LOGISTICA' || it.causa_tipo === 'RUPTURA_ZERO' || it.causa_tipo === 'RUPTURA_CAPILAR') causaDesc = 'Ruptura Logistica';
        else if (it.causa_tipo === 'PRECO_DESALINHADO') causaDesc = 'Preco Desalinhado';

        let statusConc = 'Nao Monitorado';
        if (it.precifica_monitorado) {
          if (it.preco_status === 'MAIS_CARO') statusConc = 'Sao Joao Mais Cara';
          else if (it.preco_status === 'MAIS_BARATO') statusConc = 'Lider de Preco';
          else if (it.preco_status === 'EMPATADO') statusConc = 'Preco Alinhado';
        }

        const nomeClean = (it.nome || '').replace(/;/g, ' - ');

        return [
          idx + 1,
          `"${it.sku_id || ''}"`,
          `"${nomeClean}"`,
          `"${hoje}"`,
          `"${d7Exp}"`,
          `"${gapRs}"`,
          `"${gapPct}"`,
          Math.round(saldo),
          `"${unLoja.toFixed(2).replace('.', ',')}"`,
          `"${causaDesc}"`,
          `"${precoSJ}"`,
          `"${redeConc}"`,
          `"${precoConc}"`,
          `"${spreadPct}"`,
          `"${statusConc}"`,
          `"${it.status || ''}"`
        ].join(';');
      });

      const csvContent = "\\uFEFF" + headers.join(';') + "\\r\\n" + rows.join("\\r\\n");
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      
      const corteData = (globalData.metadata?.corte_hora || 'corte').replace(':', 'h');
      let suf = currentCausaFilter !== 'TODOS' ? `_${currentCausaFilter}` : '_Top50';
      link.setAttribute("href", url);
      link.setAttribute("download", `Detratores_Canais_Digitais_${corteData}${suf}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }

    function exportPrecificaToExcel() {
      if (!precificaFilteredCache || precificaFilteredCache.length === 0) return;
      const headers = [
        "Codigo SKU", "Produto / Descricao", "Marca", "Categoria",
        "Preco Sao Joao (R$)", "Menor Concorrente", "Preco Concorrencia (R$)",
        "Spread (R$)", "Spread (%)", "Status Competitivo"
      ];

      const rows = precificaFilteredCache.map(it => {
        const precoSJ = it.nosso_preco ? it.nosso_preco.toFixed(2).replace('.', ',') : '';
        const precoConc = it.menor_preco ? it.menor_preco.toFixed(2).replace('.', ',') : '';
        const spreadRs = it.spread_rs !== undefined && it.spread_rs !== null ? it.spread_rs.toFixed(2).replace('.', ',') : '';
        const spreadPct = it.spread_pct !== undefined && it.spread_pct !== null ? it.spread_pct.toFixed(1).replace('.', ',') + '%' : '';
        const redeUpper = (it.menor_rede || '').toUpperCase().replace('FARMACIAS', '').replace('PRECO', 'PREÇO ');
        const nomeClean = (it.nome || '').replace(/;/g, ' - ');
        const marcaClean = (it.marca || '').replace(/;/g, ' - ');

        return [
          `"${it.sku || ''}"`,
          `"${nomeClean}"`,
          `"${marcaClean}"`,
          `"${it.categoria || ''}"`,
          `"${precoSJ}"`,
          `"${redeUpper}"`,
          `"${precoConc}"`,
          `"${spreadRs}"`,
          `"${spreadPct}"`,
          `"${it.status || ''}"`
        ].join(';');
      });

      const csvContent = "\\uFEFF" + headers.join(';') + "\\r\\n" + rows.join("\\r\\n");
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", `Monitor_Precos_Precifica_694_Itens.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
"""

if "function exportCurrentTableToExcel()" not in html:
    # Insere antes de </script>
    last_script_end = "</body>\n</html>"
    # Procuramos </script> antes de </body>
    parts = html.rsplit("</script>", 1)
    if len(parts) == 2:
        html = parts[0] + export_funcs + "\n  </script>" + parts[1]
        print("[OK] Funções de exportação JavaScript adicionadas a index.html.")
    else:
        print("[AVISO] Tag </script> não encontrada.")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("[SUCESSO] Integração completa de exportação para Excel realizada com sucesso!")
