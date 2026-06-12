@echo off
cd /d "%~dp0"
uv run python run_studio.py %*
