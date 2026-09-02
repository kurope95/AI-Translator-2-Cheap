' AI Translator 2 Codex Cheap - Silent Launcher
' Mirrors working Antigravity launcher pattern.

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
appUrl = "http://127.0.0.1:5030"

' Check if server is already running
On Error Resume Next
Set http = CreateObject("MSXML2.XMLHTTP")
http.Open "GET", appUrl, False
http.Send
serverRunning = (http.Status = 200)
On Error GoTo 0

If serverRunning Then
    WshShell.Run "cmd /c start """" """ & appUrl & """", 0, False
Else
    ' Start backend hidden, keep same working style as other project launcher
    WshShell.Run "cmd /c cd /d """ & scriptDir & """ && set AI_TRANSLATOR_PORT=5030 && (python app.py || py app.py)", 0, False

    ' Give server a moment to boot
    WScript.Sleep 2500

    ' Open browser
    WshShell.Run "cmd /c start """" """ & appUrl & """", 0, False
End If
