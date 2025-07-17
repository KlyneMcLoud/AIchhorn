@echo off
setlocal enabledelayedexpansion

:: Bildschirmtitel
title FLUIDster – Start über virtuelle Umgebung

:: Virtuelle Umgebung festlegen
set VENV_DIR=.venv
set PY_EXEC=%VENV_DIR%\Scripts\python.exe

:: Prüfungen
if not exist %VENV_DIR%\Scripts\activate.bat (
    echo Fehler: Virtuelle Umgebung '%VENV_DIR%' wurde nicht gefunden.
    echo Bitte zuerst erstellen mit: python -m venv %VENV_DIR%
    pause
    exit /b
)

if not exist FLUIDster.py (
    echo Fehler: Datei 'FLUIDster.py' nicht gefunden.
    echo Bitte ins Projektverzeichnis wechseln oder Datei anlegen.
    pause
    exit /b
)

:: Aktivieren und starten
call %VENV_DIR%\Scripts\activate.bat

echo Starte FLUIDster...
echo -------------------------------------
%PY_EXEC% FLUIDster.py

:: Aufräumen & warten
echo -------------------------------------
echo FLUIDster wurde beendet.
