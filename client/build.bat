@echo off
rmdir /s /q build
rmdir /s /q dist
del gui.spec
pyinstaller --onefile --noconsole gui_ws.py
pause