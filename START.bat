@echo off
echo ================================================
echo   Uttam Tailors Management System v2
echo ================================================
echo.
echo Starting Flask app...
start /B python run.py
timeout /t 3 /nobreak > nul
echo.
echo App running at: http://localhost:5000
echo.
echo To share on phone via ngrok:
echo   1. Download ngrok from https://ngrok.com/download
echo   2. Run: ngrok http 5000
echo   3. Use the https://xxxx.ngrok.io URL on your phone
echo.
start http://localhost:5000
pause
