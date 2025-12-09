@echo off
echo Starting Web Search Development Environment...
echo.
echo This will open 3 terminals:
echo   1. Meilisearch (port 7700)
echo   2. Python Backend (port 8000) - auto-reloads on changes
echo   3. Svelte Frontend (port 5173) - auto-reloads on changes
echo.
echo Press Ctrl+C in each terminal to stop.
echo.

:: Start Meilisearch with master key
start "Meilisearch" cmd /k "cd /d C:\Users\steph\documents\web-search && meilisearch.exe --db-path .\data\meilisearch --http-addr 127.0.0.1:7700 --master-key TBmZdGLVexFLTf6Pl1_JZoQt1e07aBt6z-vIF4ldTF8"

:: Wait a moment for Meilisearch to start
timeout /t 2 /nobreak > nul

:: Start Python Backend with auto-reload
start "Python Backend" cmd /k "cd /d C:\Users\steph\documents\web-search\src-python && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait a moment for backend to start
timeout /t 2 /nobreak > nul

:: Start Svelte Frontend (Vite has hot reload by default)
start "Svelte Frontend" cmd /k "cd /d C:\Users\steph\documents\web-search && npm run dev"

echo.
echo All services starting...
echo Open http://localhost:5173 in your browser.
echo.
