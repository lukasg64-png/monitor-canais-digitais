# setup_scheduler.ps1 — Registra a tarefa agendada no Windows Task Scheduler
# para atualizar o Monitor Online Canais Digitais a cada 30 minutos (minutos :20 e :50).

$TaskName = 'SaoJoao_MonitorOnline_GitSync'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) { $ScriptDir = (Get-Location).Path }
$BatPath = Join-Path $ScriptDir 'atualizar_online.bat'

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  CONFIGURACAO DE AGENDAMENTO AUTOMATICO (WINDOWS TASK SCHEDULER)" -ForegroundColor Cyan
Write-Host "  MONITOR ONLINE CANAIS DIGITAIS - FARMACIAS SAO JOAO" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Diretorio:  $ScriptDir"
Write-Host "Script:     $BatPath"
Write-Host "Frequencia: A cada 30 minutos (sempre minutos :20 e :50)"

if (-not (Test-Path $BatPath)) {
    Write-Error "Arquivo atualizar_online.bat nao encontrado em $ScriptDir"
    exit 1
}

# Remove tarefa antiga se existir
$oldTask = Get-ScheduledTask -TaskName 'MonitorOnlineCanaisDigitaisSync' -ErrorAction SilentlyContinue
if ($oldTask) {
    Unregister-ScheduledTask -TaskName 'MonitorOnlineCanaisDigitaisSync' -Confirm:$false
}

$VbsPath = Join-Path $ScriptDir 'exec_silencioso.vbs'
$Action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument "//B //Nologo `"$VbsPath`" `"$BatPath`"" -WorkingDirectory $ScriptDir

# Inicia as 00:20 com repeticao a cada 30 min (cobre o dia todo nos minutos :20 e :50)
$Trigger = New-ScheduledTaskTrigger -Daily -At '00:20'
$Trigger.Repetition = (New-ScheduledTaskTrigger -Once -At '00:20' -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 1)).Repetition

$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Sincronizacao automatica a cada 30 min (minutos :20 e :50) do Monitor Online Canais Digitais no GitHub Pages' -Force | Out-Null
    Write-Host "`n[OK] Tarefa '$TaskName' registrada com sucesso!" -ForegroundColor Green
    Write-Host "O monitor agora atualizara e publicara no GitHub nos minutos :20 e :50 de cada hora." -ForegroundColor Green
    Write-Host "Link Online: https://lukasg64-png.github.io/monitor-canais-digitais/" -ForegroundColor Cyan
} catch {
    Write-Warning "Nao foi possivel registrar a tarefa: $_"
}
