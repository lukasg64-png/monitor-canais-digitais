@echo off
chcp 65001 > nul
title Servidor Intranet - Monitor Online Canais Digitais - Farmacias Sao Joao
cls
echo ======================================================================
echo   MONITOR ONLINE CANAIS DIGITAIS — FARMACIAS SAO JOAO
echo   Iniciando Servidor HTTP Intranet e Daemon de Sincronizacao...
echo ======================================================================
echo.
echo   • URL Local:    http://localhost:3000
echo   • URL na Rede:  http://192.168.3.10:3000
echo.
echo   Compartilhe o link acima com diretores e equipe na rede corporativa!
echo   Pressione Ctrl + C para parar o servidor.
echo ======================================================================
echo.

start "" "http://localhost:3000"
python "server.py"
pause
