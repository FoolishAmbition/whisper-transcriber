@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo Set up the project's Python environment as described in README.md.
    pause
    exit /b 1
)
if not defined WHISPER_CUDA_DLL_DIR set "WHISPER_CUDA_DLL_DIR=%LOCALAPPDATA%\Programs\Ollama\lib\ollama\cuda_v12"
if exist "%WHISPER_CUDA_DLL_DIR%\cublas64_12.dll" set "PATH=%WHISPER_CUDA_DLL_DIR%;%PATH%"
"venv\Scripts\python.exe" app.py
if errorlevel 1 pause
