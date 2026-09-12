"""
Extrator de Inteligência de Preços — API Precifica
Farmácias São João — Monitor Intraday de Canais Digitais

Autentica via JWT e extrai os preços monitorados de 9.005 produtos da São João
e de seus principais concorrentes (Panvel, Droga Raia, Nissei, Preço Popular, Amazon).
Salva os dados indexados por Código de Referência / SKU em data/precifica_cache.json.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CACHE_FILE = os.path.join(DATA_DIR, "precifica_cache.json")
KEYS_FILE = os.path.join(BASE_DIR, "chave API Precifica.txt")

DEFAULT_CLIENT_KEY = "R4mHz0Q7hv8bR1rr-eDAtAqPG-7MLVKhWs3p68UhLKNMjGBYMdPoBmI2fr-5AGU5w1cD"
DEFAULT_SECRET_KEY = "3UKTjtvQYxUl7xFF7-fkuyzep_aq8TxxsG925xjV"
DOMAIN = "www.saojoaofarmacias.com.br"
PLATFORM = "ecommerce"
BASE_URL = "http://api.precifica.com.br"

class PrecificaClient:
    def __init__(self, client_key=None, secret_key=None):
        self.client_key = client_key or DEFAULT_CLIENT_KEY
        self.secret_key = secret_key or DEFAULT_SECRET_KEY
        self.token = None
        self.token_obtained_at = 0

    def load_keys_from_file(self):
        if os.path.exists(KEYS_FILE):
            try:
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                lines = [l.strip() for l in content.splitlines() if l.strip()]
                for i, l in enumerate(lines):
                    if "ClientKey" in l and i + 1 < len(lines):
                        self.client_key = lines[i + 1]
                    elif "SecretKey" in l and i + 1 < len(lines):
                        self.secret_key = lines[i + 1]
            except Exception as e:
                print(f"[Precifica] Aviso ao ler chaves do arquivo: {e}")

    def authenticate(self):
        url = f"{BASE_URL}/authentication"
        headers = {
            "client_key": self.client_key,
            "secret_key": self.secret_key,
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json"
        }
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            if data.get("success") and "data" in data and "token" in data["data"]:
                self.token = data["data"]["token"]
                self.token_obtained_at = time.time()
                return self.token
        raise RuntimeError(f"Falha na autenticação Precifica: HTTP {res.status_code} - {res.text}")

    def get_valid_token(self):
        # Token da Precifica expira em 45 segundos; renovamos após 35 segundos
        if not self.token or (time.time() - self.token_obtained_at) > 35:
            self.authenticate()
        return self.token

    def get_headers(self):
        token = self.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json"
        }

    def fetch_products_page(self, page=1):
        url = f"{BASE_URL}/platform/{PLATFORM}/{DOMAIN}/scan/products?page={page}"
        headers = self.get_headers()
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 429:
            # Rate limit hit, espera intervalo indicado
            delay = int(res.headers.get("X-Ratelimit-Delay-Sec", 2))
            print(f"   [RateLimit] Aguardando {delay}s...")
            time.sleep(delay)
            return self.fetch_products_page(page)
        else:
            print(f"   [Erro] Página {page}: HTTP {res.status_code} - {res.text[:100]}")
            return None

    def fetch_sku_last_scan(self, sku_or_ref):
        url = f"{BASE_URL}/platform/{PLATFORM}/{DOMAIN}/scan/last/{sku_or_ref}"
        headers = self.get_headers()
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 429:
            delay = int(res.headers.get("X-Ratelimit-Delay-Sec", 2))
            time.sleep(delay)
            return self.fetch_sku_last_scan(sku_or_ref)
        return None


REDE_FARMACIA_MAP = {
    "panvel": "Panvel",
    "farmaciasnissei": "Farmácias Nissei",
    "nissei": "Farmácias Nissei",
    "precopopular": "Preço Popular",
    "drogaraia": "Droga Raia",
    "drogasil": "Drogasil",
    "paguemenos": "Pague Menos",
    "farmaciasassociadas": "Farmácias Associadas",
    "agafarma": "Agafarma",
    "ultrafarma": "Ultrafarma"
}

def parse_item_pricing(item):
    """Processa a estrutura de um item retornado pela Precifica e calcula métricas de competitividade."""
    sku_vtex = str(item.get("sku", "")).strip()
    ref_code = str(item.get("reference_code", "")).strip()
    title = item.get("title") or ""
    dept = item.get("department") or ""
    category = item.get("category") or ""
    brand = item.get("brand") or ""
    ean = item.get("ean") or ""

    last_scan = item.get("last_scan", {}).get("data", [])
    
    nosso_preco = None
    nosso_disp = False
    concorrentes = []

    for c in last_scan:
        dom = (c.get("domain") or "").lower().replace("www.", "").replace(".com.br", "").replace(".com", "")
        p = c.get("offer_price") or c.get("price")
        avail = (c.get("availability") == "available")
        sold_by = c.get("sold_by") or ""

        if "saojoao" in dom:
            nosso_preco = float(p) if p is not None else None
            nosso_disp = avail
        else:
            if p is not None and avail:
                is_farm = any(k in dom for k in REDE_FARMACIA_MAP)
                nome_formatado = REDE_FARMACIA_MAP.get(dom, "Amazon" if "amazon" in dom else dom.capitalize())
                
                # Checagem de anomalia de preço (>150% de spread vs nosso_preco se existir)
                is_anomalo = False
                if nosso_preco and nosso_preco > 0:
                    spread = abs(float(p) - nosso_preco) / nosso_preco
                    if spread > 1.5:
                        is_anomalo = True

                concorrentes.append({
                    "rede": dom,
                    "rede_nome": nome_formatado,
                    "preco": float(p),
                    "disponivel": True,
                    "sold_by": sold_by,
                    "is_farmacia": is_farm,
                    "is_anomalo": is_anomalo
                })

    concorrentes.sort(key=lambda x: x["preco"])
    
    # Menor farmácia concorrente direta (sem anomalia de pack)
    farmacias = [c for c in concorrentes if c["is_farmacia"] and not c["is_anomalo"]]
    if not farmacias:
        farmacias = [c for c in concorrentes if c["is_farmacia"]]
    menor_farmacia = farmacias[0] if farmacias else None

    # Menor geral
    menor_concorrente = concorrentes[0] if concorrentes else None
    
    # Menor concorrente para balanço (prioriza rede física de farmácia)
    ref_conc = menor_farmacia if menor_farmacia else menor_concorrente

    # Status de competitividade
    status = "SEM_CONCORRENTE"
    diff_pct = None
    diff_rs = None

    if nosso_preco and ref_conc:
        menor_p = ref_conc["preco"]
        diff_rs = round(nosso_preco - menor_p, 2)
        diff_pct = round(((nosso_preco / menor_p) - 1.0) * 100.0, 1)

        if diff_pct > 1.0:
            status = "MAIS_CARO"
        elif diff_pct < -1.0:
            status = "MAIS_BARATO"
        else:
            status = "EMPATADO"

    return {
        "sku_vtex": sku_vtex,
        "ref_code": ref_code,
        "title": title,
        "department": dept,
        "category": category,
        "brand": brand,
        "ean": ean,
        "nosso_preco": nosso_preco,
        "nosso_disponivel": nosso_disp,
        "total_concorrentes": len(concorrentes),
        "menor_concorrente_rede": ref_conc["rede_nome"] if ref_conc else (menor_concorrente["rede"] if menor_concorrente else None),
        "menor_concorrente_preco": ref_conc["preco"] if ref_conc else (menor_concorrente["preco"] if menor_concorrente else None),
        "menor_farmacia_rede": menor_farmacia["rede_nome"] if menor_farmacia else None,
        "menor_farmacia_preco": menor_farmacia["preco"] if menor_farmacia else None,
        "spread_pct": diff_pct,
        "spread_rs": diff_rs,
        "status": status,
        "anomalia_pack": bool(ref_conc and ref_conc.get("is_anomalo")),
        "concorrentes": concorrentes[:6]
    }


def calculate_competitor_loss_ranking(items_by_ref):
    """
    Calcula para qual concorrente mais estamos perdendo faturamento/margem.
    Agrupa os produtos monitorados onde a São João está mais cara.
    """
    ranking_map = {}
    
    for k, item in items_by_ref.items():
        if not isinstance(item, dict):
            continue
        nosso_p = item.get("nosso_preco")
        concs = item.get("concorrentes", [])
        if not nosso_p or not concs:
            continue
        for c in concs:
            c_preco = c.get("preco")
            c_raw = str(c.get("rede", "")).lower()
            is_farm = c.get("is_farmacia", any(k in c_raw for k in REDE_FARMACIA_MAP))
            c_rede = c.get("rede_nome") or REDE_FARMACIA_MAP.get(c_raw, "Amazon" if "amazon" in c_raw else c_raw.capitalize())
            
            if c_preco and c_preco < nosso_p:
                diff = round(nosso_p - c_preco, 2)
                diff_pct = round(((nosso_p / c_preco) - 1.0) * 100.0, 1)
                
                # Ignora discrepâncias extremas (>200% de diferença, indício forte de pack/kit incorreto)
                if diff_pct > 200:
                    continue
                    
                if c_rede not in ranking_map:
                    ranking_map[c_rede] = {
                        "rede": c_rede,
                        "is_farmacia": is_farm,
                        "skus_mais_baratos": 0,
                        "impacto_financeiro_estimado_rs": 0.0,
                        "maior_spread_pct": 0.0,
                        "exemplos_skus": []
                    }
                
                ranking_map[c_rede]["skus_mais_baratos"] += 1
                ranking_map[c_rede]["impacto_financeiro_estimado_rs"] += diff
                if diff_pct > ranking_map[c_rede]["maior_spread_pct"]:
                    ranking_map[c_rede]["maior_spread_pct"] = diff_pct
                
                if len(ranking_map[c_rede]["exemplos_skus"]) < 5:
                    ranking_map[c_rede]["exemplos_skus"].append({
                        "sku": item.get("ref_code") or item.get("sku_vtex"),
                        "titulo": item.get("title") or "Item",
                        "nosso_preco": nosso_p,
                        "concorrente_preco": c_preco,
                        "diff_rs": diff,
                        "diff_pct": diff_pct
                    })
                    
    ranking_list = list(ranking_map.values())
    ranking_list.sort(key=lambda x: (x["skus_mais_baratos"], x["impacto_financeiro_estimado_rs"]), reverse=True)
    return ranking_list


def sync_precifica_cache(max_pages=None, target_skus=None):
    """
    Sincroniza os dados da Precifica.
    Se target_skus for fornecido, faz varredura cirúrgica nesses SKUs.
    Caso contrário, varre as páginas do catálogo até max_pages (ou todas as 181 páginas).
    """
    client = PrecificaClient()
    client.load_keys_from_file()
    print("[Precifica] Autenticando na API Precifica...")
    client.authenticate()
    print("[Precifica] Autenticação realizada com sucesso!")

    # Carrega cache existente para atualização incremental
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
                cache = existing.get("items_by_ref", {})
                print(f"[Precifica] Cache existente carregado com {len(cache)} produtos.")
        except Exception as e:
            print(f"[Precifica] Aviso ao carregar cache prévio: {e}")

    total_catalog = 9005

    # Modo 1: Consulta direta a lista de SKUs específicos (Ultrarrápido: ~30s para 30 SKUs)
    if target_skus:
        print(f"[Precifica] Executando varredura direcionada em {len(target_skus)} SKUs alvo...")
        for i, sku in enumerate(target_skus):
            sku_str = str(sku).strip()
            time.sleep(1.05)
            res = client.fetch_sku_last_scan(sku_str)
            if res and res.get("success") and res.get("data"):
                item_data = res["data"][0]
                parsed = parse_item_pricing(item_data)
                key = parsed["ref_code"] or parsed["sku_vtex"] or sku_str
                cache[key] = parsed
                # Indexa também pelo código alternativo
                if parsed["ref_code"]:
                    cache[parsed["ref_code"]] = parsed
                if parsed["sku_vtex"]:
                    cache[parsed["sku_vtex"]] = parsed
                print(f"   [{i+1}/{len(target_skus)}] SKU {sku_str} sincronizado: {parsed['status']} (Nosso R$ {parsed['nosso_preco']} vs Menor R$ {parsed['menor_concorrente_preco']})")
            else:
                print(f"   [{i+1}/{len(target_skus)}] SKU {sku_str}: Não cadastrado na Precifica")

    # Modo 2: Varredura por catálogo paginado
    else:
        print("[Precifica] Consultando primeira página para detectar total de páginas do catálogo...")
        first_res = client.fetch_products_page(1)
        if not first_res or not first_res.get("success"):
            raise RuntimeError("Falha ao consultar primeira página da Precifica!")

        data1 = first_res.get("data", {})
        total_catalog = data1.get("total", 9005)
        limit = data1.get("limit", 50)
        calculated_pages = (total_catalog + limit - 1) // limit  # 181 páginas

        pages_to_fetch = max_pages or calculated_pages
        print(f"[Precifica] Catálogo oficial detectado: {total_catalog:,} produtos ({calculated_pages} páginas).")
        print(f"[Precifica] Iniciando varredura completa de {pages_to_fetch} páginas...")

        # Processa página 1
        scan1 = data1.get("scan", [])
        for item in scan1:
            parsed = parse_item_pricing(item)
            if parsed["ref_code"]:
                cache[parsed["ref_code"]] = parsed
            if parsed["sku_vtex"]:
                cache[parsed["sku_vtex"]] = parsed

        for page in range(2, pages_to_fetch + 1):
            time.sleep(1.05)
            res = client.fetch_products_page(page)
            if not res or not res.get("success"):
                print(f"   [Aviso] Falha na página {page}, pulando...")
                continue

            scan = res.get("data", {}).get("scan", [])
            if not scan:
                print(f"   Fim dos itens atingido na página {page}.")
                break

            for item in scan:
                parsed = parse_item_pricing(item)
                if parsed["ref_code"]:
                    cache[parsed["ref_code"]] = parsed
                if parsed["sku_vtex"]:
                    cache[parsed["sku_vtex"]] = parsed

            if page % 10 == 0 or page == pages_to_fetch:
                unique_so_far = len(set(v.get("ref_code") or k for k, v in cache.items()))
                print(f"   Progresso: Página {page}/{pages_to_fetch} ({page/pages_to_fetch*100:.1f}%) | {unique_so_far} produtos únicos indexados no cache.")
                # Salva checkpoint intermediário no disco
                try:
                    with open(CACHE_FILE, "w", encoding="utf-8") as f_chk:
                        json.dump({"summary": {"atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "total_produtos_indexados": unique_so_far}, "items_by_ref": cache}, f_chk, ensure_ascii=False)
                except Exception:
                    pass

    # Gera estatísticas consolidadas do cache
    unique_items = {}
    for k, v in cache.items():
        ref = v.get("ref_code") or k
        unique_items[ref] = v

    items_list = list(unique_items.values())
    com_concorrente = [i for i in items_list if i["status"] in ("MAIS_CARO", "MAIS_BARATO", "EMPATADO")]
    mais_caros = [i for i in com_concorrente if i["status"] == "MAIS_CARO"]
    mais_baratos = [i for i in com_concorrente if i["status"] == "MAIS_BARATO"]
    empatados = [i for i in com_concorrente if i["status"] == "EMPATADO"]

    spreads = [i["spread_pct"] for i in mais_caros if i["spread_pct"] is not None]
    spread_medio = round(sum(spreads) / len(spreads), 1) if spreads else 0.0

    # Ranking de agressividade dos concorrentes
    ranking_concorrentes = {}
    for i in com_concorrente:
        rede = i.get("menor_concorrente_rede")
        if rede:
            ranking_concorrentes[rede] = ranking_concorrentes.get(rede, 0) + 1

    ranking_ordenado = sorted(ranking_concorrentes.items(), key=lambda x: x[1], reverse=True)

    summary = {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "total_catalogo_precifica": total_catalog,
        "total_produtos_indexados": len(unique_items),
        "total_com_concorrencia_ativa": len(com_concorrente),
        "qtd_mais_caros": len(mais_caros),
        "pct_mais_caros": round((len(mais_caros) / len(com_concorrente) * 100), 1) if com_concorrente else 0.0,
        "qtd_mais_baratos": len(mais_baratos),
        "pct_mais_baratos": round((len(mais_baratos) / len(com_concorrente) * 100), 1) if com_concorrente else 0.0,
        "qtd_empatados": len(empatados),
        "pct_empatados": round((len(empatados) / len(com_concorrente) * 100), 1) if com_concorrente else 0.0,
        "spread_medio_sobrepreco_pct": spread_medio,
        "ranking_agressores": [{"rede": r[0], "itens_liderados": r[1]} for r in ranking_ordenado]
    }

    final_payload = {
        "summary": summary,
        "items_by_ref": cache
    }

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"[Precifica] SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!")
    print(f"   Arquivo gerado: {CACHE_FILE}")
    print(f"   Produtos indexados no cache: {len(unique_items):,} itens")
    print(f"   Produtos com concorrência ativa: {len(com_concorrente):,} itens")
    print(f"   Mais Caros: {summary['qtd_mais_caros']} ({summary['pct_mais_caros']}%) | Spread Médio: +{summary['spread_medio_sobrepreco_pct']}%")
    print(f"   Mais Baratos: {summary['qtd_mais_baratos']} ({summary['pct_mais_baratos']}%)")
    print(f"   Concorrente Mais Agressivo: {ranking_ordenado[0][0] if ranking_ordenado else 'N/A'}")
    print("=" * 70)
    return final_payload


if __name__ == "__main__":
    # Suporta passar --pages N ou --target-detratores
    max_p = None  # Padrão: None = busca TODAS as 181 páginas do catálogo completo!
    target = None

    if "--pages" in sys.argv:
        idx = sys.argv.index("--pages")
        if idx + 1 < len(sys.argv):
            max_p = int(sys.argv[idx + 1])

    if "--target-detratores" in sys.argv:
        # Carrega os top detratores do monitor atual para sincronização instantânea
        monitor_file = os.path.join(DATA_DIR, "intraday_monitor.json")
        if os.path.exists(monitor_file):
            with open(monitor_file, "r", encoding="utf-8") as f:
                m = json.load(f)
            det = m.get("detratores_alavancadores", {}).get("skus", {}).get("detratores_top", [])
            target = [d.get("sku_id") for d in det if d.get("sku_id")]
            print(f"[Precifica] Modo direcionado ativado com {len(target)} SKUs detratores.")

    sync_precifica_cache(max_pages=max_p, target_skus=target)
