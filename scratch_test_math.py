import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('data/intraday_monitor.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

hourly_curve = data.get('hourly_curve', [])
kpis = data.get('kpis', {})
meta = data.get('metadata', {})
corte_timestamp = meta.get('corte_timestamp', '')
corte_hora = meta.get('corte_hora', '15:53')

print(f"Corte timestamp: {corte_timestamp}, Corte hora: {corte_hora}")

# Extract current cut-off minutes if available
corte_min_float = 15.0
if ':' in str(corte_hora):
    parts = str(corte_hora).split(':')
    corte_min_float = int(parts[0]) + int(parts[1]) / 60.0

print(f"Corte exact time: {corte_min_float:.3f}")

for ch in ['Total', 'APP', 'Site', 'MKP']:
    kpi = kpis.get(ch, {})
    meta_dia = kpi.get('meta_dia', 0)
    realizado = kpi.get('realizado_hoje', 0)
    proj_eod = kpi.get('projecao_eod', 0)
    speed_atual = kpi.get('run_rate_atual_hora', 0)
    speed_req = kpi.get('run_rate_necessario_hora', 0)
    pct_meta = (realizado / meta_dia * 100) if meta_dia else 0
    
    print(f"\n================ Canal: {ch} ================")
    print(f"Realizado: R$ {realizado:,.2f} ({pct_meta:.1f}% da Meta R$ {meta_dia:,.2f})")
    print(f"Projeção EOD: R$ {proj_eod:,.2f}")
    print(f"Velocidade Atual: R$ {speed_atual:,.2f}/h | Necessária: R$ {speed_req:,.2f}/h")
    
    # 1. Check if already reached
    if realizado >= meta_dia and meta_dia > 0:
        exact_h = None
        for i, pt in enumerate(hourly_curve):
            acc = pt['accum_hoje'].get(ch, 0)
            if acc >= meta_dia:
                prev_acc = hourly_curve[i-1]['accum_hoje'].get(ch, 0) if i > 0 else 0
                step = acc - prev_acc
                frac = (meta_dia - prev_acc) / step if step > 0 else 0
                exact_h = (i - 1) + frac if i > 0 else frac
                break
        
        hours = int(exact_h)
        mins = int(round((exact_h - hours) * 60))
        if mins == 60:
            hours += 1
            mins = 0
        print(f"STATUS: ALREADY REACHED at {hours:02d}:{mins:02d} (exact={exact_h:.2f})")
    elif proj_eod >= meta_dia and meta_dia > 0:
        # Find exact hour where accum_proj_base >= meta_dia
        exact_h = None
        for i, pt in enumerate(hourly_curve):
            proj_acc = pt['accum_proj_base'].get(ch, 0)
            if proj_acc >= meta_dia:
                prev_acc = hourly_curve[i-1]['accum_proj_base'].get(ch, 0) if i > 0 else 0
                step = proj_acc - prev_acc
                frac = (meta_dia - prev_acc) / step if step > 0 else 0
                exact_h = (i - 1) + frac if i > 0 else frac
                break
        hours = int(exact_h)
        mins = int(round((exact_h - hours) * 60))
        if mins == 60:
            hours += 1
            mins = 0
        
        # Remaining time from cut-off
        rem_min = int(round((exact_h - corte_min_float) * 60))
        if rem_min < 0:
            rem_min = 0
        rem_h = rem_min // 60
        rem_m = rem_min % 60
        rem_str = f"{rem_h}h {rem_m:02d}min" if rem_h > 0 else f"{rem_m}min"
        
        # Gap
        gap_val = meta_dia - realizado
        
        print(f"STATUS: PROJECTED at ~{hours:02d}:{mins:02d} (em aprox. {rem_str}) - Faltam R$ {gap_val:,.2f} para 100%")
    else:
        gap_val = meta_dia - proj_eod
        print(f"STATUS: NOT REACHED (Projeção EOD: R$ {proj_eod:,.2f} ({proj_eod/meta_dia*100:.1f}%), Déficit final: R$ {gap_val:,.2f})")
