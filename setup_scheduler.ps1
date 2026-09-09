# setup_scheduler.ps1 — Registra a tarefa agendada no Windows Task Scheduler
# para atualizar o Monitor Online Canais Digitais continuamente (a cada 15 minutos).

$TaskName = "MonitorOnlineCanaisDigitaisSync"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatPath = Join-Path $ScriptDir "atualizar_online.bat"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  CONFIGURAÇÃO DE AGENDAMENTO AUTOMÁTICO (WINDOWS TASK SCHEDULER)" -ForegroundColor Cyan
Write-Host "  MONITOR ONLINE CANAIS DIGITAIS — FARMÁCIAS SÃO JOÃO" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Diretório: $ScriptDir"
Write-Host "Script:    $BatPath"
Write-Host "Frequência: A cada 15 minutos durante o dia"

if (-not (Test-Path $BatPath)) {
    Write-Error "Arquivo atualizar_online.bat não encontrado em $ScriptDir"
    exit 1
}

$VbsPath = Join-Path $ScriptDir "exec_silencioso.vbs"
$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B //Nologo `"$VbsPath`" `"$BatPath`"" -WorkingDirectory $ScriptDir
$Trigger = New-ScheduledTaskTrigger -Daily -At "06:00"
$Trigger.Repetition = (New-ScheduledTaskTrigger -Once -At "06:00" -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Hours 18)).Repetition

$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Sincronizacao automatica a cada 15min do Monitor Online Canais Digitais no GitHub Pages" -Force | Out-Null
    Write-Host "`n✅ Tarefa '$TaskName' registrada com sucesso!" -ForegroundColor Green
    Write-Host "O monitor agora atualizará e publicará no GitHub a cada 15 minutos automaticamente." -ForegroundColor Green
    Write-Host "Link Online: https://lukasg64-png.github.io/monitor-canais-digitais/" -ForegroundColor Cyan
} catch {
    Write-Warning "Não foi possível registrar com privilégios de Administrador direto: $_"
    Write-Host "Você pode rodar atualizar_online.bat manualmente ou executar o PowerShell como Administrador." -ForegroundColor Yellow
}
