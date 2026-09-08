import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Adicionar estilo para a caixa de Preço Precifica e os botões de filtro
style_add = '''
    .story-preco-box {
      margin: 10px 0 14px 0;
      padding: 14px 18px;
      background: rgba(255, 149, 0, 0.07);
      border: 1px solid rgba(255, 149, 0, 0.25);
      border-left: 4px solid var(--apple-orange);
      border-radius: 10px;
    }
    .pill-filter-btn {
      padding: 5px 12px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 20px;
      border: 1px solid var(--border-color);
      background: var(--bg-card);
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .pill-filter-btn.active {
      background: var(--apple-blue);
      color: #fff;
      border-color: var(--apple-blue);
    }
    .pill-filter-btn:hover:not(.active) {
      background: var(--bg-card-hover);
      color: var(--text-primary);
    }
'''

if '.story-preco-box' not in html:
    html = html.replace('.story-estoque-box {', style_add + '\n    .story-estoque-box {')
    print("Added CSS styles for Precifica box and filter pills!")

# 2. Adicionar o bloco de Storytelling de Preço logo abaixo do bloco de Estoque
preco_box_html = '''
      <div class="story-preco-box" id="story-preco-container">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 16px;">🏷️</span>
            <strong style="color: var(--apple-orange-text); font-size: 13.5px; font-weight: 700;">Auditoria de Competitividade de Preço (API Precifica — 9.005 Itens Monitorados)</strong>
          </div>
          <span class="tag-badge tag-moderado" style="font-weight: 700; font-size: 11px;" id="story-preco-badge">+30,1% SPREAD MÉDIO</span>
        </div>
        <div id="story-preco" style="font-size: 12.5px; color: var(--text-primary); line-height: 1.55;">Carregando dados da Precifica...</div>
      </div>
'''

if 'id="story-preco-container"' not in html:
    target = 'id="story-estoque-container"'
    idx = html.find(target)
    if idx != -1:
        # Encontra o fechamento da div do estoque-container
        end_div = html.find('</div>\n      </div>', idx)
        if end_div != -1:
            html = html[:end_div + 13] + '\n' + preco_box_html + html[end_div + 13:]
            print("Inserted story-preco-container in HTML!")

# 3. Atualizar Card 3 do Cockpit para Radar de Preço (Precifica)
old_card3 = '''        <!-- Card 3: Densidade Média nos Detratores -->
        <div class="kpi-card" style="border-left: 4px solid var(--apple-orange);">
          <div class="kpi-label-row">
            <span class="kpi-title">Densidade Média da Rede</span>
            <span class="tag-badge tag-moderado" id="kpi-est-tag-densidade">🚨 Ruptura Crítica</span>
          </div>
          <div class="kpi-value" id="kpi-est-densidade-val" style="color: var(--apple-orange-text);">0.48 un / loja</div>
          <div class="kpi-footer-row">
            <span>Régua: <strong>1.147 Filiais</strong></span>
            <span>Mounjaro: <strong>0.31 un/lj</strong></span>
          </div>
        </div>'''

new_card3 = '''        <!-- Card 3: Radar de Preços (Precifica) -->
        <div class="kpi-card" style="border-left: 4px solid var(--apple-orange);">
          <div class="kpi-label-row">
            <span class="kpi-title">Radar de Preços (Precifica)</span>
            <span class="tag-badge tag-critico" id="kpi-preco-badge">+30,1% SPREAD</span>
          </div>
          <div class="kpi-value" id="kpi-preco-val" style="color: var(--apple-orange-text);">87,8% Mais Caros</div>
          <div class="kpi-footer-row">
            <span id="kpi-preco-sub">Base: <strong>9.005 Itens</strong></span>
            <span id="kpi-preco-agressor">Agressor: <strong>Nissei / Preço Pop</strong></span>
          </div>
        </div>'''

if old_card3 in html:
    html = html.replace(old_card3, new_card3)
    print("Replaced Card 3 with Radar de Preços (Precifica)!")

# 4. Adicionar Filtros Rápidos de Causa-Raiz acima da tabela
filter_pills_html = '''
      <div style="display: flex; gap: 8px; margin: 12px 0 16px 0; flex-wrap: wrap; align-items: center;" id="causa-filters-wrapper">
        <span style="font-size: 12px; font-weight: 700; color: var(--text-tertiary); margin-right: 4px;">FILTRAR CAUSA:</span>
        <button class="pill-filter-btn active" id="btn-filtro-todos" onclick="setFiltroCausa('TODOS')">Todos os SKUs</button>
        <button class="pill-filter-btn" id="btn-filtro-ruptura" onclick="setFiltroCausa('RUPTURA')">🚨 Apenas Ruptura de Estoque</button>
        <button class="pill-filter-btn" id="btn-filtro-preco" onclick="setFiltroCausa('PRECO')">🏷️ Apenas Preço Desalinhado</button>
        <button class="pill-filter-btn" id="btn-filtro-comercial" onclick="setFiltroCausa('COMERCIAL')">📉 Apenas Demanda Comercial</button>
      </div>
'''

if 'id="causa-filters-wrapper"' not in html:
    target_table_wrap = '<div class="table-card" style="margin-top: 20px;">'
    if target_table_wrap in html:
        html = html.replace(target_table_wrap, target_table_wrap + '\n' + filter_pills_html)
        print("Added causa-filters-wrapper above matrix table!")

# 5. Atualizar Header da Tabela de SKUs com a coluna de Preço vs Concorrência
old_thead_skus = '''      if (currentLevel === 'skus') {
        thead.innerHTML = `
          <th>Código</th>
          <th>Item / Descrição</th>
          <th class="num-col">Hoje (até corte)</th>
          <th class="num-col">Esperado D-7</th>
          <th class="num-col">GAP vs D-7 (R$)</th>
          <th class="num-col">Saldo Rede</th>
          <th class="num-col">Densidade</th>
          <th>Causa-Raiz (1.147 Lojas)</th>
          <th class="num-col">D-7 Total</th>
          <th>Classificação</th>
        `;'''

new_thead_skus = '''      if (currentLevel === 'skus') {
        thead.innerHTML = `
          <th>Código</th>
          <th>Item / Descrição</th>
          <th class="num-col">Hoje (até corte)</th>
          <th class="num-col">Esperado D-7</th>
          <th class="num-col">GAP vs D-7 (R$)</th>
          <th class="num-col">Saldo Rede</th>
          <th class="num-col">Densidade</th>
          <th>Causa-Raiz (Estoque)</th>
          <th>Preço vs Concorrência (Precifica)</th>
          <th class="num-col">D-7 Total</th>
          <th>Classificação</th>
        `;'''

if old_thead_skus in html:
    html = html.replace(old_thead_skus, new_thead_skus)
    print("Updated SKU table thead with Preço vs Concorrência column!")

# 6. Atualizar a renderização de linhas de SKUs para incluir o Preço e aplicar o filtro
old_sku_render = '''        if (currentLevel === 'skus') {
          const saldo = item.saldo !== undefined && item.saldo !== null ? Number(item.saldo) : 0;
          const unLoja = item.un_por_loja !== undefined && item.un_por_loja !== null ? Number(item.un_por_loja) : (saldo / 1147);
          
          let causaBadge = '';
          if (saldo <= 0) {
            causaBadge = `<span class="tag-badge tag-critico" style="font-size: 10.5px; white-space: nowrap;">🚨 Ruptura Zero (0 un)</span>`;
          } else if (unLoja < 0.5) {
            causaBadge = `<span class="tag-badge tag-critico" style="font-size: 10.5px; white-space: nowrap;">🚨 Ruptura Severa (${unLoja.toFixed(2).replace('.', ',')} un/lj)</span>`;
          } else if (unLoja < 1.5) {
            causaBadge = `<span class="tag-badge tag-moderado" style="font-size: 10.5px; white-space: nowrap;">⚠️ Estoque Restrito (${unLoja.toFixed(2).replace('.', ',')} un/lj)</span>`;
          } else {
            causaBadge = `<span class="tag-badge tag-alavancador" style="font-size: 10.5px; white-space: nowrap;">📉 Demanda Comercial</span>`;
          }

          return `
            <tr>
              <td style="font-family: var(--font-mono); font-weight: 700; color: var(--apple-blue);">${item.sku_id}</td>
              <td style="font-weight: 600;">${item.nome}</td>
              <td class="num-col">${fmtBRL(item.hoje)}</td>
              <td class="num-col">${fmtBRL(item.d7_exp_corte)}</td>
              <td class="num-col" style="color: ${gapColor}; font-weight: 700;">${fmtBRLDelta(gapD7)}</td>
              <td class="num-col" style="font-family: var(--font-mono); font-weight: 600;">${Math.round(saldo).toLocaleString('pt-BR')} un</td>
              <td class="num-col" style="font-family: var(--font-mono); font-weight: 700; color: ${unLoja < 1.5 ? 'var(--apple-red-text)' : 'var(--apple-green-text)'};">${unLoja.toFixed(2).replace('.', ',')} un/lj</td>
              <td>${causaBadge}</td>
              <td class="num-col" style="color: var(--text-tertiary);">${fmtBRL(item.d7_full)}</td>
              <td><span class="tag-badge ${tagClass}">${item.status}</span></td>
            </tr>
          `;'''

new_sku_render = '''        if (currentLevel === 'skus') {
          const saldo = item.saldo !== undefined && item.saldo !== null ? Number(item.saldo) : 0;
          const unLoja = item.un_por_loja !== undefined && item.un_por_loja !== null ? Number(item.un_por_loja) : (saldo / 1147);
          
          let causaBadge = '';
          if (saldo <= 0) {
            causaBadge = `<span class="tag-badge tag-critico" style="font-size: 10.5px; white-space: nowrap;">🚨 Ruptura Zero (0 un)</span>`;
          } else if (unLoja < 0.5) {
            causaBadge = `<span class="tag-badge tag-critico" style="font-size: 10.5px; white-space: nowrap;">🚨 Ruptura Severa (${unLoja.toFixed(2).replace('.', ',')} un/lj)</span>`;
          } else if (unLoja < 1.5) {
            causaBadge = `<span class="tag-badge tag-moderado" style="font-size: 10.5px; white-space: nowrap;">⚠️ Estoque Restrito (${unLoja.toFixed(2).replace('.', ',')} un/lj)</span>`;
          } else if (item.causa_tipo === 'PRECO_DESALINHADO') {
            causaBadge = `<span class="tag-badge tag-critico" style="font-size: 10.5px; white-space: nowrap;">🏷️ Preço Desalinhado</span>`;
          } else {
            causaBadge = `<span class="tag-badge tag-alavancador" style="font-size: 10.5px; white-space: nowrap;">📉 Demanda Comercial</span>`;
          }

          let precoBadge = '<span style="color: var(--text-quaternary); font-size: 11px;">Sem monitoramento</span>';
          if (item.precifica_monitorado) {
            const spreadStr = fmtPct(item.spread_pct, true);
            const concRede = (item.menor_concorrente_rede || '').toUpperCase();
            const menorPrecoStr = item.menor_concorrente_preco ? `R$ ${item.menor_concorrente_preco.toFixed(2).replace('.', ',')}` : '';
            if (item.preco_status === 'MAIS_CARO') {
              precoBadge = `<span class="tag-badge tag-critico" style="font-size: 10.5px; white-space: nowrap;" title="Nosso R$ ${item.nosso_preco} vs ${concRede} ${menorPrecoStr}">🚨 ${spreadStr} vs ${concRede} (${menorPrecoStr})</span>`;
            } else if (item.preco_status === 'MAIS_BARATO') {
              precoBadge = `<span class="tag-badge tag-alavancador" style="font-size: 10.5px; white-space: nowrap;" title="Nosso R$ ${item.nosso_preco} vs ${concRede} ${menorPrecoStr}">✅ Líder (${spreadStr})</span>`;
            } else if (item.preco_status === 'EMPATADO') {
              precoBadge = `<span class="tag-badge tag-super" style="font-size: 10.5px; white-space: nowrap;">⚖️ Empatado (${concRede})</span>`;
            } else {
              precoBadge = `<span style="color: var(--text-tertiary); font-size: 10.5px;">Sem concorrência ativa</span>`;
            }
          }

          return `
            <tr>
              <td style="font-family: var(--font-mono); font-weight: 700; color: var(--apple-blue);">${item.sku_id}</td>
              <td style="font-weight: 600;">${item.nome}</td>
              <td class="num-col">${fmtBRL(item.hoje)}</td>
              <td class="num-col">${fmtBRL(item.d7_exp_corte)}</td>
              <td class="num-col" style="color: ${gapColor}; font-weight: 700;">${fmtBRLDelta(gapD7)}</td>
              <td class="num-col" style="font-family: var(--font-mono); font-weight: 600;">${Math.round(saldo).toLocaleString('pt-BR')} un</td>
              <td class="num-col" style="font-family: var(--font-mono); font-weight: 700; color: ${unLoja < 1.5 ? 'var(--apple-red-text)' : 'var(--apple-green-text)'};">${unLoja.toFixed(2).replace('.', ',')} un/lj</td>
              <td>${causaBadge}</td>
              <td>${precoBadge}</td>
              <td class="num-col" style="color: var(--text-tertiary);">${fmtBRL(item.d7_full)}</td>
              <td><span class="tag-badge ${tagClass}">${item.status}</span></td>
            </tr>
          `;'''

if old_sku_render in html:
    html = html.replace(old_sku_render, new_sku_render)
    print("Updated SKU row rendering with Precifica price badge!")

# 7. Adicionar lógica JavaScript para atualizar o card de Precifica e filtrar por causa
js_update_add = '''
      // Storytelling Precifica
      if (document.getElementById('story-preco')) {
        document.getElementById('story-preco').innerText = story.auditoria_preco || 'Auditoria de preços não disponível.';
      }

      // Cockpit Precifica KPIs
      const comp = est.competitividade_preco || {};
      const sumCat = comp.summary_catalogo || {};
      if (document.getElementById('kpi-preco-val')) {
        const pctMaisCaros = sumCat.pct_mais_caros !== undefined ? sumCat.pct_mais_caros : 87.8;
        const spreadMedio = sumCat.spread_medio_sobrepreco_pct !== undefined ? sumCat.spread_medio_sobrepreco_pct : 30.1;
        document.getElementById('kpi-preco-badge').innerText = `+${fmtPct(spreadMedio)} SPREAD`;
        document.getElementById('kpi-preco-val').innerText = `${fmtPct(pctMaisCaros)} Mais Caros`;
        document.getElementById('kpi-preco-sub').innerHTML = `Base: <strong>${(sumCat.total_produtos_indexados || 759).toLocaleString('pt-BR')} Itens</strong>`;
        const agressorTop = (sumCat.ranking_agressores && sumCat.ranking_agressores[0]) ? sumCat.ranking_agressores[0].rede.toUpperCase() : 'NISSEI';
        document.getElementById('kpi-preco-agressor').innerHTML = `Agressor: <strong>${agressorTop}</strong>`;
      }
'''

if 'id="story-preco"' not in html:
    html = html.replace("if (document.getElementById('story-estoque')) {\n        document.getElementById('story-estoque').innerText = story.auditoria_estoque || '';\n      }", "if (document.getElementById('story-estoque')) {\n        document.getElementById('story-estoque').innerText = story.auditoria_estoque || '';\n      }\n" + js_update_add)
    print("Added JavaScript update logic for Precifica storytelling and cockpit!")

# 8. Adicionar controle de filtro por causa no JavaScript
js_filter_functions = '''
    let currentCausaFilter = 'TODOS';
    function setFiltroCausa(causa) {
      currentCausaFilter = causa;
      ['todos', 'ruptura', 'preco', 'comercial'].forEach(c => {
        const btn = document.getElementById(`btn-filtro-${c}`);
        if (btn) btn.className = `pill-filter-btn ${c.toUpperCase() === causa ? 'active' : ''}`;
      });
      renderMatrixTable();
    }
'''

if 'let currentCausaFilter' not in html:
    html = html.replace('let currentLevel = \'skus\';', 'let currentLevel = \'skus\';\n' + js_filter_functions)
    print("Added setFiltroCausa function in JS!")

# 9. Aplicar o filtro currentCausaFilter dentro de renderMatrixTable()
old_filter_block = '''      let items = (catData[currentCategory] && catData[currentCategory][currentLevel]) ? catData[currentCategory][currentLevel] : [];'''
new_filter_block = '''      let items = (catData[currentCategory] && catData[currentCategory][currentLevel]) ? catData[currentCategory][currentLevel] : [];
      
      if (currentLevel === 'skus' && currentCausaFilter !== 'TODOS') {
        if (currentCausaFilter === 'RUPTURA') {
          items = items.filter(i => (i.causa_tipo === 'RUPTURA_ZERO' || i.causa_tipo === 'RUPTURA_CAPILAR' || i.causa_tipo === 'ESTOQUE_RESTRITO' || (i.un_por_loja !== undefined && i.un_por_loja < 1.5)));
        } else if (currentCausaFilter === 'PRECO') {
          items = items.filter(i => (i.causa_tipo === 'PRECO_DESALINHADO' || (i.preco_status === 'MAIS_CARO' && i.spread_pct >= 5.0)));
        } else if (currentCausaFilter === 'COMERCIAL') {
          items = items.filter(i => (i.causa_tipo === 'ABASTECIDO' && i.preco_status !== 'MAIS_CARO'));
        }
      }'''

if old_filter_block in html:
    html = html.replace(old_filter_block, new_filter_block)
    print("Applied currentCausaFilter inside renderMatrixTable!")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Dashboard index.html updated successfully with Precifica integration!")
