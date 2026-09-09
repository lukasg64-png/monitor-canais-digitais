#!/usr/bin/env pwsh
# ============================================================================
#  INSTALAÇÃO AUTOMÁTICA — MONITOR ONLINE CANAIS DIGITAIS
#  Farmácias São João — Configuração do Task Scheduler
# ============================================================================
#  Registra duas tarefas no Windows Task Scheduler:
#  1. SaoJoao_MonitorOnline_Daemon: Servidor HTTP + Daemon de sync contínuo
#     → Inicia ao fazer login, se recupera de falhas, roda minimizado
#  2. SaoJoao_MonitorOnline_GitSync: Publicação no GitHub Pages a cada 15 min
#     → Garante que o dashboard online esteja sempre atualizado
# ============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python" }

$ServerScript = Join-Path $ScriptDir "server.py"
$UpdateBat = Join-Path $ScriptDir "atualizar_online.bat"
$LogDir = Join-Path $ScriptDir "logs"

Write-Host ""
Write-Host "=" * 75 -ForegroundColor Cyan
Write-Host "  INSTALAÇÃO DO SERVIÇO AUTOMÁTICO" -ForegroundColor Cyan
Write-Host "  Monitor Online Canais Digitais — Farmácias São João" -ForegroundColor Cyan
Write-Host "=" * 75 -ForegroundColor Cyan
Write-Host ""
Write-Host "  Diretório: $ScriptDir" -ForegroundColor Gray
Write-Host "  Python:    $PythonExe" -ForegroundColor Gray
Write-Host "  Servidor:  $ServerScript" -ForegroundColor Gray
Write-Host ""

if (-not (Test-Path $ServerScript)) {
    Write-Error "Arquivo server.py não encontrado em $ScriptDir"
    exit 1
}

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

# ============================================================================
# TAREFA 1: Daemon do Servidor HTTP + Sincronização Contínua
# ============================================================================
$TaskNameDaemon = "SaoJoao_MonitorOnline_Daemon"

Write-Host "📡 [1/2] Configurando Daemon do Servidor (porta 3000)..." -ForegroundColor Yellow

# Remove tarefa anterior se existir
$existingTask = Get-ScheduledTask -TaskName $TaskNameDaemon -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "  → Removendo tarefa anterior..." -ForegroundColor Gray
    Unregister-ScheduledTask -TaskName $TaskNameDaemon -Confirm:$false
}

# Ação: Rodar server.py minimizado via pythonw (sem janela de console)
# Fallback: python com start /min se pythonw não existir
$PythonDir = Split-Path $PythonExe
$PythonWExe = Join-Path $PythonDir "pythonw.exe"

if (Test-Path $PythonWExe) {
    # pythonw.exe roda sem janela de console — ideal para daemon
    $DaemonAction = New-ScheduledTaskAction `
        -Execute $PythonWExe `
        -Argument "`"$ServerScript`"" `
        -WorkingDirectory $ScriptDir
} else {
    # Fallback: cmd /c start /min para minimizar a janela
    $DaemonAction = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c start /min `"MonitorOnline`" `"$PythonExe`" `"$ServerScript`"" `
        -WorkingDirectory $ScriptDir
}

# Trigger: Ao fazer login do usuário atual
$DaemonTrigger = New-ScheduledTaskTrigger -AtLogOn
$DaemonTrigger.UserId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# Configurações: Não parar nunca, reiniciar em caso de falha
$DaemonSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Days 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

try {
    Register-ScheduledTask `
        -TaskName $TaskNameDaemon `
        -Action $DaemonAction `
        -Trigger $DaemonTrigger `
        -Settings $DaemonSettings `
        -Description "Servidor HTTP (porta 3000) e daemon de sincronizacao continua com Qlik Sense Enterprise para o Monitor Online Canais Digitais" `
        -Force | Out-Null

    Write-Host "  ✅ Tarefa '$TaskNameDaemon' registrada com sucesso!" -ForegroundColor Green
    Write-Host "  → Inicia automaticamente ao fazer login" -ForegroundColor Gray
    Write-Host "  → Reinicia em caso de falha (até 3 tentativas)" -ForegroundColor Gray
    Write-Host "  → Acesso local:  http://localhost:3000" -ForegroundColor Cyan
    Write-Host "  → Acesso na rede: http://$(hostname):3000" -ForegroundColor Cyan
} catch {
    Write-Warning "Não foi possível registrar a tarefa do daemon: $_"
    Write-Host "  💡 Tente executar este script como Administrador." -ForegroundColor Yellow
}

# ============================================================================
# TAREFA 2: Publicação no GitHub Pages (a cada 30 minutos — minutos :20 e :50)
# ============================================================================
$TaskNameGit = "SaoJoao_MonitorOnline_GitSync"

if (Test-Path $UpdateBat) {
    Write-Host ""
    Write-Host "🌐 [2/2] Configurando Publicação Automática no GitHub Pages (minutos :20 e :50)..." -ForegroundColor Yellow

    $existingGit = Get-ScheduledTask -TaskName $TaskNameGit -ErrorAction SilentlyContinue
    if ($existingGit) {
        Unregister-ScheduledTask -TaskName $TaskNameGit -Confirm:$false
    }

    # Também remove a tarefa antiga com nome diferente se existir
    $oldTask = Get-ScheduledTask -TaskName "MonitorOnlineCanaisDigitaisSync" -ErrorAction SilentlyContinue
    if ($oldTask) {
        Write-Host "  → Removendo tarefa antiga 'MonitorOnlineCanaisDigitaisSync'..." -ForegroundColor Gray
        Unregister-ScheduledTask -TaskName "MonitorOnlineCanaisDigitaisSync" -Confirm:$false
    }

    $GitAction = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c `"$UpdateBat`"" `
        -WorkingDirectory $ScriptDir

    # Inicia às 00:20 e repete a cada 30 min (disparando sempre nos minutos :20 e :50 de todas as horas)
    $GitTrigger = New-ScheduledTaskTrigger -Daily -At "00:20"
    $GitTrigger.Repetition = (
        New-ScheduledTaskTrigger -Once -At "00:20" `
            -RepetitionInterval (New-TimeSpan -Minutes 30) `
            -RepetitionDuration (New-TimeSpan -Days 1)
    ).Repetition

    $GitSettings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew

    try {
        Register-ScheduledTask `
            -TaskName $TaskNameGit `
            -Action $GitAction `
            -Trigger $GitTrigger `
            -Settings $GitSettings `
            -Description "Publicacao automatica a cada 30 min (minutos :20 e :50) do Monitor Online Canais Digitais no GitHub Pages" `
            -Force | Out-Null

        Write-Host "  ✅ Tarefa '$TaskNameGit' registrada com sucesso!" -ForegroundColor Green
        Write-Host "  → Executa a cada 30 min (sempre minuto :20 e minuto :50)" -ForegroundColor Gray
        Write-Host "  → URL Online: https://lukasg64-png.github.io/monitor-canais-digitais/" -ForegroundColor Cyan
    } catch {
        Write-Warning "Não foi possível registrar a tarefa do GitSync: $_"
    }
} else {
    Write-Host ""
    Write-Host "⏭️  [2/2] atualizar_online.bat não encontrado. GitSync não configurado." -ForegroundColor Gray
}

# ============================================================================
# INICIAR O DAEMON AGORA
# ============================================================================
Write-Host ""
Write-Host "=" * 75 -ForegroundColor Cyan
Write-Host "  🚀 INICIANDO O SERVIDOR DAEMON AGORA..." -ForegroundColor Yellow
Write-Host "=" * 75 -ForegroundColor Cyan

# Mata instâncias anteriores do server.py se existirem
$existingServers = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*server.py*" }
if ($existingServers) {
    Write-Host "  → Encerrando instâncias anteriores do server.py..." -ForegroundColor Gray
    $existingServers | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

# Inicia via Start-ScheduledTask para validar que a tarefa funciona
try {
    Start-ScheduledTask -TaskName $TaskNameDaemon
    Start-Sleep -Seconds 3
    $taskInfo = Get-ScheduledTask -TaskName $TaskNameDaemon
    if ($taskInfo.State -eq "Running") {
        Write-Host ""
        Write-Host "  ✅ SERVIDOR DAEMON INICIADO COM SUCESSO!" -ForegroundColor Green
        Write-Host ""
        Write-Host "  📊 Dashboard:     http://localhost:3000" -ForegroundColor Cyan
        Write-Host "  📡 API Status:    http://localhost:3000/api/status" -ForegroundColor Cyan
        Write-Host "  🔄 Sync Manual:   http://localhost:3000/api/sync (POST)" -ForegroundColor Cyan
        Write-Host "  🌐 GitHub Pages:  https://lukasg64-png.github.io/monitor-canais-digitais/" -ForegroundColor Cyan
    } else {
        Write-Host "  ⚠️  Tarefa em estado: $($taskInfo.State)" -ForegroundColor Yellow
        Write-Host "  → Tente iniciar manualmente: python server.py" -ForegroundColor Gray
    }
} catch {
    Write-Warning "Não foi possível iniciar via Task Scheduler: $_"
    Write-Host "  → Iniciando diretamente..." -ForegroundColor Gray
    if (Test-Path $PythonWExe) {
        Start-Process -FilePath $PythonWExe -ArgumentList "`"$ServerScript`"" -WorkingDirectory $ScriptDir
    } else {
        Start-Process -FilePath $PythonExe -ArgumentList "`"$ServerScript`"" -WorkingDirectory $ScriptDir -WindowStyle Minimized
    }
    Write-Host "  ✅ Servidor iniciado em background!" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" * 75 -ForegroundColor Green
Write-Host "  INSTALAÇÃO CONCLUÍDA!" -ForegroundColor Green
Write-Host "  O servidor agora inicia automaticamente ao fazer login." -ForegroundColor Green
Write-Host "  Para desinstalar: schtasks /Delete /TN SaoJoao_MonitorOnline_Daemon /F" -ForegroundColor Gray
Write-Host "=" * 75 -ForegroundColor Green
Write-Host ""
