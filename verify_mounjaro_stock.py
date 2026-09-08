import json
import sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

with open('data/intraday_monitor.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

da = d.get('detratores_alavancadores', {})
skus = da.get('skus', {})
all_skus = skus.get('all', [])
mounj = [s for s in all_skus if 'MOUNJARO' in s.get('nome', '').upper()]

print("=== MOUNJARO NO MONITOR DE CANAIS DIGITAIS ===")
for m in mounj:
    print(f"SKU: {m.get('sku_id')} | Nome: {m.get('nome')}")
    print(f"  • Estoque Rede Oficial: {m.get('saldo'):,} un")
    print(f"  • Densidade por Loja:   {m.get('un_por_loja')} un/loja (Base 1.259 lojas)")
    print(f"  • Status Estoque:       {m.get('status_estoque')}")
    print(f"  • Causa Raiz:           {m.get('causa_tipo')}")
    print(f"  • GAP vs D-7:           R$ {m.get('gap_d7_rs'):,.2f} ({m.get('gap_d7_pct')}%)")
    print(f"  • Preço São João:       R$ {m.get('nosso_preco')} | Menor Conc: R$ {m.get('menor_concorrente_preco')} ({m.get('menor_concorrente_rede')})")
    print()

st = d.get('storytelling', {})
print("=== STORYTELLING EXECUTIVO ===")
print("Auditoria Estoque:", st.get('auditoria_estoque'))
print("\nPrincipais Detratores:", st.get('principais_detratores'))

