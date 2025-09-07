@echo off
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

echo.
echo 2. Adding all files to Git repository...
git add .

echo.
echo 3. Creating initial commit...
git commit -m "feat: initial commit - Finance Manager v1.0.0

- Complete stock portfolio management system
- Financial calculation engine with precision formatting
- Enhanced UI with modern styling
- Comprehensive database integration
- VS Code workspace configuration
- Documentation and CI/CD setup"

echo.
echo 4. Repository is ready for GitHub!
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
echo    - Do NOT initialize with README (we already have one)
echo.
echo 2. Add GitHub as remote origin:
echo    git remote add origin https://github.com/YOUR_USERNAME/FinanceManager.git
echo.
echo 3. Push to GitHub:
echo    git branch -M main
echo    git push -u origin main
echo.
echo 4. Optional: Create development branch:
echo    git checkout -b develop
echo    git push -u origin develop
echo.
echo Repository setup complete!
echo.

pause
