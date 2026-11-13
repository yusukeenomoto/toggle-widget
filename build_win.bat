@echo off
rem Build dist\toggle-widget.exe on Windows
setlocal
cd /d "%~dp0"

py -3 -m venv .venv || goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade "pip>=26.2" || goto :error
python -m pip install -r requirements-build.txt || goto :error
pyinstaller --noconfirm --clean toggle-widget.spec || goto :error

echo Done: dist\toggle-widget.exe
exit /b 0

:error
echo Build failed.
exit /b 1
