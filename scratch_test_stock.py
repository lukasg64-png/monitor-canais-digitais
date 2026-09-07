import json, sys
sys.stdout.reconfigure(encoding='utf-8')
with open('data/intraday_monitor.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

skus = d['detratores_alavancadores']['skus']['detratores_top']
print(f"Top {len(skus)} Detratores:")
desabastecidos = []
for s in skus:
    saldo = s.get('saldo', 0)
    un_lj = s.get('un_por_loja', 0)
    gap = s.get('gap_d7_rs', 0)
    if un_lj < 1.5:
        desabastecidos.append(s)
    print(f"{s['sku_id']} | {s['nome'][:38]:<38} | Saldo: {saldo:>6.0f} | {un_lj:>5.2f} un/lj | GAP: R$ {gap:>10,.2f} | {s.get('status_estoque')}")

print(f"\nTotal desabastecidos (<1.5 un/lj): {len(desabastecidos)} de {len(skus)}")
dens_desab = sum(s.get('un_por_loja', 0) for s in desabastecidos) / len(desabastecidos) if desabastecidos else 0
print(f"Densidade Média nos Desabastecidos: {dens_desab:.2f} un/loja")
perda_desab = sum(abs(s.get('gap_d7_rs', 0)) for s in desabastecidos)
perda_total_top = sum(abs(s.get('gap_d7_rs', 0)) for s in skus)
print(f"Perda nos Desabastecidos: R$ {perda_desab:,.2f} de R$ {perda_total_top:,.2f} ({perda_desab/perda_total_top*100:.1f}%)")
