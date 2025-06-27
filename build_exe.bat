@echo off
REM Simple helper script to build a standalone executable
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --noconsole --clean osu_profile_checker.py
