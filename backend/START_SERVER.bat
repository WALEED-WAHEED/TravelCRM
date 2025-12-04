@echo off
echo ================================================================================
echo               NAHD TRAVELS BACKEND - STARTING SERVER
echo ================================================================================
echo.

cd /d "%~dp0"

echo Activating virtual environment...
call env\Scripts\activate.bat

echo.
echo Server starting at: http://127.0.0.1:8001/
echo.
echo ================================================================================
echo                    IMPORTANT URLS TO ACCESS
echo ================================================================================
echo.
echo API Documentation (Swagger): http://127.0.0.1:8001/api/docs/
echo Django Admin Panel:           http://127.0.0.1:8001/admin/
echo OpenAPI Schema:               http://127.0.0.1:8001/api/schema/
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
echo                    SERVER IS STARTING...
echo ================================================================================
echo.
echo Press CTRL+C to stop the server
echo.

python manage.py runserver

