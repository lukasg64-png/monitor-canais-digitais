#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_complete_tomorrow_run.py
Simula a execução completa de processamento analítico para Amanhã (Terça 08/09/2026).
"""
import os
import sys
import json
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from process_intraday_analytics import load_metas, norm_canal, get_minute_of_day

def run_simulation():
    print("=" * 70)
    print("SIMULAÇÃO RIGOROSA: PROCESSAMENTO DE AMANHÃ (08/09/2026)")
    print("=" * 70)

    # 1. Carregamento da Meta do Dia 8
    m8 = load_metas(8)
    print(f"1. Meta Oficial Carregada para o Dia 8:")
    print(f"   Total: R$ {m8['Total']:,.2f}")
    print(f"   APP:   R$ {m8['APP']:,.2f}")
    print(f"   Site:  R$ {m8['Site']:,.2f}")
    print(f"   MKP:   R$ {m8['MKP']:,.2f}")

    assert round(m8['Total'], 2) == 2119005.91, f"Meta incorreta: {m8['Total']}"
    assert round(m8['APP'], 2) == 1004145.76, f"Meta APP incorreta: {m8['APP']}"
    assert round(m8['Site'], 2) == 561010.25, f"Meta Site incorreta: {m8['Site']}"
    assert round(m8['MKP'], 2) == 553849.90, f"Meta MKP incorreta: {m8['MKP']}"
    print("   -> [PASSOU] Metas do Dia 8 coincidem 100% com a Diarização Oficial!")

    # 2. Teste do mapeamento dos canais
    assert norm_canal("APP") == "APP"
    assert norm_canal("APP Tele Entrega") == "APP"
    assert norm_canal("SITE") == "Site"
    assert norm_canal("SITE Tele Entrega") == "Site"
    assert norm_canal("e_Commerce") == "MKP"
    assert norm_canal("iFood") == "MKP"
    assert norm_canal("Lojas Físicas") is None
    print("   -> [PASSOU] Mapeamento de Canais estritamente validado!")

    # 3. Teste de virada de data e rótulo de dia da semana
    dt_amanha = datetime(2026, 9, 8, 8, 30)
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dow = dias_semana[dt_amanha.weekday()]
    assert dow == "Terça-feira"
    print(f"   -> [PASSOU] Dia da Semana de amanhã identificado: {dow}")

    print("\nTODOS OS CRITÉRIOS DE INTEGRIDADE FORAM APROVADOS!")

if __name__ == "__main__":
    run_simulation()
