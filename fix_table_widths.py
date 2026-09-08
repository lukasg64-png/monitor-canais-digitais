# -*- coding: utf-8 -*-
with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Aplicar min-width de 1600px na tabela Precifica e larguras explícitas em cada th
old_prec_table_tag = '<table class="apple-table">'
# Vamos substituir apenas a ocorrência dentro de precifica-table-section
prec_section_marker = '<div class="matrix-card" id="precifica-table-section">'

if prec_section_marker in html:
    part1, part2 = html.split(prec_section_marker, 1)
    
    old_prec_thead_block = """          <thead>
            <tr>
              <th style="white-space: nowrap; width: 90px;">Código</th>
              <th style="min-width: 240px; padding-right: 14px;">Produto / Descrição</th>
              <th style="min-width: 140px; padding-right: 14px;">Marca</th>
              <th style="white-space: nowrap; padding-right: 14px;">Categoria</th>
              <th class="num-col" style="white-space: nowrap; min-width: 95px;">Preço SJ</th>
              <th style="white-space: nowrap; min-width: 130px;">Menor Concorrente</th>
              <th class="num-col" style="white-space: nowrap; min-width: 100px;">Preço Concorrência</th>
              <th class="num-col" style="white-space: nowrap; min-width: 95px;">Spread (R$)</th>
              <th class="num-col" style="white-space: nowrap; min-width: 90px;">Spread (%)</th>
              <th style="white-space: nowrap; min-width: 150px;">Status Competitivo</th>
            </tr>
          </thead>"""

    new_prec_thead_block = """          <thead>
            <tr>
              <th style="width: 100px; min-width: 100px; white-space: nowrap;">Código</th>
              <th style="width: 320px; min-width: 320px; white-space: nowrap;">Produto / Descrição</th>
              <th style="width: 200px; min-width: 200px; white-space: nowrap;">Marca</th>
              <th style="width: 150px; min-width: 150px; white-space: nowrap;">Categoria</th>
              <th class="num-col" style="width: 110px; min-width: 110px; white-space: nowrap;">Preço SJ</th>
              <th style="width: 150px; min-width: 150px; white-space: nowrap;">Menor Concorrente</th>
              <th class="num-col" style="width: 130px; min-width: 130px; white-space: nowrap;">Preço Concorrência</th>
              <th class="num-col" style="width: 120px; min-width: 120px; white-space: nowrap;">Spread (R$)</th>
              <th class="num-col" style="width: 110px; min-width: 110px; white-space: nowrap;">Spread (%)</th>
              <th style="width: 180px; min-width: 180px; white-space: nowrap;">Status Competitivo</th>
            </tr>
          </thead>"""

    part2 = part2.replace('<table class="apple-table">', '<table class="apple-table" style="min-width: 1600px;">', 1)
    part2 = part2.replace(old_prec_thead_block, new_prec_thead_block)
    
    # Nas linhas do tbody da precifica, garantir nowrap e elipse elegantes
    old_row_gen = """          <tr>
            <td style="font-family: var(--font-mono); font-weight: 700; color: var(--apple-blue); white-space: nowrap;">${it.sku}</td>
            <td style="font-weight: 600; min-width: 220px; max-width: 320px; line-height: 1.35; padding-right: 14px; word-break: break-word;">${it.nome || '-'}</td>
            <td style="color: var(--text-secondary); font-size: 11.5px; min-width: 130px; max-width: 170px; line-height: 1.3; padding-right: 14px; word-break: break-word;" title="${it.marca || ''}">${it.marca || '-'}</td>
            <td style="color: var(--text-tertiary); font-size: 11.5px; white-space: nowrap; padding-right: 12px;">${it.categoria || '-'}</td>
            <td class="num-col" style="font-weight: 700; white-space: nowrap;">${precoSJ}</td>
            <td style="font-weight: 700; font-size: 11.5px; white-space: nowrap;"><span class="tag-badge tag-neutro" style="font-size: 11px;">🏪 ${redeUpper}</span></td>
            <td class="num-col" style="font-weight: 600; color: var(--text-secondary); white-space: nowrap;">${precoConc}</td>
            <td class="num-col" style="font-weight: 700; color: ${spreadColor}; font-family: var(--font-mono); white-space: nowrap;">${spreadRsStr}</td>
            <td class="num-col" style="font-weight: 700; color: ${spreadColor}; font-family: var(--font-mono); white-space: nowrap;">${spreadPctStr}</td>
            <td style="white-space: nowrap;"><span class="tag-badge ${tagClass}" style="font-size: 10.5px; white-space: nowrap;">${statusText}</span></td>
          </tr>"""

    new_row_gen = """          <tr>
            <td style="font-family: var(--font-mono); font-weight: 700; color: var(--apple-blue); white-space: nowrap;">${it.sku}</td>
            <td style="font-weight: 600; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${it.nome || ''}">${it.nome || '-'}</td>
            <td style="color: var(--text-secondary); font-size: 11.5px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${it.marca || ''}">${it.marca || '-'}</td>
            <td style="color: var(--text-tertiary); font-size: 11.5px; white-space: nowrap;">${it.categoria || '-'}</td>
            <td class="num-col" style="font-weight: 700; white-space: nowrap;">${precoSJ}</td>
            <td style="font-weight: 700; font-size: 11.5px; white-space: nowrap;"><span class="tag-badge tag-neutro" style="font-size: 11px;">🏪 ${redeUpper}</span></td>
            <td class="num-col" style="font-weight: 600; color: var(--text-secondary); white-space: nowrap;">${precoConc}</td>
            <td class="num-col" style="font-weight: 700; color: ${spreadColor}; font-family: var(--font-mono); white-space: nowrap;">${spreadRsStr}</td>
            <td class="num-col" style="font-weight: 700; color: ${spreadColor}; font-family: var(--font-mono); white-space: nowrap;">${spreadPctStr}</td>
            <td style="white-space: nowrap;"><span class="tag-badge ${tagClass}" style="font-size: 10.5px; white-space: nowrap;">${statusText}</span></td>
          </tr>"""

    part2 = part2.replace(old_row_gen, new_row_gen)
    
    html = part1 + prec_section_marker + part2
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[OK] Tabela Precifica refinada com min-width 1600px e text-overflow ellipsis sem sobreposição.")
else:
    print("[ERRO] prec_section_marker não encontrado.")
