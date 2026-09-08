import json
import requests
import time

with open('data/intraday_monitor.json', 'r', encoding='utf-8') as f:
    monitor = json.load(f)

detratores_skus = monitor['detratores_alavancadores']['skus']['detratores_top']
print(f'Total de SKUs detratores no monitor: {len(detratores_skus)}')

client_key = 'R4mHz0Q7hv8bR1rr-eDAtAqPG-7MLVKhWs3p68UhLKNMjGBYMdPoBmI2fr-5AGU5w1cD'
secret_key = '3UKTjtvQYxUl7xFF7-fkuyzep_aq8TxxsG925xjV'

def get_auth_token():
    headers_auth = {
        'client_key': client_key,
        'secret_key': secret_key,
        'Accept': 'application/vnd.api+json',
        'Content-Type': 'application/vnd.api+json'
    }
    r = requests.get('http://api.precifica.com.br/authentication', headers=headers_auth, timeout=10)
    return r.json()['data']['token']

token = get_auth_token()
headers_api = {
    'Authorization': f'Bearer {token}',
    'Accept': 'application/vnd.api+json',
    'Content-Type': 'application/vnd.api+json'
}

found = []
token_time = time.time()

# Test the 30 top detratores
for i, d in enumerate(detratores_skus[:30]):
    sku = str(d['sku_id'])
    if time.time() - token_time > 35:
        token = get_auth_token()
        headers_api['Authorization'] = f'Bearer {token}'
        token_time = time.time()
        print('   [Token renovado]')

    url = f'http://api.precifica.com.br/platform/ecommerce/www.saojoaofarmacias.com.br/scan/last/{sku}'
    try:
        time.sleep(1.05)
        res = requests.get(url, headers=headers_api, timeout=10)
        res_json = res.json() if res.status_code == 200 else {}
        nome_short = d['nome'][:30]
        if res.status_code == 200 and res_json.get('success') and res_json.get('data'):
            item_data = res_json['data'][0]
            last_scan = item_data.get('last_scan', {}).get('data', [])
            
            # Análise de Preço: Nosso preço vs concorrentes
            nosso_preco = None
            concorrentes_precos = []
            for c in last_scan:
                dom = c.get('domain', '').lower()
                p = c.get('offer_price') or c.get('price')
                avail = c.get('availability') == 'available'
                if 'saojoao' in dom:
                    nosso_preco = p
                else:
                    if p is not None and avail:
                        concorrentes_precos.append({
                            'domain': c.get('domain'),
                            'price': p
                        })
            
            menor_concorrente = min([c['price'] for c in concorrentes_precos]) if concorrentes_precos else None
            maior_concorrente = max([c['price'] for c in concorrentes_precos]) if concorrentes_precos else None
            
            # Posição de competitividade
            comp_status = "N/A"
            diff_pct = None
            if nosso_preco and menor_concorrente:
                diff_pct = ((nosso_preco / menor_concorrente) - 1.0) * 100.0
                if diff_pct > 1.0:
                    comp_status = f"MAIS CARO (+{diff_pct:.1f}%)"
                elif diff_pct < -1.0:
                    comp_status = f"MAIS BARATO ({diff_pct:.1f}%)"
                else:
                    comp_status = "EMPATADO (0%)"
            
            found_info = {
                'sku': sku,
                'nome': d['nome'],
                'gap_d7_rs': d.get('impacto_d7_rs', 0),
                'saldo': d.get('saldo_atual_rede', 0),
                'un_loja': d.get('un_por_loja', 0),
                'nosso_preco': nosso_preco,
                'menor_concorrente': menor_concorrente,
                'comp_status': comp_status,
                'diff_pct': diff_pct,
                'total_concorrentes': len(concorrentes_precos),
                'details': last_scan
            }
            found.append(found_info)
            print(f"[{i+1}/30] SKU {sku:8} | {nome_short:30} | Nosso: R$ {nosso_preco} | Menor Conc: R$ {menor_concorrente} | {comp_status} | Conc: {len(concorrentes_precos)}")
        else:
            print(f"[{i+1}/30] SKU {sku:8} | {nome_short:30} | Nao monitorado na Precifica")
    except Exception as e:
        print(f"[{i+1}/30] SKU {sku:8} | Erro: {e}")

print(f"\nTotal de detratores encontrados na Precifica: {len(found)} de {len(detratores_skus[:30])}")
with open('test_precifica_detratores.json', 'w', encoding='utf-8') as f:
    json.dump(found, f, ensure_ascii=False, indent=2)
