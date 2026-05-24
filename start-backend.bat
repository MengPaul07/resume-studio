@echo off
cd /d "D:\Repo\resume-builder"
echo Starting resume-builder backend (Windows) on port 8001...
call .venv\Scripts\activate.bat
python -m uvicorn src.main:app --host 127.0.0.1 --port 8001 --reload
pause
