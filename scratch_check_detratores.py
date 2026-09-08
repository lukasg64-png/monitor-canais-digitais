import json

with open('data/intraday_monitor.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

skus = d.get('detratores_alavancadores', {}).get('skus', {}).get('all', [])
det = [s for s in skus if (s.get('gap_d7_rs') or 0) < 0]
det.sort(key=lambda x: x.get('gap_d7_rs') or 0)

print(f'Total detratores: {len(det)}')
reprec = [s for s in det if s.get('causa_tipo') == 'PRECO_DESALINHADO']
rupt = [s for s in det if s.get('causa_tipo') in ('RUPTURA_LOGISTICA', 'RUPTURA_ZERO', 'RUPTURA_CAPILAR', 'ESTOQUE_RESTRITO')]
duplo = [s for s in det if s.get('causa_tipo') == 'DUPLO_DETRATOR']
comercial = [s for s in det if s.get('causa_tipo') == 'DEMANDA_COMERCIAL']

sum_reprec = sum(abs(s.get('gap_d7_rs', 0)) for s in reprec)
sum_rupt = sum(abs(s.get('gap_d7_rs', 0)) for s in rupt)
sum_duplo = sum(abs(s.get('gap_d7_rs', 0)) for s in duplo)
sum_comercial = sum(abs(s.get('gap_d7_rs', 0)) for s in comercial)

print(f'Preco desalinhado: {len(reprec)} | Perda: R$ {sum_reprec:,.2f}')
print(f'Ruptura logistica: {len(rupt)} | Perda: R$ {sum_rupt:,.2f}')
print(f'Duplo detrator: {len(duplo)} | Perda: R$ {sum_duplo:,.2f}')
print(f'Demanda comercial: {len(comercial)} | Perda: R$ {sum_comercial:,.2f}')

print('\nTop 8 Preco Desalinhado (Estoque alto e preco mais caro):')
for s in reprec[:8]:
    print(f"  {s.get('sku_id')} - {s.get('nome')[:35]} | Gap: R$ {s.get('gap_d7_rs',0):,.2f} | Est: {s.get('saldo')} ({s.get('un_por_loja')} u/lj) | SJ R$ {s.get('nosso_preco')} vs {s.get('menor_concorrente_rede')} R$ {s.get('menor_concorrente_preco')} (+{s.get('spread_pct')}%)")

print('\nTop 8 Ruptura Logistica (Estoque critico < 1.5 u/lj):')
for s in rupt[:8]:
    print(f"  {s.get('sku_id')} - {s.get('nome')[:35]} | Gap: R$ {s.get('gap_d7_rs',0):,.2f} | Est: {s.get('saldo')} ({s.get('un_por_loja')} u/lj) | Preco status: {s.get('preco_status')}")

print('\nTop 8 Demanda Comercial (Estoque alto e preco alinhado/sem concorrencia):')
for s in comercial[:8]:
    print(f"  {s.get('sku_id')} - {s.get('nome')[:35]} | Gap: R$ {s.get('gap_d7_rs',0):,.2f} | Est: {s.get('saldo')} ({s.get('un_por_loja')} u/lj) | Preco status: {s.get('preco_status')} | SJ: {s.get('nosso_preco')}")
