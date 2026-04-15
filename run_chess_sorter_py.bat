@echo off
rem -- Windows .bat to run ChessSorter from J:\CHESS -- [cite: 1]

rem Set script folder
set ROOT_DIR=E:\coding_workspaces\Python\ChessSorter

rem If 1st arg is provided, use it as source directory; 
if "%~1"=="" (
    set SRC_DIR=J:\CHESS 
) else (
    set SRC_DIR=%~1 
)

echo.
echo [CHESS SORTER] Running from %ROOT_DIR% with source %SRC_DIR% [cite: 3]
echo.

pushd "%ROOT_DIR%" || (
    echo ERROR: Cannot change directory to %ROOT_DIR% [cite: 4]
    pause
    exit /b 1 [cite: 4]
)

rem Directly call system python 
python main.py

pause