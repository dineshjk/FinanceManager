# Contributing to Finance Manager

Thank you for your interest in contributing to Finance Manager! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Git
- Basic knowledge of Python and Tkinter
- Familiarity with SQLite databases

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/FinanceManager.git
   cd FinanceManager
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

4. **Verify Setup**
   ```bash
   python -m FinanceManager.GUIStock.MyGUIStock
   ```

## 📋 Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise
- Use type hints where appropriate

### Example Function Documentation
```python
def calculate_brokerage(rate: float, quantity: int, brokerage_rate: float = 0.001) -> float:
    """
    Calculate brokerage amount for a trade.

    Args:
        rate: The rate per share
        quantity: Number of shares
        brokerage_rate: Brokerage percentage (default: 0.001)

    Returns:
        float: Calculated brokerage amount rounded to 4 decimal places

    Example:
        >>> calculate_brokerage(100.0, 10, 0.001)
        1.0
    """
    return round(rate * quantity * brokerage_rate, 4)
```

### Database Guidelines
- Always use context managers for database connections
- Implement proper error handling for database operations
- Use parameterized queries to prevent SQL injection
- Test database operations thoroughly

### UI Guidelines
- Maintain consistent styling across all components
- Use the existing color schemes and fonts
- Ensure all UI elements are accessible via keyboard
- Implement proper focus management
- Add tooltips for complex fields

## 🐛 Reporting Issues

### Before Submitting an Issue
1. Check if the issue already exists
2. Verify the issue with the latest version
3. Collect relevant information (Python version, OS, error messages)

### Issue Template
```
**Describe the Bug**
A clear and concise description of the bug.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
A clear description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
- OS: [e.g. Windows 10]
- Python Version: [e.g. 3.9.0]
- Application Version: [e.g. 1.0.0]

**Additional Context**
Add any other context about the problem here.
```

## 🔧 Development Areas

### Current Focus Areas
1. **Financial Calculations**: Enhance precision and add new calculation types
2. **Reporting**: Add charts and analysis features
3. **Import/Export**: Support for CSV, Excel files
4. **Performance**: Optimize database queries and UI responsiveness
5. **Testing**: Expand test coverage

### Architecture Overview
```
FinanceManager/
├── GUIStock/                 # Main application
│   ├── business/            # Business logic
│   ├── config/              # Configuration
│   ├── dbutils/             # Database utilities
│   ├── dialogs/             # Custom dialogs
│   └── ui/                  # UI components
├── tests/                   # Test files
└── docs/                    # Documentation
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=GUIStock

# Run specific test file
python -m pytest tests/test_transaction_utils.py
```

### Writing Tests
- Write tests for all new functionality
- Include both positive and negative test cases
- Mock external dependencies (database, file system)
- Test UI components where possible

### Test Example
```python
import pytest
from unittest.mock import Mock, patch
from GUIStock.dbutils.transaction_utils import calculate_net_amount

def test_calculate_net_amount_buy():
    """Test net amount calculation for buy transactions."""
    lot_price = 1000.0
    levies = 50.0
    trade_type = "BUY"

    result = calculate_net_amount(lot_price, levies, trade_type)

    assert result == 1050.0
    assert isinstance(result, float)

def test_calculate_net_amount_sell():
    """Test net amount calculation for sell transactions."""
    lot_price = 1000.0
    levies = 50.0
    trade_type = "SELL"

    result = calculate_net_amount(lot_price, levies, trade_type)

    assert result == 950.0
    assert isinstance(result, float)
```

## 📝 Pull Request Process

### Before Submitting
1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following the guidelines
   - Add tests for new functionality
   - Update documentation if needed

3. **Test Changes**
   ```bash
   python -m pytest tests/
   python -m FinanceManager.GUIStock.MyGUIStock  # Manual testing
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new financial calculation feature"
   ```

### Commit Message Format
Use conventional commits format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

### Pull Request Template
```
**Description**
Brief description of changes and why they were made.

**Type of Change**
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

**Testing**
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing completed

**Screenshots** (if applicable)
Add screenshots of UI changes.

**Checklist**
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## 🏗️ Project Structure Guidelines

### Adding New Features

1. **Database Changes**
   - Update schema in `dbutils/`
   - Add migration scripts if needed
   - Update related utility functions

2. **UI Components**
   - Add new dialogs in `dialogs/`
   - Follow existing styling patterns
   - Implement proper event handling

3. **Business Logic**
   - Add logic in `business/` package
   - Keep UI and business logic separated
   - Use appropriate error handling

### File Organization
- Keep related functionality together
- Use descriptive file and function names
- Maintain consistent imports structure
- Document complex algorithms

## 🤝 Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Provide constructive feedback
- Help newcomers get started
- Focus on what's best for the project

### Communication
- Use clear, concise language
- Ask questions if something is unclear
- Share knowledge and best practices
- Be patient with review processes

## 📚 Resources

### Learning Resources
- [Python Documentation](https://docs.python.org/)
- [Tkinter Tutorial](https://docs.python.org/3/library/tkinter.html)
- [SQLite Documentation](https://sqlite.org/docs.html)
- [Git Handbook](https://guides.github.com/introduction/git-handbook/)

### Development Tools
- [VS Code](https://code.visualstudio.com/) - Recommended IDE
- [DB Browser for SQLite](https://sqlitebrowser.org/) - Database viewer
- [Git](https://git-scm.com/) - Version control

## 🎉 Recognition

Contributors will be acknowledged in:
- README.md contributors section
- Release notes for significant contributions
- Special recognition for major features

Thank you for contributing to Finance Manager! 🚀
