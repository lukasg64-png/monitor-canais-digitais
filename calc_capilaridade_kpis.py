import json, sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

with open('data/intraday_raw.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

TOTAL_LOJAS = 1147
items = []
for r in raw.get('rowsSKUs', []):
    sku = r[0]
    nome = r[1]
    hoje = float(r[2] or 0)
    d7 = float(r[4] or 0)
    saldo = float(r[5] or 0) if len(r) > 5 and r[5] not in [None, '-', 'NaN'] else 0.0
    gap = hoje - d7
    un_lj = saldo / TOTAL_LOJAS
    if gap < 0:
        items.append({
            'sku': sku,
            'nome': nome,
            'hoje': hoje,
            'd7': d7,
            'gap': gap,
            'saldo': saldo,
            'un_lj': un_lj
        })

items.sort(key=lambda x: x['gap'])
print(f"Total Detratores: {len(items)}")

total_gap_neg = sum(abs(x['gap']) for x in items)
gap_ruptura_severa = sum(abs(x['gap']) for x in items if x['un_lj'] < 0.5) # < 0.5 un/loja
gap_restrito = sum(abs(x['gap']) for x in items if 0.5 <= x['un_lj'] < 1.5) # 0.5 a 1.5 un/loja
gap_abastecido = sum(abs(x['gap']) for x in items if x['un_lj'] >= 1.5)

pct_severa = gap_ruptura_severa / total_gap_neg * 100 if total_gap_neg > 0 else 0
pct_restrito = gap_restrito / total_gap_neg * 100 if total_gap_neg > 0 else 0
pct_total_estoque = (gap_ruptura_severa + gap_restrito) / total_gap_neg * 100 if total_gap_neg > 0 else 0
pct_comercial = gap_abastecido / total_gap_neg * 100 if total_gap_neg > 0 else 0

print(f"Perda Total Detratores: R$ {total_gap_neg:,.2f}")
print(f"🚨 Ruptura Capilar Severa (<0.5 un/loja): R$ {gap_ruptura_severa:,.2f} ({pct_severa:.1f}%)")
print(f"⚠️ Estoque Restrito (0.5 a 1.5 un/loja):  R$ {gap_restrito:,.2f} ({pct_restrito:.1f}%)")
print(f"🔴 TOTAL IMPACTO ESTOQUE / RUPTURA:       R$ {(gap_ruptura_severa+gap_restrito):,.2f} ({pct_total_estoque:.1f}%)")
print(f"🟢 Perda Comercial / Demanda (>=1.5 un):  R$ {gap_abastecido:,.2f} ({pct_comercial:.1f}%)")

print("\n" + "=" * 95)
print("Top 15 Detratores com Unidades por Loja (Rede 1.147 Filiais):")
print("=" * 95)
for x in items[:15]:
    tipo = "🚨 RUPTURA SEVERA" if x['un_lj'] < 0.5 else ("⚠️ RESTRITO" if x['un_lj'] < 1.5 else "✅ ABASTECIDO")
    print(f"SKU {x['sku']} | {x['nome'][:32]:<32} | Saldo: {x['saldo']:>5.0f} un | {x['un_lj']:>4.2f} un/lj | GAP: R$ {x['gap']:>8,.0f} | {tipo}")
