# Osu Profile Checker

This repository contains a small Python tool to fetch and analyze osu! player profiles using the public API.

## Usage
1. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Set the `OSU_API_KEY` environment variable with your osu! API key.
3. Run `python osu_profile_checker.py` and enter a username when prompted.

The script reports basic profile stats, a rough improvement rate, the favourite beatmap creator and aggregated metrics from the player's best scores.

## Building a Windows executable
Run `build_exe.bat` to create a standalone `.exe` with PyInstaller. The output is placed inside the `dist` folder.
