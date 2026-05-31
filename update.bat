@echo off
title Game Fix Scraper - Update
cd /d "%~dp0"

echo ================================================
echo  Game Fix Scraper - Update Tool
echo ================================================
echo.

echo [1/3] Syncing new FreeTP games...
python main.py freetp
if errorlevel 1 (
    echo WARNING: FreeTP sync had issues, continuing anyway...
)

echo.
echo [2/3] Pushing updated database to GitHub...
git add site/games.db
git commit -m "FreeTP sync update [deploy]"
git push origin main

echo.
echo [3/3] Done! GitHub is now rebuilding the site.
echo Visit https://github.com/ShayneVi/onlinefix-analyzer/actions to watch progress.
echo The live site will be updated in a few minutes.
echo.
pause
