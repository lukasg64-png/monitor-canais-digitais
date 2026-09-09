' ==============================================================================
' atualizar_online_silencioso.vbs
' Dispara a atualizacao do Monitor Online em segundo plano sem janela de prompt.
' ==============================================================================
Dim WshShell, strCurrentDir, strBatPath
Set WshShell = CreateObject("WScript.Shell")
strCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
strBatPath = strCurrentDir & "\atualizar_online.bat"
WshShell.Run """" & strBatPath & """", 0, False
Set WshShell = Nothing
