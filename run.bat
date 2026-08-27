@echo off
chcp 65001 >nul
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
python run.py
pause
