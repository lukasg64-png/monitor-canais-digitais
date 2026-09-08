import json

with open('test_precifica_detratores.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

print(f"Total de itens no JSON: {len(items)}")
competitor_counts = {}

for item in items:
    sku = item['sku']
    nome = item['nome']
    nosso = item['nosso_preco']
    menor = item['menor_concorrente']
    comp = item['comp_status']
    diff_pct = item.get('diff_pct')
    saldo = item.get('saldo', 0)
    un_loja = item.get('un_loja', 0)
    gap_rs = item.get('gap_d7_rs', 0)

    print(f"\n=== SKU {sku}: {nome} ===")
    print(f"  Venda GAP D-7: R$ {gap_rs:,.2f} | Saldo: {saldo:,.0f} un ({un_loja:.2f} un/loja)")
    print(f"  Preço São João: R$ {nosso} | Menor Concorrente: R$ {menor} | Spread: {comp}")
    
    details = item.get('details', [])
    for d in details:
        dom = d.get('domain', '').replace('www.', '').replace('.com.br', '')
        p = d.get('offer_price') or d.get('price')
        avail = 'disp' if d.get('availability') == 'available' else 'indisp'
        seller = d.get('sold_by') or ''
        if seller:
            seller = f" ({seller})"
        print(f"    - {dom:22}: R$ {p} [{avail}]{seller}")
        
        if 'saojoao' not in dom and p is not None and avail == 'disp':
            if dom not in competitor_counts:
                competitor_counts[dom] = {'menor_preco_count': 0, 'total_items': 0}
            competitor_counts[dom]['total_items'] += 1
            if p == menor:
                competitor_counts[dom]['menor_preco_count'] += 1

print("\n" + "="*60)
print("RANKING DE CONCORRENTES MAIS AGRESSIVOS EM PREÇO:")
print("="*60)
for dom, stats in sorted(competitor_counts.items(), key=lambda x: x[1]['menor_preco_count'], reverse=True):
    print(f"  - {dom:22}: Menor preço em {stats['menor_preco_count']} de {stats['total_items']} itens disputados")
