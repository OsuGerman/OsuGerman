# Osu Profile Checker

This repository contains a small Python tool to fetch and analyze osu! player profiles using the public API.

## Usage
1. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Set the `OSU_API_KEY` environment variable with your osu! API key.
3. Run `python osu_profile_checker.py` to start a small GUI where you can enter a username.

The tool reports basic profile stats, a rough improvement rate, the favourite beatmap creator and aggregated metrics from the player's best scores. When launched without arguments the program opens a window asking for the username and shows the results in a message box.

## Building a Windows executable
Run `build_exe.bat` to create a standalone `.exe` with PyInstaller. The output is placed inside the `dist` folder. The executable opens the same GUI without a console window.
