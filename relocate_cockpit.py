import re, sys

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Encontrar o bloco do Cockpit
pattern_cockpit = r'(<!-- PAINEL DE AUDITORIA DE RUPTURA & CAPILARIDADE DE ESTOQUE \(1\.147 LOJAS\) -->[\s\S]*?<\/div>\s*<\/div>\s*<\/div>)\s*(?=<!-- DETRACTORS & BOOSTERS MATRIX)'

match = re.search(pattern_cockpit, html)
if not match:
    # Try alternative matching
    start_str = '<!-- PAINEL DE AUDITORIA DE RUPTURA & CAPILARIDADE DE ESTOQUE (1.147 LOJAS) -->'
    end_str = '<!-- DETRACTORS & BOOSTERS MATRIX (5 HIERARCHY LEVELS) -->'
    start_pos = html.find(start_str)
    end_pos = html.find(end_str)
    if start_pos != -1 and end_pos != -1:
        cockpit_block = html[start_pos:end_pos].strip()
        html = html[:start_pos] + html[end_pos:]
        print("Extracted cockpit block via positions, length:", len(cockpit_block))
    else:
        print("ERROR: Cockpit block boundaries not found!")
        sys.exit(1)
else:
    cockpit_block = match.group(1).strip()
    html = html[:match.start()] + html[match.end():]
    print("Extracted cockpit block via regex, length:", len(cockpit_block))

# 2. Inserir o Cockpit logo após o Executive KPI Grid (antes do RADAR DE MIX)
target_insertion = '<!-- RADAR DE MIX & EFICIÊNCIA DOS CANAIS (RETAIL ANALYTICS) -->'
if target_insertion not in html:
    print("ERROR: target insertion not found!")
    sys.exit(1)

html = html.replace(target_insertion, cockpit_block + '\n\n    ' + target_insertion)
print("Successfully inserted Cockpit right above RADAR DE MIX!")

# 3. Melhorar o container de story-estoque no Diagnóstico
old_story_estoque = '<div class="story-body" id="story-estoque" style="margin-top: -6px; color: var(--apple-blue); font-weight: 500;">...</div>'
new_story_estoque = '''<div class="story-estoque-box" id="story-estoque-container" style="margin: 14px 0 10px 0; padding: 14px 18px; background: rgba(255, 59, 48, 0.07); border: 1px solid rgba(255, 59, 48, 0.25); border-left: 4px solid var(--apple-red); border-radius: 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 8px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 16px;">📦</span>
            <strong style="color: var(--apple-red-text); font-size: 13.5px; font-weight: 700;">Auditoria Executiva de Estoque & Ruptura Capilar (Rede 1.147 Lojas São João)</strong>
          </div>
          <span class="tag-badge tag-critico" style="font-weight: 700; font-size: 11px;">67% DO DÉFICIT É RUPTURA LOGÍSTICA</span>
        </div>
        <div id="story-estoque" style="font-size: 12.5px; color: var(--text-primary); line-height: 1.55;">...</div>
      </div>'''

if old_story_estoque in html:
    html = html.replace(old_story_estoque, new_story_estoque)
    print("Successfully enhanced story-estoque callout container!")

# 4. Atualizar o JS para preencher kpi-est-densidade-val
old_js_block = "document.getElementById('kpi-est-pct-comercial').innerText = `${est.pct_comercial || 35}% DO GAP`;"
new_js_block = '''document.getElementById('kpi-est-pct-comercial').innerText = `${est.pct_comercial || 35}% DO GAP`;

        if (document.getElementById('kpi-est-densidade-val') && est.densidade_media_desabastecidos !== undefined) {
          document.getElementById('kpi-est-densidade-val').innerText = `${est.densidade_media_desabastecidos.toFixed(2).replace('.', ',')} un / loja`;
        }'''

if old_js_block in html:
    html = html.replace(old_js_block, new_js_block)
    print("Successfully added kpi-est-densidade-val dynamic update in JS!")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("SUCCESS: index.html updated successfully!")
