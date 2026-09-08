# -*- coding: utf-8 -*-
"""
Script de refinamento visual e de layout no index.html:
1. Corrige o duplo '+' no spread percentual (++401,4% -> +401,4%).
2. Aplica min-width, padding e formatação em colunas para evitar sobreposição de textos em telas desktop e mobile.
3. Formata Spread R$ com sinal explícito (+R$ 80,32 ou -R$ 1,84).
4. Assegura espaçamento impecável nos badges de status competitivo.
"""

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Ajuste do header da tabela Precifica
old_prec_thead = """          <thead>
            <tr>
              <th>Código</th>
              <th>Produto / Descrição</th>
              <th>Marca</th>
              <th>Categoria</th>
              <th class="num-col">Preço SJ</th>
              <th>Menor Concorrente</th>
              <th class="num-col">Preço Concorrência</th>
              <th class="num-col">Spread (R$)</th>
              <th class="num-col">Spread (%)</th>
              <th>Status Competitivo</th>
            </tr>
          </thead>"""

new_prec_thead = """          <thead>
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

if old_prec_thead in html:
    html = html.replace(old_prec_thead, new_prec_thead)
    print("[OK] Header da tabela Precifica refinado.")

# 2. Ajuste do renderPrecificaTable
old_render_prec_block = """        let spreadRsStr = '-';
        if (it.spread_rs !== undefined && it.spread_rs !== null) {
          const sVal = it.spread_rs;
          spreadRsStr = `${sVal > 0 ? '+' : ''}R$ ${sVal.toFixed(2).replace('.', ',')}`;
        }

        let spreadPctStr = '-';
        if (it.spread_pct !== undefined && it.spread_pct !== null) {
          spreadPctStr = `${it.spread_pct > 0 ? '+' : ''}${fmtPct(it.spread_pct, true)}`;
        }

        return `
          <tr>
            <td style="font-family: var(--font-mono); font-weight: 700; color: var(--apple-blue);">${it.sku}</td>
            <td style="font-weight: 600; max-width: 280px;">${it.nome || '-'}</td>
            <td style="color: var(--text-secondary); font-size: 11.5px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${it.marca || ''}">${it.marca || '-'}</td>
            <td style="color: var(--text-tertiary); font-size: 11.5px;">${it.categoria || '-'}</td>
            <td class="num-col" style="font-weight: 700;">${precoSJ}</td>
            <td style="font-weight: 700; font-size: 11.5px;"><span class="tag-badge tag-neutro" style="font-size: 11px;">🏪 ${redeUpper}</span></td>
            <td class="num-col" style="font-weight: 600; color: var(--text-secondary);">${precoConc}</td>
            <td class="num-col" style="font-weight: 700; color: ${spreadColor}; font-family: var(--font-mono);">${spreadRsStr}</td>
            <td class="num-col" style="font-weight: 700; color: ${spreadColor}; font-family: var(--font-mono);">${spreadPctStr}</td>
            <td><span class="tag-badge ${tagClass}" style="font-size: 10.5px; white-space: nowrap;">${statusText}</span></td>
          </tr>
        `;"""

new_render_prec_block = """        let spreadRsStr = '-';
        if (it.spread_rs !== undefined && it.spread_rs !== null) {
          const sVal = it.spread_rs;
          const absVal = Math.abs(sVal).toFixed(2).replace('.', ',');
          spreadRsStr = sVal > 0 ? `+R$ ${absVal}` : (sVal < 0 ? `-R$ ${absVal}` : `R$ 0,00`);
        }

        let spreadPctStr = '-';
        if (it.spread_pct !== undefined && it.spread_pct !== null) {
          spreadPctStr = fmtPct(it.spread_pct, true);
        }

        return `
          <tr>
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
          </tr>
        `;"""

if old_render_prec_block in html:
    html = html.replace(old_render_prec_block, new_render_prec_block)
    print("[OK] Renderização das linhas da Precifica refinada.")

# 3. Ajuste das células da Matriz de SKUs para prevenir sobreposição de colunas
old_skus_row = """            <tr>
              <td style="font-family: var(--font-mono); font-weight: 700; color: var(--apple-blue);">${item.sku_id}</td>
              <td style="font-weight: 600;">${item.nome}</td>
              <td class="num-col">${fmtBRL(item.hoje)}</td>
              <td class="num-col">${fmtBRL(item.d7_exp_corte)}</td>
              <td class="num-col" style="color: ${gapColor}; font-weight: 700;">${fmtBRLDelta(gapD7)}</td>
              <td class="num-col">${estoqueCell}</td>
              <td>${precoBadge}</td>
              <td>${causaBadge}</td>
              <td><span class="tag-badge ${tagClass}">${item.status}</span></td>
            </tr>"""

new_skus_row = """            <tr>
              <td style="font-family: var(--font-mono); font-weight: 700; color: var(--apple-blue); white-space: nowrap;">${item.sku_id}</td>
              <td style="font-weight: 600; min-width: 220px; max-width: 340px; line-height: 1.35; padding-right: 14px; word-break: break-word;">${item.nome}</td>
              <td class="num-col" style="white-space: nowrap;">${fmtBRL(item.hoje)}</td>
              <td class="num-col" style="white-space: nowrap;">${fmtBRL(item.d7_exp_corte)}</td>
              <td class="num-col" style="color: ${gapColor}; font-weight: 700; white-space: nowrap;">${fmtBRLDelta(gapD7)}</td>
              <td class="num-col" style="white-space: nowrap;">${estoqueCell}</td>
              <td style="white-space: nowrap;">${precoBadge}</td>
              <td style="white-space: nowrap;">${causaBadge}</td>
              <td style="white-space: nowrap;"><span class="tag-badge ${tagClass}">${item.status}</span></td>
            </tr>"""

if old_skus_row in html:
    html = html.replace(old_skus_row, new_skus_row)
    print("[OK] Células da matriz de SKUs refinadas com espaçamento perfeito.")

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("[SUCESSO] Refinamentos visuais aplicados com sucesso!")
