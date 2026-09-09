' ==============================================================================
' exec_silencioso.vbs — Executor Invisivel em Segundo Plano
' Executa qualquer comando ou script .bat/.cmd sem abrir janela de prompt preta.
' ==============================================================================
Dim WshShell, strCommand, i
Set WshShell = CreateObject("WScript.Shell")
strCommand = ""
For i = 0 To WScript.Arguments.Count - 1
    strCommand = strCommand & """" & WScript.Arguments(i) & """ "
Next
If Trim(strCommand) <> "" Then
    WshShell.Run Trim(strCommand), 0, False
End If
Set WshShell = Nothing
