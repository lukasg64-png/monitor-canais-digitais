import sys
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
import json

with open('data/intraday_monitor.json', 'r', encoding='utf-8') as f:
    m = json.load(f)

det = m['detratores_alavancadores']['skus']['detratores_top']

cat_counts = {"DUPLO": 0, "RUPTURA": 0, "PRECO": 0, "DEMANDA": 0}
cat_loss = {"DUPLO": 0.0, "RUPTURA": 0.0, "PRECO": 0.0, "DEMANDA": 0.0}

print("NOVA CLASSIFICAÇÃO DOS TOP 30 DETRATORES:")
print("-" * 85)

for d in det:
    gap = abs(d.get('gap_d7_rs', 0))
    saldo = d.get('saldo', 0)
    un_lj = d.get('un_por_loja', 0)
    monit = d.get('precifica_monitorado')
    status_p = d.get('preco_status')
    spread = d.get('spread_pct') or 0.0
    rede = d.get('menor_concorrente_rede')
    
    is_ruptura = (un_lj < 1.5 or saldo <= 0)
    is_caro = (monit and status_p == 'MAIS_CARO' and spread >= 5.0)
    
    if is_ruptura and is_caro:
        cat = "DUPLO"
        label = f"🚨 Duplo Detrator (Ruptura {un_lj:.2f}u/lj + Preço +{spread:.1f}% vs {rede})"
    elif is_ruptura:
        cat = "RUPTURA"
        label = f"🚨 Ruptura Logística ({un_lj:.2f} un/lj)"
    elif is_caro:
        cat = "PRECO"
        label = f"🏷️ Preço Desalinhado (+{spread:.1f}% vs {rede} | {un_lj:.1f}u/lj)"
    else:
        cat = "DEMANDA"
        label = f"📉 Demanda Normal ({un_lj:.1f} un/lj)"
        
    cat_counts[cat] += 1
    cat_loss[cat] += gap
    print(f"SKU {d['sku_id']} | GAP: -R$ {gap:>5.0f} | {label}")

total_loss = sum(cat_loss.values())
print("=" * 85)
print("RESUMO CONSOLIDADO:")
for k in ["DUPLO", "RUPTURA", "PRECO", "DEMANDA"]:
    pct = (cat_loss[k] / total_loss * 100) if total_loss > 0 else 0
    print(f"{k:<10}: {cat_counts[k]:2d} itens ({cat_counts[k]/len(det)*100:4.1f}%) | Perda: R$ {cat_loss[k]:>8.2f} ({pct:4.1f}%)")
