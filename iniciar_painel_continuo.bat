@echo off
chcp 65001 > nul
cls
echo ===============================================================================
echo   PAINEL ONLINE EM TEMPO REAL - CANAIS DIGITAIS (FARMÁCIAS SÃO JOÃO)
echo   Iniciando Daemon de Monitoramento Contínuo (Qlik Sense Enterprise)
echo ===============================================================================
echo.

python "%~dp0auto_monitor_daemon.py"
pause
