#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAEMON DE MONITORAMENTO CONTÍNUO INTRADAY — FARMÁCIAS SÃO JOÃO
Verifica e extrai novas transações do Qlik Sense Enterprise periodicamente
(a cada atualização ou intervalo programado de N minutos) e reprocessa
a inteligência analítica em tempo real para alimentar o painel online.
"""

import os
import sys
import time
import asyncio
from datetime import datetime

# Garante importação dos módulos locais
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from extract_intraday_qlik import fetch_intraday_data
from process_intraday_analytics import process_analytics

INTERVAL_MINUTES = 10  # Intervalo de checagem contínua em minutos

async def run_daemon():
    print("=" * 75)
    print("  DAEMON DE MONITORAMENTO ONLINE CONTÍNUO — FARMÁCIAS SÃO JOÃO")
    print(f"  Ciclo de atualização: a cada {INTERVAL_MINUTES} minutos")
    print("  Pressione Ctrl + C para encerrar a qualquer momento")
    print("=" * 75)

    last_cut = None
    iteration = 1

    while True:
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        print(f"\n[{now_str}] 🔄 Ciclo #{iteration}: Consultando Qlik Sense Enterprise...")

        try:
            # 1. Extração no QIX Engine via WebSocket
            raw_data = await fetch_intraday_data()
            curr_cut = raw_data.get("maxDataHora")

            if curr_cut != last_cut:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✨ Novo corte detectado no Qlik Sense: {curr_cut}")
                last_cut = curr_cut
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️ Corte inalterado ({curr_cut}), atualizando projeções...")

            # 2. Processamento Analítico & Storytelling
            process_analytics()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Painel online atualizado com sucesso!")

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Erro no ciclo de atualização: {e}")

        iteration += 1
        sleep_secs = INTERVAL_MINUTES * 60
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Aguardando próximo ciclo em {INTERVAL_MINUTES} minutos...")
        await asyncio.sleep(sleep_secs)

if __name__ == "__main__":
    try:
        asyncio.run(run_daemon())
    except KeyboardInterrupt:
        print("\n\n🛑 Daemon de monitoramento finalizado pelo usuário.")
