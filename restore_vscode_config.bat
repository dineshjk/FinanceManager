@echo off
echo Restoring VS Code configuration...

if "%1"=="" (
    echo Usage: restore_vscode_config.bat ^<backup_folder^>
    echo Example: restore_vscode_config.bat vscode_backup_2025-09-01_10-30-00
    pause
    exit /b 1
)

set "BACKUP_DIR=%1"

if not exist "%BACKUP_DIR%" (
    echo Error: Backup directory "%BACKUP_DIR%" not found!
    pause
    exit /b 1
)

echo Restoring from: %BACKUP_DIR%

REM Restore workspace settings
if exist "%BACKUP_DIR%\.vscode" (
    echo Restoring workspace settings...
    xcopy "%BACKUP_DIR%\.vscode" ".vscode" /E /I /Y
)

REM Restore global settings
if exist "%BACKUP_DIR%\User" (
    echo Restoring global VS Code settings...
    copy "%BACKUP_DIR%\User\settings.json" "%APPDATA%\Code\User\" 2>nul
    copy "%BACKUP_DIR%\User\keybindings.json" "%APPDATA%\Code\User\" 2>nul
    if exist "%BACKUP_DIR%\User\snippets" (
        xcopy "%BACKUP_DIR%\User\snippets" "%APPDATA%\Code\User\snippets" /E /I /Y 2>nul
    )
)

REM Install extensions
if exist "%BACKUP_DIR%\extensions.txt" (
    echo Installing extensions...
    for /f "delims=" %%i in (%BACKUP_DIR%\extensions.txt) do (
        echo Installing %%i...
        code --install-extension %%i
    )
)

echo.
echo Restore completed!
echo Please restart VS Code to apply all settings.
echo.
pause
