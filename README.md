# 💼 Finance Manager - Stock Portfolio Management System

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Maintenance](https://img.shields.io/badge/maintained-yes-green.svg)](https://github.com/yourusername/FinanceManager)
[![Windows](https://img.shields.io/badge/platform-windows-lightgrey.svg)](https://www.microsoft.com/windows)

A comprehensive desktop application for managing stock portfolios, tracking trades, and analyzing investment performance. Built with Python and Tkinter for a user-friendly experience.

![Finance Manager Screenshot](docs/images/main_interface.png)

## 🌟 Features

### 📊 Portfolio Management
- **Real-time Portfolio Tracking**: Monitor your stock holdings and performance
- **Trade Recording**: Record buy/sell transactions with detailed execution data
- **Financial Calculations**: Automatic calculation of brokerage, taxes, and net amounts
- **Multi-Exchange Support**: Support for NSE (National Stock Exchange) and BSE (Bombay Stock Exchange)

### 💰 Financial Features
- **Precision Formatting**: Automatic formatting with appropriate decimal places
  - Rate EO: 2 decimal places
  - Weighted Average Price: 4 decimal places
  - Cascading calculations for dependent fields
- **Comprehensive Cost Tracking**:
  - Brokerage calculations
  - Exchange charges (ETC)
  - SEBI charges
  - GST, STT, Stamp Duty
  - IGST and other levies

### 🎨 User Experience
- **Intuitive GUI**: Clean, modern interface with enhanced styling
- **Modal Window Management**: Centralized focus management system
- **Smart Form Validation**: Real-time input validation and error handling
- **Keyboard Shortcuts**: Full keyboard navigation support
- **Auto-completion**: Smart company name completion and selection

### 🗄️ Data Management
- **SQLite Database**: Robust local data storage
- **CRUD Operations**: Complete Create, Read, Update, Delete functionality
- **Data Integrity**: Comprehensive validation and error handling
- **Backup Support**: Database backup and restoration capabilities

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Windows OS (primary platform)
- Git (for cloning the repository)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/FinanceManager.git
   cd FinanceManager
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   # Method 1: Direct execution
   python GUIStock/MyGUIStock.py

   # Method 2: Module execution (recommended)
   python -m FinanceManager.GUIStock.MyGUIStock
   ```

### VS Code Setup (Recommended)

1. **Open the workspace file**
   ```bash
   code FinanceManager.code-workspace
   ```

2. **Install recommended extensions**
   - Python (ms-python.python)
   - Pylance (ms-python.vscode-pylance)

3. **Run using VS Code**
   - Use `Ctrl+F5` or `F5` for debugging
   - Multiple launch configurations available

## 📁 Project Structure

```
FinanceManager/
├── 📁 GUIStock/                    # Main application package
│   ├── 📁 business/                # Business logic layer
│   ├── 📁 config/                  # Configuration and settings
│   ├── 📁 core/                    # Core functionality
│   ├── 📁 dbutils/                 # Database utilities
│   │   ├── company_utils.py        # Company management
│   │   ├── transaction_utils.py    # Transaction handling
│   │   └── ...
│   ├── 📁 dialogs/                 # Custom dialog components
│   ├── 📁 ui/                      # UI components
│   ├── 📁 logs/                    # Application logs
│   └── MyGUIStock.py              # Main application entry point
├── 📁 GUI/                         # Legacy GUI components
├── 📁 Stocks/                      # Stock data utilities
├── 📁 .vscode/                     # VS Code configuration
│   ├── launch.json                 # Debug configurations
│   ├── settings.json               # Workspace settings
│   └── extensions.json             # Recommended extensions
├── 📁 docs/                        # Documentation
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── LICENSE                         # License information
├── .gitignore                      # Git ignore rules
└── FinanceManager.code-workspace   # VS Code workspace
```

## 🛠️ Development

### Setting up Development Environment

1. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run tests**
   ```bash
   python -m pytest tests/
   ```

3. **Code formatting**
   ```bash
   black GUIStock/
   isort GUIStock/
   ```

### Database Schema

The application uses SQLite with the following main tables:
- `stocks`: Company information and ISIN codes
- `contracts`: Trading contract details
- `transactions`: Individual trade transactions
- `exchange_orders`: Exchange order details

### Key Components

- **MyGUIStock.py**: Main application window and menu system
- **transaction_utils.py**: Trade entry and management
- **company_utils.py**: Company and stock management
- **globals.py**: Global constants and configurations

## 📋 Usage Guide

### Adding a New Trade

1. **Open Trade Entry**: Click "Add Trade" from the main menu
2. **Enter Contract Details**:
   - Contract number
   - Trade date
   - Settlement details
3. **Select Company**: Use the dropdown with auto-completion
4. **Choose Trade Type**: Buy or Sell
5. **Enter Execution Details**:
   - Quantity, order numbers, trade numbers
   - Rate and brokerage information
6. **Review Calculations**: All financial calculations are automatic
7. **Submit**: Save the trade to database

### Financial Field Formatting

The application automatically formats financial fields:
- **Rate EO**: Rounds to 2 decimal places on focus-out
- **Weighted Average Price**: Formats to 4 decimal places
- **Cascading Updates**: WAP changes automatically update:
  - Brokerage Per Share
  - Lot Price
  - Lot Brokerage
  - All dependent calculations

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/FinanceManager/issues)
- **Documentation**: [Wiki](https://github.com/yourusername/FinanceManager/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/FinanceManager/discussions)

## 🔄 Changelog

### v1.0.0 (Latest)
- ✅ Complete financial formatting system implementation
- ✅ Enhanced UI with precision decimal control
- ✅ Cascading calculations from WAP changes
- ✅ Comprehensive event binding system
- ✅ Modal window management improvements
- ✅ VS Code integration with multiple launch configurations

### Previous Versions
See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

## 🙏 Acknowledgments

- Built with Python and Tkinter
- Uses tkcalendar for date selection
- SQLite for robust data storage
- VS Code for development environment

---

**Made with ❤️ for financial portfolio management**
