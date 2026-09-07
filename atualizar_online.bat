@echo off
pushd "%~dp0"
if not exist logs mkdir logs

set LOG=logs\auto_sync.log
echo. >> "%LOG%"
echo ====================================================================== >> "%LOG%"
echo [%date% %time%] INICIANDO ATUALIZACAO - MONITOR ONLINE CANAIS DIGITAIS >> "%LOG%"
echo ====================================================================== >> "%LOG%"

echo ======================================================================
echo INICIANDO ATUALIZACAO - MONITOR ONLINE CANAIS DIGITAIS
echo ======================================================================

echo [1/3] Sincronizando com Qlik Sense Enterprise via WebSocket...
python -u extract_intraday_qlik.py >> "%LOG%" 2>&1
if errorlevel 1 goto :erro

echo.
echo [2/3] Processando Inteligencia Intraday (Metas Excel, Curva e Detratores)...
python -u process_intraday_analytics.py >> "%LOG%" 2>&1
if errorlevel 1 goto :erro

echo.
echo [3/3] Publicando no GitHub Pages (Online para Diretoria)...
git add index.html data/*.json data/*.js *.py .github/workflows/*.yml >nul 2>&1
git diff --staged --quiet
if errorlevel 1 (
    git commit -m "Auto-sync Qlik Sense Intraday (%date% %time%)" >> "%LOG%" 2>&1
    git push github main --quiet >> "%LOG%" 2>&1
    git push github HEAD:gh-pages --quiet >> "%LOG%" 2>&1
    echo Atualizacoes enviadas para o GitHub Pages com sucesso!
    echo [%date% %time%] Atualizacoes enviadas com sucesso! >> "%LOG%"
) else (
    echo Nenhum dado novo para publicacao.
    echo [%date% %time%] Nenhum dado novo para publicacao. >> "%LOG%"
)

echo.
echo ======================================================================
echo ATUALIZACAO CONCLUIDA COM SUCESSO!
echo Dashboard Online: https://lukasg64-png.github.io/monitor-canais-digitais/
echo ======================================================================
echo [%date% %time%] ATUALIZACAO CONCLUIDA COM SUCESSO! >> "%LOG%"
popd
exit /b 0

:erro
echo.
echo ======================================================================
echo ERRO NA ATUALIZACAO DO MONITOR ONLINE
echo ======================================================================
echo [%date% %time%] ERRO NA ATUALIZACAO DO MONITOR ONLINE >> "%LOG%"
popd
exit /b 1
