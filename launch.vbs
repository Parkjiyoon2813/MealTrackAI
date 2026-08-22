Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Jiyoon\PROJECTS\MealTrackAI"
WshShell.Run """C:\Users\Jiyoon\PROJECTS\MealTrackAI\.venv\Scripts\pythonw.exe"" app.py", 0, False
