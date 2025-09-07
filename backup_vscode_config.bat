@echo off
echo Backing up VS Code configuration...

REM Create backup directory with timestamp
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD%_%HH%-%Min%-%Sec%"

set "BACKUP_DIR=vscode_backup_%timestamp%"
mkdir "%BACKUP_DIR%"

REM Backup workspace settings
echo Backing up workspace settings...
xcopy ".vscode" "%BACKUP_DIR%\.vscode" /E /I /Y

REM Backup global settings
echo Backing up global VS Code settings...
mkdir "%BACKUP_DIR%\User"
copy "%APPDATA%\Code\User\settings.json" "%BACKUP_DIR%\User\" 2>nul
copy "%APPDATA%\Code\User\keybindings.json" "%BACKUP_DIR%\User\" 2>nul
xcopy "%APPDATA%\Code\User\snippets" "%BACKUP_DIR%\User\snippets" /E /I /Y 2>nul

REM Backup extension list
echo Backing up extension list...
code --list-extensions > "%BACKUP_DIR%\extensions.txt"

echo.
echo Backup completed in: %BACKUP_DIR%
echo.
echo To restore:
echo 1. Copy .vscode folder to your project
echo 2. Copy User files to %%APPDATA%%\Code\User\
echo 3. Install extensions: code --install-extension ^<extension-name^>
echo.
pause
