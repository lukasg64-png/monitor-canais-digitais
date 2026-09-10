import json

with open('data/intraday_raw.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

print("rowsSKUs count:", len(raw.get("rowsSKUs", [])))
if raw.get("rowsSKUs"):
    print("Sample rowsSKUs:", raw["rowsSKUs"][:3])

print("stockMap count:", len(raw.get("stockMap", {})))
if raw.get("stockMap"):
    sample_key = list(raw["stockMap"].keys())[0]
    print("Sample stockMap item:", sample_key, raw["stockMap"][sample_key])
