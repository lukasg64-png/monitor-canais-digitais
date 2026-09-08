import requests
import json
import time

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

departments = {}
competitor_domains = set()
total_products = 0

print("Consultando páginas da Precifica para mapear o catálogo...")
for page in range(1, 6):
    url = f'http://api.precifica.com.br/platform/ecommerce/www.saojoaofarmacias.com.br/scan/products?page={page}'
    time.sleep(1.05)
    res = requests.get(url, headers=headers_api, timeout=10)
    if res.status_code == 200:
        data = res.json().get('data', {})
        total_products = data.get('total', 9005)
        scan = data.get('scan', [])
        for item in scan:
            dept = item.get('department') or 'Outros'
            departments[dept] = departments.get(dept, 0) + 1
            for c in item.get('last_scan', {}).get('data', []):
                dom = c.get('domain')
                if dom:
                    competitor_domains.add(dom.replace('www.', ''))
    print(f"  Página {page} processada ({len(scan)} itens)")

print("\n" + "="*60)
print(f"TOTAL DE PRODUTOS MONITORADOS NA CONTA SÃO JOÃO: {total_products:,} itens")
print("="*60)
print("\nDepartamentos identificados na amostra:")
for dept, count in sorted(departments.items(), key=lambda x: x[1], reverse=True):
    print(f"  - {dept}: {count} itens")

print(f"\nConcorrentes monitorados identificados ({len(competitor_domains)} redes):")
for dom in sorted(competitor_domains):
    print(f"  - {dom}")
