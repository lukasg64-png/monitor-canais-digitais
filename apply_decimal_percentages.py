import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Adicionar fmtPct junto aos formatadores
fmt_pct_def = '''    const fmtNum = (val) => {
      if (val === null || val === undefined || isNaN(val)) return '0';
      return Math.round(val).toLocaleString('pt-BR');
    };

    const fmtPct = (val, showSign = false) => {
      if (val === null || val === undefined || isNaN(val)) return '0,0%';
      const num = Number(val);
      const sign = (showSign && num > 0) ? '+' : '';
      return `${sign}${num.toFixed(1).replace('.', ',')}%`;
    };'''

if 'const fmtPct' not in html:
    html = html.replace('''    const fmtNum = (val) => {
      if (val === null || val === undefined || isNaN(val)) return '0';
      return Math.round(val).toLocaleString('pt-BR');
    };''', fmt_pct_def)
    print("Added fmtPct function!")

# 2. Channel Tabs
html = html.replace("badgeEl.innerText = `${Math.round(cKpi.pacing_corte_pct || 0)}%`;", "badgeEl.innerText = fmtPct(cKpi.pacing_corte_pct);")
html = html.replace("document.getElementById(`tab-d1-${ch}`).innerText = `${cKpi.janela_d1.var_pct >= 0 ? '+' : ''}${Math.round(cKpi.janela_d1.var_pct)}%`;", "document.getElementById(`tab-d1-${ch}`).innerText = fmtPct(cKpi.janela_d1.var_pct, true);")
html = html.replace("document.getElementById(`tab-d7-${ch}`).innerText = `${cKpi.janela_d7.var_pct >= 0 ? '+' : ''}${Math.round(cKpi.janela_d7.var_pct)}%`;", "document.getElementById(`tab-d7-${ch}`).innerText = fmtPct(cKpi.janela_d7.var_pct, true);")

# 3. Hero Cards
html = html.replace("pacingBadge.innerText = `${Math.round(pacing)}% PACING`;", "pacingBadge.innerText = `${fmtPct(pacing)} PACING`;")
html = html.replace("document.getElementById('card-curva-pct').innerText = `${Math.round(activeKpi.curva_peso_corte_pct || 0)}% do dia`;", "document.getElementById('card-curva-pct').innerText = `${fmtPct(activeKpi.curva_peso_corte_pct)} do dia`;")
html = html.replace("projBadge.innerText = `${Math.round(projPacing)}% DA META`;", "projBadge.innerText = `${fmtPct(projPacing)} DA META`;")

# 4. Janelas
html = html.replace("document.getElementById('win-badge-d1').innerText = `${j1.var_pct >= 0 ? '+' : ''}${Math.round(j1.var_pct)}%`;", "document.getElementById('win-badge-d1').innerText = fmtPct(j1.var_pct, true);")
html = html.replace("document.getElementById('win-delta-d1').innerText = `${fmtBRLDelta(j1.var_rs)} (${j1.var_pct >= 0 ? '+' : ''}${Math.round(j1.var_pct)}%)`;", "document.getElementById('win-delta-d1').innerText = `${fmtBRLDelta(j1.var_rs)} (${fmtPct(j1.var_pct, true)})`;")

html = html.replace("document.getElementById('win-badge-d7').innerText = `${j7.var_pct >= 0 ? '+' : ''}${Math.round(j7.var_pct)}%`;", "document.getElementById('win-badge-d7').innerText = fmtPct(j7.var_pct, true);")
html = html.replace("document.getElementById('win-delta-d7').innerText = `${fmtBRLDelta(j7.var_rs)} (${j7.var_pct >= 0 ? '+' : ''}${Math.round(j7.var_pct)}%)`;", "document.getElementById('win-delta-d7').innerText = `${fmtBRLDelta(j7.var_rs)} (${fmtPct(j7.var_pct, true)})`;")

html = html.replace("document.getElementById('win-badge-m7').innerText = `${jm7.var_pct >= 0 ? '+' : ''}${Math.round(jm7.var_pct)}%`;", "document.getElementById('win-badge-m7').innerText = fmtPct(jm7.var_pct, true);")
html = html.replace("document.getElementById('win-delta-m7').innerText = `${fmtBRLDelta(jm7.var_rs)} (${jm7.var_pct >= 0 ? '+' : ''}${Math.round(jm7.var_pct)}%)`;", "document.getElementById('win-delta-m7').innerText = `${fmtBRLDelta(jm7.var_rs)} (${fmtPct(jm7.var_pct, true)})`;")

# 5. Cockpit Ruptura
html = html.replace("document.getElementById('kpi-est-pct-ruptura').innerText = `${est.pct_impacto_estoque || 65}% DO GAP`;", "document.getElementById('kpi-est-pct-ruptura').innerText = `${fmtPct(est.pct_impacto_estoque || 65)} DO GAP`;")
html = html.replace("document.getElementById('kpi-est-pct-comercial').innerText = `${est.pct_comercial || 35}% DO GAP`;", "document.getElementById('kpi-est-pct-comercial').innerText = `${fmtPct(est.pct_comercial || 35)} DO GAP`;")
html = html.replace("const pctQtd = Math.round(((est.qtd_top_desabastecidos || 10) / (est.total_top_avaliados || 30)) * 100);\n        document.getElementById('kpi-est-tag-qtd').innerText = `${pctQtd}% DOS TOP`;", "const pctQtd = ((est.qtd_top_desabastecidos || 10) / (est.total_top_avaliados || 30)) * 100;\n        document.getElementById('kpi-est-tag-qtd').innerText = `${fmtPct(pctQtd)} DOS TOP`;")

# 6. Radar de Mix
html = html.replace("document.getElementById('mix-share-real-mkp').innerText = `${mkpMix.share_realizado_pct || 0}%`;", "document.getElementById('mix-share-real-mkp').innerText = fmtPct(mkpMix.share_realizado_pct);")
html = html.replace("document.getElementById('mix-share-meta-mkp').innerText = `${mkpMix.share_meta_pct || 0}%`;", "document.getElementById('mix-share-meta-mkp').innerText = fmtPct(mkpMix.share_meta_pct);")
html = html.replace("document.getElementById('mix-badge-mkp').innerText = `${mkpMix.share_diff_pp >= 0 ? '+' : ''}${Math.round(mkpMix.share_diff_pp * 10) / 10} p.p.`;", "document.getElementById('mix-badge-mkp').innerText = `${fmtPct(mkpMix.share_diff_pp, true).replace('%', ' p.p.')}`;")

html = html.replace("document.getElementById('mix-share-real-app').innerText = `${appMix.share_realizado_pct || 0}%`;", "document.getElementById('mix-share-real-app').innerText = fmtPct(appMix.share_realizado_pct);")
html = html.replace("document.getElementById('mix-share-meta-app').innerText = `${appMix.share_meta_pct || 0}%`;", "document.getElementById('mix-share-meta-app').innerText = fmtPct(appMix.share_meta_pct);")
html = html.replace("document.getElementById('mix-badge-app').innerText = `${appMix.share_diff_pp >= 0 ? '+' : ''}${Math.round(appMix.share_diff_pp * 10) / 10} p.p.`;", "document.getElementById('mix-badge-app').innerText = `${fmtPct(appMix.share_diff_pp, true).replace('%', ' p.p.')}`;")

html = html.replace("document.getElementById('mix-share-real-site').innerText = `${siteMix.share_realizado_pct || 0}%`;", "document.getElementById('mix-share-real-site').innerText = fmtPct(siteMix.share_realizado_pct);")
html = html.replace("document.getElementById('mix-share-meta-site').innerText = `${siteMix.share_meta_pct || 0}%`;", "document.getElementById('mix-share-meta-site').innerText = fmtPct(siteMix.share_meta_pct);")
html = html.replace("document.getElementById('mix-badge-site').innerText = `${siteMix.share_diff_pp >= 0 ? '+' : ''}${Math.round(siteMix.share_diff_pp * 10) / 10} p.p.`;", "document.getElementById('mix-badge-site').innerText = `${fmtPct(siteMix.share_diff_pp, true).replace('%', ' p.p.')}`;")

html = html.replace("document.getElementById('nobre-peso-badge').innerText = `${nobre.peso_curva_pct || 0}% do dia`;", "document.getElementById('nobre-peso-badge').innerText = `${fmtPct(nobre.peso_curva_pct)} do dia`;")

html = html.replace("document.getElementById('stack-real-mkp').innerText = `MKP ${Math.round(mkpMix.share_realizado_pct || 0)}%`;", "document.getElementById('stack-real-mkp').innerText = `MKP ${fmtPct(mkpMix.share_realizado_pct)}`;")
html = html.replace("document.getElementById('stack-real-app').innerText = `APP ${Math.round(appMix.share_realizado_pct || 0)}%`;", "document.getElementById('stack-real-app').innerText = `APP ${fmtPct(appMix.share_realizado_pct)}`;")
html = html.replace("document.getElementById('stack-real-site').innerText = `Site ${Math.round(siteMix.share_realizado_pct || 0)}%`;", "document.getElementById('stack-real-site').innerText = `Site ${fmtPct(siteMix.share_realizado_pct)}`;")
html = html.replace("document.getElementById('stack-meta-mkp').innerText = `MKP ${Math.round(mkpMix.share_meta_pct || 0)}%`;", "document.getElementById('stack-meta-mkp').innerText = `MKP ${fmtPct(mkpMix.share_meta_pct)}`;")
html = html.replace("document.getElementById('stack-meta-app').innerText = `APP ${Math.round(appMix.share_meta_pct || 0)}%`;", "document.getElementById('stack-meta-app').innerText = `APP ${fmtPct(appMix.share_meta_pct)}`;")
html = html.replace("document.getElementById('stack-meta-site').innerText = `Site ${Math.round(siteMix.share_meta_pct || 0)}%`;", "document.getElementById('stack-meta-site').innerText = `Site ${fmtPct(siteMix.share_meta_pct)}`;")

# 7. Velocímetros
html = html.replace("document.getElementById('gauge-corte-val').innerText = `${Math.round(pacing)}%`;", "document.getElementById('gauge-corte-val').innerText = fmtPct(pacing);")
html = html.replace("document.getElementById('gauge-eod-val').innerText = `${Math.round(projPacing)}%`;", "document.getElementById('gauge-eod-val').innerText = fmtPct(projPacing);")
html = html.replace("speedChip.innerText = `Ritmo: ${speedPct.toFixed(0)}% da meta/h`;", "speedChip.innerText = `Ritmo: ${fmtPct(speedPct)} da meta/h`;")

# 8. Tables
html = html.replace("${gapPct >= 0 ? '+' : ''}${Math.round(gapPct)}%", "${fmtPct(gapPct, true)}")

# 9. Tabela Horária
html = html.replace("<td>${Math.round(row.peso_d7_pct || 0)}%</td>", "<td>${fmtPct(row.peso_d7_pct)}</td>")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Applied 1-decimal-place percentage rule across all components in index.html!")
