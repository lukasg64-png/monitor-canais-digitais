import json

with open('data/intraday_raw.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

print("Keys in intraday_raw.json:", list(raw.keys()))
print("maxDataHora:", raw.get("maxDataHora"))
print("dataHoje:", raw.get("dataHoje"))
print("diaHoje:", raw.get("diaHoje"), "diaOntem:", raw.get("diaOntem"), "diaD7:", raw.get("diaD7"))
print("rowsHoje count:", len(raw.get("rowsHoje", [])))
print("rowsOntem count:", len(raw.get("rowsOntem", [])))
print("Sample rowsOntem:", raw.get("rowsOntem", [])[:5])

# Let's sum rowsOntem
total_ontem = sum(r[2] for r in raw.get("rowsOntem", []) if len(r) > 2 and isinstance(r[2], (int, float)))
print("Total Ontem Receita Líquida:", total_ontem)

total_hoje = sum(r[2] for r in raw.get("rowsHoje", []) if len(r) > 2 and isinstance(r[2], (int, float)))
print("Total Hoje Receita Líquida:", total_hoje)
