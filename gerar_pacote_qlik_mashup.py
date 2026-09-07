#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_pacote_qlik_mashup.py — Gera o pacote .zip para importação oficial no Qlik Sense Enterprise
Importável via: QMC (Qlik Management Console) > Extensions > Import
URL final gerada: https://sense.farmaciassaojoao.com.br/extensions/monitor-canais-digitais/index.html
"""
import os, sys, zipfile
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_OUTPUT = os.path.join(BASE_DIR, "monitor-canais-digitais.zip")

FILES_TO_INCLUDE = [
    ("index.html", "index.html"),
    ("monitor-canais-digitais.qext", "monitor-canais-digitais.qext"),
    (os.path.join("data", "intraday_monitor.json"), "data/intraday_monitor.json"),
    (os.path.join("data", "intraday_data.js"), "data/intraday_data.js")
]

print("Criando pacote Mashup do Qlik Sense...")
with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as z:
    for src_rel, arc_name in FILES_TO_INCLUDE:
        full_src = os.path.join(BASE_DIR, src_rel)
        if os.path.exists(full_src):
            z.write(full_src, arc_name)
            print(f"  + Adicionado: {arc_name}")
        else:
            print(f"  ! Aviso: {src_rel} não encontrado")

print(f"\n✅ Pacote gerado com sucesso: {ZIP_OUTPUT}")
print("Passos para publicar no Qlik Sense:")
print("1. Acesse: https://sense.farmaciassaojoao.com.br/qmc")
print("2. No menu lateral, clique em 'Extensions'")
print("3. Clique no botão 'Import' no rodapé e selecione este arquivo: monitor-canais-digitais.zip")
print("4. Pronto! O dashboard ficará online em: https://sense.farmaciassaojoao.com.br/extensions/monitor-canais-digitais/index.html")
