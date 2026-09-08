import json

with open('data/intraday_monitor.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

da = d.get('detratores_alavancadores', {})
skus_all = da.get('skus', {}).get('all', [])

print('--- TOP 15 DETRATORES SKUS ---')
top_det = sorted([s for s in skus_all if (s.get('gap_d7_rs') or 0) < 0], key=lambda x: x.get('gap_d7_rs') or 0)[:15]
for s in top_det:
    cod = s.get('codigo')
    nome = s.get('nome')
    gap = s.get('gap_d7_rs', 0)
    hoje = s.get('hoje_corte_rs', 0)
    d7 = s.get('d7_exp_corte_rs', 0)
    est = s.get('estoque_rede', 0)
    causa = s.get('causa_raiz')
    print(f"{cod} | {nome[:35]} | GAP: R$ {gap:,.2f} | Hoje: R$ {hoje:,.2f} | D7: R$ {d7:,.2f} | Est: {est} | {causa}")

print('\n--- TOP 10 DETRATORES LABS ---')
labs_all = da.get('laboratorios', {}).get('all', [])
top_labs_det = sorted([l for l in labs_all if (l.get('gap_d7_rs') or 0) < 0], key=lambda x: x.get('gap_d7_rs') or 0)[:10]
for l in top_labs_det:
    nome = l.get('nome')
    gap = l.get('gap_d7_rs', 0)
    hoje = l.get('hoje_corte_rs', 0)
    d7 = l.get('d7_exp_corte_rs', 0)
    print(f"{nome[:35]} | GAP: R$ {gap:,.2f} | Hoje: R$ {hoje:,.2f} | D7: R$ {d7:,.2f}")
