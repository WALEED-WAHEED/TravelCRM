@echo off
echo ================================================================================
echo               NAHD TRAVELS - STARTING DEVELOPMENT SERVER
echo ================================================================================
echo.

cd /d "%~dp0"

echo Activating virtual environment and starting Django Server on port 8000...
call .venv\Scripts\activate.bat && python manage.py runserver

echo.
echo ================================================================================
echo                    IMPORTANT URLS TO ACCESS
echo ================================================================================
echo.
echo Member Portal:            http://127.0.0.1:8000/
echo Django Admin Panel:       http://127.0.0.1:8000/admin/
echo Backend API Docs:         http://127.0.0.1:8000/api/docs/
echo.
echo ================================================================================
echo                         TEST CREDENTIALS
echo ================================================================================
echo.
echo Username: admin
echo Password: admin123
echo Role: administrator/developer
echo.
echo ================================================================================
echo                    SERVER IS RUNNING
echo ================================================================================
echo.
echo Close this window to stop the server.
echo.
pause
