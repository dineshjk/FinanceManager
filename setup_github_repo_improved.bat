@echo off
setlocal enabledelayedexpansion

REM Finance Manager - GitHub Repository Setup Script
REM This script helps you set up the repository for GitHub

echo.
echo ========================================
echo   Finance Manager Repository Setup
echo ========================================
echo.

REM Check if Git is available
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)

echo 1. Checking Git repository status...
git status

REM Check if there are changes to commit
git diff-index --quiet HEAD -- 2>nul
set has_changes=%errorlevel%

git ls-files --others --exclude-standard | findstr . >nul 2>&1
set has_untracked=%errorlevel%

if %has_changes% equ 0 if %has_untracked% neq 0 (
    echo.
    echo Found untracked files. Adding to repository...
    git add .
    goto :do_commit
) else if %has_changes% neq 0 (
    echo.
    echo Found changes. Adding to repository...
    git add .
    goto :do_commit
) else (
    echo.
    echo No changes to commit. Repository is up to date.
    goto :check_remote
)

:do_commit
echo.
echo 2. Creating commit...
git commit -m "feat: initial commit - Finance Manager v1.0.0" -m "Complete stock portfolio management system with financial precision"
if %errorlevel% neq 0 (
    echo ERROR: Failed to create commit
    pause
    exit /b 1
)

:check_remote
echo.
echo 3. Checking remote repository configuration...
git remote get-url origin >nul 2>&1
if %errorlevel% equ 0 (
    echo Remote origin already configured:
    git remote -v
    echo.
    echo Repository appears to be ready for push!
    echo Run: git push -u origin main
) else (
    echo No remote repository configured yet.
    echo.
    echo ========================================
    echo   Next Steps:
    echo ========================================
    echo.
    echo 1. Create a new repository on GitHub:
    echo    - Go to https://github.com/new
    echo    - Repository name: FinanceManager
    echo    - Description: Desktop Stock Portfolio Management System
    echo    - Choose Public or Private
    echo    - Do NOT initialize with README
    echo.
    echo 2. Add GitHub as remote origin:
    echo    git remote add origin https://github.com/YOUR_USERNAME/FinanceManager.git
    echo.
    echo 3. Push to GitHub:
    echo    git branch -M main
    echo    git push -u origin main
)

echo.
echo ========================================
echo Repository setup complete!
echo ========================================
echo.

pause
