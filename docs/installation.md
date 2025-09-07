# Installation Guide

This guide provides detailed instructions for setting up and running the Finance Manager application.

## 📋 System Requirements

### Minimum Requirements
- **Operating System**: Windows 10 or later
- **Python**: 3.8 or higher
- **Memory**: 4GB RAM
- **Storage**: 100MB free space
- **Display**: 1024x768 resolution minimum

### Recommended Requirements
- **Operating System**: Windows 11
- **Python**: 3.10 or higher
- **Memory**: 8GB RAM
- **Storage**: 500MB free space (for data growth)
- **Display**: 1920x1080 resolution

## 🚀 Installation Methods

### Method 1: Standard Installation (Recommended)

1. **Install Python**
   - Download Python from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"
   - Verify installation:
     ```cmd
     python --version
     pip --version
     ```

2. **Clone the Repository**
   ```cmd
   git clone https://github.com/yourusername/FinanceManager.git
   cd FinanceManager
   ```

3. **Create Virtual Environment**
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```

4. **Install Dependencies**
   ```cmd
   pip install -r requirements.txt
   ```

5. **Verify Installation**
   ```cmd
   python -m FinanceManager.GUIStock.MyGUIStock
   ```

### Method 2: VS Code Development Setup

1. **Install VS Code**
   - Download from [code.visualstudio.com](https://code.visualstudio.com/)
   - Install Python extension

2. **Open Project**
   ```cmd
   code FinanceManager.code-workspace
   ```

3. **Install Recommended Extensions**
   - VS Code will prompt to install recommended extensions
   - Accept the installation

4. **Select Python Interpreter**
   - Press `Ctrl+Shift+P`
   - Type "Python: Select Interpreter"
   - Choose the virtual environment interpreter

5. **Run Application**
   - Press `F5` or `Ctrl+F5`
   - Or use Run menu

## 🛠️ Configuration

### Database Setup
The application automatically creates the SQLite database on first run. No manual setup required.

### VS Code Configuration
The project includes pre-configured VS Code settings:
- **launch.json**: Debug configurations
- **settings.json**: Python interpreter and analysis settings
- **extensions.json**: Recommended extensions

### Environment Variables
No environment variables are required for basic operation.

## 🔧 Troubleshooting

### Common Issues

#### Python Not Found
**Error**: `'python' is not recognized as an internal or external command`

**Solution**:
1. Reinstall Python with "Add to PATH" checked
2. Or manually add Python to system PATH
3. Restart command prompt/VS Code

#### Module Import Errors
**Error**: `ModuleNotFoundError: No module named 'tkcalendar'`

**Solution**:
```cmd
pip install -r requirements.txt
```

#### Virtual Environment Issues
**Error**: Virtual environment not activating

**Solution**:
```cmd
# Delete existing environment
rmdir /s .venv

# Create new environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

#### Database Permissions
**Error**: Database access denied

**Solution**:
1. Ensure the application folder has write permissions
2. Run command prompt as administrator if needed
3. Check antivirus software isn't blocking file access

#### GUI Display Issues
**Error**: GUI doesn't display properly

**Solutions**:
1. Update graphics drivers
2. Check display scaling settings
3. Try running in compatibility mode

### VS Code Specific Issues

#### Python Interpreter Not Found
**Solution**:
1. Open Command Palette (`Ctrl+Shift+P`)
2. Type "Python: Select Interpreter"
3. Choose the correct interpreter from `.venv\Scripts\python.exe`

#### Debugging Not Working
**Solution**:
1. Check launch.json configuration
2. Ensure Python extension is installed
3. Verify working directory is correct

## 📱 Running the Application

### Command Line Execution
```cmd
# Activate virtual environment
.venv\Scripts\activate

# Method 1: Direct execution
python GUIStock/MyGUIStock.py

# Method 2: Module execution (recommended)
python -m FinanceManager.GUIStock.MyGUIStock
```

### VS Code Execution
1. Open workspace file: `FinanceManager.code-workspace`
2. Press `F5` (debug mode) or `Ctrl+F5` (run without debugging)
3. Select launch configuration if prompted

### Creating Desktop Shortcut
1. Create a batch file `launch_finance_manager.bat`:
   ```batch
   @echo off
   cd /d "C:\path\to\FinanceManager"
   .venv\Scripts\activate
   python -m FinanceManager.GUIStock.MyGUIStock
   pause
   ```
2. Create shortcut to this batch file on desktop

## 🔄 Updates and Maintenance

### Updating the Application
```cmd
git pull origin main
pip install -r requirements.txt --upgrade
```

### Backing Up Data
The SQLite database is located in:
- `GUIStock/StockData/myfolio.db`

Copy this file to backup your data.

### Log Files
Application logs are stored in:
- `GUIStock/logs/stock_portfolio.log`

## 🐛 Getting Help

If you encounter issues:

1. **Check the logs**: Look in `GUIStock/logs/` for error messages
2. **Verify installation**: Run the verification commands above
3. **Check requirements**: Ensure all dependencies are installed
4. **Report issues**: Create an issue on GitHub with:
   - Error messages
   - Steps to reproduce
   - System information
   - Log file contents

## 📞 Support Resources

- **GitHub Issues**: [Create an issue](https://github.com/yourusername/FinanceManager/issues)
- **Documentation**: [Project Wiki](https://github.com/yourusername/FinanceManager/wiki)
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md)

---

**Next Steps**: After installation, see the [User Guide](user_guide.md) for information on using the application.
