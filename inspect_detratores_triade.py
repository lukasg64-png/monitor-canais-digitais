import json

with open('data/intraday_monitor.json', 'r', encoding='utf-8') as f:
    m = json.load(f)

det = m['detratores_alavancadores']['skus']['detratores_top']
print(f"Total Top Detratores: {len(det)}")
print("=" * 80)

for i, d in enumerate(det):
    sku = d.get('sku_id')
    nome = d.get('nome', '')[:32]
    gap = d.get('gap_d7_rs', 0)
    saldo = d.get('saldo', 0)
    un_lj = d.get('un_por_loja', 0)
    monit = d.get('precifica_monitorado')
    status_preco = d.get('preco_status')
    spread = d.get('spread_pct')
    rede = d.get('menor_concorrente_rede')
    nosso = d.get('nosso_preco')
    menor = d.get('menor_concorrente_preco')
    causa_atual = d.get('causa_tipo')
    
    preco_info = f"{status_preco} (+{spread}% vs {rede})" if monit and status_preco == 'MAIS_CARO' else ("MONITORADO_OUTRO" if monit else "SEM_MONITORAMENTO")
    print(f"{i+1:02d}. SKU {sku:<9} | {nome:<32} | GAP: R$ {gap:>6.0f} | Estoque: {saldo:>5.0f}un ({un_lj:>4.2f}/lj) | Preço: {preco_info:<35} | Causa Atual: {causa_atual}")
