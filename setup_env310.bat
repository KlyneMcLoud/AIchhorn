@echo off
setlocal

REM Pfade
set PYTHON310=D:\bin\dev\Python310
set VENV_DIR=.venv310

echo [1/6] Aktiviere Python 3.10...
if not exist "%PYTHON310%\python.exe" (
    echo ❌ Python 3.10 nicht gefunden unter %PYTHON310%
    echo ➜ Bitte installiere Python 3.10 von https://www.python.org/downloads/release/python-31013/
    pause
    exit /b 1
)

echo [2/6] Erstelle virtuelle Umgebung...
%PYTHON310%\python.exe -m venv %VENV_DIR%

echo [3/6] Aktiviere virtuelle Umgebung...
call %VENV_DIR%\Scripts\activate.bat

echo [4/6] Aktualisiere pip...
python -m pip install --upgrade pip

echo [5/6] Installiere Abhängigkeiten...
REM GPU-kompatibles PyTorch für CUDA 11.8 (GTX 1070)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

REM FLUIDster-relevante Pakete
pip install openai-whisper
pip install pydub qtpy PySide2 pyperclip urllib3 requests

echo [6/6] Starte FLUIDstar...
python FLUIDstar_mod.py

endlocal
