@echo off
setlocal

chcp 65001 >nul
pushd "%~dp0"

echo [1/3] Syncing project dependencies...
uv sync --dev
if errorlevel 1 goto :failed

echo [2/3] Building standalone vrp.exe...
uv run pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name vrp ^
  --collect-all pymysql ^
  --collect-all psycopg2 ^
  --collect-submodules sqlalchemy.dialects.mysql ^
  --collect-submodules sqlalchemy.dialects.postgresql ^
  vrp\run.py
if errorlevel 1 goto :failed

echo [3/3] Verifying executable...
dist\vrp.exe --version
if errorlevel 1 goto :failed

echo.
echo Build completed: %CD%\dist\vrp.exe
popd
exit /b 0

:failed
echo.
echo Build failed with exit code %errorlevel%.
popd
exit /b 1
