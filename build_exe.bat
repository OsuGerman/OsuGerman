@echo off
REM Simple helper script to build a standalone executable
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --clean osu_profile_checker.py
