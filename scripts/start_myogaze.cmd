@echo off
cd /d "C:\Users\MELVIN\Projects\NeuroShift"
if not exist logs mkdir logs
"C:\Users\MELVIN\AppData\Local\Programs\Python\Python312\python.exe" -m src.neuroshift serve --host 0.0.0.0 --port 8000 >> logs\server.log 2>&1
