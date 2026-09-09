#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py — Servidor HTTP Intranet & Daemon de Automação Contínua
Farmácias São João — Monitor Online Canais Digitais

1. Hospeda o dashboard na porta 3000 acessível em toda a rede interna da São João (0.0.0.0:3000).
2. Executa a sincronização contínua com o Qlik Sense Enterprise a cada N minutos em segundo plano.
3. Fornece endpoints REST:
   - GET /api/status -> Status do daemon, última sincronização e IP de rede
   - POST /api/sync  -> Dispara sincronização imediata no Qlik via browser/dashboard
"""

import os
import sys

# Quando executado via pythonw.exe (sem console), stdout/stderr são None.
# Redireciona para arquivo de log para evitar crash nos print().
if sys.stdout is None or sys.stderr is None:
    _log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(_log_dir, exist_ok=True)
    _log_file = open(os.path.join(_log_dir, 'server_daemon.log'), 'a', encoding='utf-8')
    sys.stdout = _log_file
    sys.stderr = _log_file

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

import time
import json
import socket
import threading
import subprocess
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
STATUS_FILE = os.path.join(DATA_DIR, 'daemon_status.json')
PORT = 3000
SYNC_TARGET_MINUTES = [20, 50]  # Atualização aos minutos :20 e :50 de cada hora

def get_seconds_until_next_sync():
    """Calcula quantos segundos faltam até o próximo minuto alvo (:20 ou :50)"""
    now = datetime.now()
    next_time = None
    for m in SYNC_TARGET_MINUTES:
        candidate = now.replace(minute=m, second=0, microsecond=0)
        if candidate > now:
            next_time = candidate
            break
    if next_time is None:
        next_hour = (now + timedelta(hours=1)).replace(minute=SYNC_TARGET_MINUTES[0], second=0, microsecond=0)
        next_time = next_hour
    diff = int((next_time - now).total_seconds())
    return max(1, diff)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "192.168.3.10"

LOCAL_IP = get_local_ip()

# Estado em memória do daemon
daemon_state = {
    "status": "ONLINE",
    "started_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    "last_sync": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    "last_corte": "14:54",
    "last_status": "Sucesso",
    "sync_count": 1,
    "is_syncing": False,
    "next_sync_in": get_seconds_until_next_sync(),
    "target_minutes": "20 e 50",
    "network_url": f"http://{LOCAL_IP}:{PORT}",
    "local_url": f"http://localhost:{PORT}"
}

if os.path.exists(STATUS_FILE):
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            _st = json.load(f)
            if isinstance(_st, dict):
                daemon_state.update(_st)
                daemon_state["status"] = "ONLINE"
                daemon_state["is_syncing"] = False
                daemon_state["next_sync_in"] = get_seconds_until_next_sync()
    except Exception:
        pass

def save_status():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(daemon_state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# Flag para garantir execução 100% invisível em background no Windows (sem abrir janelas de prompt/console)
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

def run_sync():
    """Executa a rotina de extração e processamento no Qlik Sense em segundo plano silencioso"""
    if daemon_state["is_syncing"]:
        return {"status": "already_running", "message": "Sincronização já em andamento."}
    
    daemon_state["is_syncing"] = True
    save_status()
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iniciando ciclo de sincronização com Qlik Sense...")
    
    try:
        # 1. Executa extração via WebSocket no Qlik Sense (100% silencioso / sem janela)
        ext_script = os.path.join(BASE_DIR, "extract_intraday_qlik.py")
        proc_ext = subprocess.run(
            [sys.executable, ext_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            creationflags=CREATE_NO_WINDOW
        )
        
        if proc_ext.returncode != 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ERRO na extração Qlik: {proc_ext.stderr or proc_ext.stdout}")
            daemon_state["last_status"] = f"Erro na extração ({proc_ext.returncode})"
            daemon_state["is_syncing"] = False
            save_status()
            return {"status": "error", "message": f"Falha na extração: {proc_ext.stderr[:200] if proc_ext.stderr else 'Erro'}"}
        
        # 2. Executa processamento analítico (100% silencioso / sem janela)
        proc_script = os.path.join(BASE_DIR, "process_intraday_analytics.py")
        proc_ana = subprocess.run(
            [sys.executable, proc_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            creationflags=CREATE_NO_WINDOW
        )
        if proc_ana.returncode != 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ERRO no processamento: {proc_ana.stderr or proc_ana.stdout}")
            daemon_state["last_status"] = f"Erro no processamento ({proc_ana.returncode})"
            daemon_state["is_syncing"] = False
            save_status()
            return {"status": "error", "message": "Falha no processamento analítico."}
        monitor_json = os.path.join(DATA_DIR, "intraday_monitor.json")
        corte_hora = "09:54"
        if os.path.exists(monitor_json):
            try:
                with open(monitor_json, "r", encoding="utf-8") as f:
                    mj = json.load(f)
                    corte_hora = mj.get("metadata", {}).get("corte_timestamp", corte_hora)
            except Exception:
                pass

        daemon_state["last_sync"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        daemon_state["last_corte"] = corte_hora
        daemon_state["last_status"] = "Sucesso"
        daemon_state["sync_count"] += 1
        save_status()
        
        # 4. Publica automaticamente no GitHub Pages (100% silencioso / sem janela)
        try:
            subprocess.run(
                ["git", "add", "index.html", "data", "process_intraday_analytics.py", "extract_intraday_qlik.py"],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                creationflags=CREATE_NO_WINDOW
            )
            diff_chk = subprocess.run(
                ["git", "diff", "--staged", "--quiet"],
                cwd=BASE_DIR,
                creationflags=CREATE_NO_WINDOW
            )
            if diff_chk.returncode != 0:
                now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                subprocess.run(
                    ["git", "commit", "-m", f"Auto-sync Qlik Sense Intraday ({now_str}) [Corte: {corte_hora}]"],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    creationflags=CREATE_NO_WINDOW
                )
                subprocess.run(
                    ["git", "push", "github", "main"],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                    creationflags=CREATE_NO_WINDOW
                )
                subprocess.run(
                    ["git", "push", "github", "HEAD:gh-pages"],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                    creationflags=CREATE_NO_WINDOW
                )
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Atualizações publicadas com sucesso no GitHub Pages!")
        except Exception as e_git:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Info Git Push: {e_git}")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Ciclo concluído! Corte Qlik: {corte_hora}")
        return {"status": "success", "last_sync": daemon_state["last_sync"], "corte": corte_hora}

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Erro na sincronização: {e}")
        daemon_state["last_status"] = f"Erro: {e}"
        return {"status": "error", "message": str(e)}
    finally:
        daemon_state["is_syncing"] = False
        save_status()

def background_daemon_worker():
    """Worker em segundo plano que sincroniza rigorosamente aos minutos :20 e :50 de cada hora"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Daemon contínuo iniciado. Sincronizações nos minutos :20 e :50 de cada hora.")
    while True:
        seconds_left = get_seconds_until_next_sync()
        while seconds_left > 0:
            daemon_state["next_sync_in"] = seconds_left
            time.sleep(1)
            seconds_left -= 1
        
        run_sync()
        time.sleep(2)

class IntranetRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(daemon_state, ensure_ascii=False).encode("utf-8"))
            return
        elif self.path in ["", "/"]:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/sync":
            res = run_sync()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def end_headers(self):
        # Desativa cache para garantir que atualizações do Qlik apareçam na hora
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        # Silencia logs de assets estáticos para manter o log limpo
        if "GET /api/" in format % args or "POST /api/" in format % args:
            super().log_message(format, *args)

def start_server():
    print("=" * 75)
    print("  SERVIDOR INTRANET & DAEMON DE MONITORAMENTO — FARMÁCIAS SÃO JOÃO")
    print(f"  • Acesso Local:     http://localhost:{PORT}")
    print(f"  • Acesso na Rede:   http://{LOCAL_IP}:{PORT} (Compartilhe com a equipe)")
    print(f"  • Intervalo Qlik:   Minutos :20 e :50 de cada hora (a cada 30 min)")
    print("=" * 75)

    # Inicia worker do daemon em thread separada
    daemon_thread = threading.Thread(target=background_daemon_worker, daemon=True)
    daemon_thread.start()

    # Inicia servidor HTTP
    server = ThreadingHTTPServer(("0.0.0.0", PORT), IntranetRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        server.server_close()

if __name__ == "__main__":
    start_server()
