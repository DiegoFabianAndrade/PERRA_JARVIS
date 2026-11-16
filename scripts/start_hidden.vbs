' Script VBS para ejecutar PERRA_JARVIS en segundo plano sin ventana de consola
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectDir = fso.GetParentFolderName(scriptDir)

' Ejecuta python main.py en modo invisible (0) y sin esperar (False)
WshShell.CurrentDirectory = projectDir
WshShell.Run "pythonw.exe main.py", 0, False
