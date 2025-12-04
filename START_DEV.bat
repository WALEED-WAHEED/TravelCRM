@echo off
echo ================================================================================
echo               NAHD TRAVELS - STARTING FRONTEND AND BACKEND
echo ================================================================================
echo.

cd /d "%~dp0"

REM Start Backend Server
echo Starting Backend Server on port 8001...
start "NAHD Travels Backend" cmd /k "cd backend && call venv\Scripts\activate.bat && python manage.py runserver 8001"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start Frontend Server
echo Starting Frontend Server on port 9006...
start "NAHD Travels Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ================================================================================
echo                    IMPORTANT URLS TO ACCESS
echo ================================================================================
echo.
echo Backend API:              http://127.0.0.1:8001/
echo Backend API Docs:         http://127.0.0.1:8001/api/docs/
echo Django Admin Panel:       http://127.0.0.1:8001/admin/
echo.
echo Frontend Application:     http://127.0.0.1:9006/
echo.
echo ================================================================================
echo                         TEST CREDENTIALS
echo ================================================================================
echo.
echo Username: admin
echo Password: admin123
echo Role: developer
echo.
echo ================================================================================
echo                    SERVERS ARE STARTING...
echo ================================================================================
echo.
echo Two separate windows have been opened for Backend and Frontend.
echo Close those windows to stop the servers.
echo.
pause

