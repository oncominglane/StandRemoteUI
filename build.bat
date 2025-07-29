@echo off
rmdir /s /q build
rmdir /s /q dist
del gui_.spec
pyinstaller --onefile --noconsole gui.py
pause