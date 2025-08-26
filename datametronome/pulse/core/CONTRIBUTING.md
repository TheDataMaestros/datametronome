# Contributing to DataPulse Core

Thank you for your interest in contributing to DataPulse Core! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **🐛 Bug Reports**: Help us identify and fix issues
- **✨ Feature Requests**: Suggest new functionality
- **📚 Documentation**: Improve docs, examples, and guides
- **🧪 Tests**: Add or improve test coverage
- **🔧 Code**: Fix bugs, implement features, improve performance
- **📖 Examples**: Create usage examples and tutorials

### Before You Start

1. **Check existing issues** to see if your idea is already being worked on
2. **Search discussions** to see if your question has been answered
3. **Read the documentation** to understand the current architecture
4. **Join our community** to discuss ideas and get help

## 🚀 Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- pip or uv (recommended)

### Local Development

```bash
# Clone the repository
git clone https://github.com/datametronome/metronome-pulse-core.git
cd metronome-pulse-core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Using uv (Recommended)

```bash
# Install uv if you haven't already
pip install uv

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=metronome_pulse_core

# Run specific test categories
pytest -m "unit"      # Unit tests only
pytest -m "integration"  # Integration tests only
pytest -m "slow"      # Slow tests only

# Run tests in parallel
pytest -n auto

# Run tests with verbose output
pytest -v
```

### Test Structure

```
tests/
├── unit/           # Unit tests (fast, isolated)
├── integration/    # Integration tests (slower, real dependencies)
├── conftest.py     # Shared test fixtures
└── test_*.py       # Test modules
```

### Writing Tests

- **Unit tests**: Test individual functions/methods in isolation
- **Integration tests**: Test interactions between components
- **Use fixtures**: Leverage pytest fixtures for common setup
- **Mock external dependencies**: Use pytest-mock for external services
- **Test edge cases**: Include boundary conditions and error scenarios

Example test:

```python
import pytest
from metronome_pulse_core import Pulse, Readable

class TestPulse:
    """Test the Pulse base interface."""
    
    def test_pulse_is_abstract(self):
        """Test that Pulse cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Pulse()
    
    def test_pulse_has_required_methods(self):
        """Test that Pulse has required abstract methods."""
        assert hasattr(Pulse, 'connect')
        assert hasattr(Pulse, 'disconnect')
        assert hasattr(Pulse, 'is_connected')
```

## 📝 Code Style

### Formatting

We use several tools to maintain code quality:

```bash
# Format code with black
black metronome_pulse_core tests

# Sort imports with isort
isort metronome_pulse_core tests

# Type checking with mypy
mypy metronome_pulse_core

# Linting with ruff
ruff check metronome_pulse_core tests
ruff check --fix metronome_pulse_core tests
```

### Style Guidelines

- **Follow PEP 8**: Use our configured tools (black, isort, ruff)
- **Type hints**: Use type hints for all function parameters and return values
- **Docstrings**: Use Google-style docstrings for all public functions
- **Naming**: Use descriptive names that follow Python conventions
- **Comments**: Write clear, concise comments explaining complex logic

### Example Code

```python
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

class DataConnector(Pulse, Readable, Writable):
    """Abstract base class for data connectors.
    
    This class provides a common interface for all data connectors
    in the DataPulse ecosystem.
    """
    
    def __init__(self, connection_string: str, **kwargs: Any) -> None:
        """Initialize the data connector.
        
        Args:
            connection_string: Connection string for the data source
            **kwargs: Additional configuration options
        """
        self.connection_string = connection_string
        self.config = kwargs
        self._connection: Optional[Any] = None
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the data source."""
        pass
```

## 🔄 Development Workflow

### 1. Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write code following our style guidelines
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 3. Commit Your Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new connector interface

- Add new abstract method for bulk operations
- Include comprehensive test coverage
- Update documentation with examples"
```

### 4. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
```

## 📋 Pull Request Guidelines

### Before Submitting

- [ ] All tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] New features have tests
- [ ] Breaking changes are documented

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

## 🐛 Bug Reports

### Bug Report Template

```markdown
## Bug Description
Clear and concise description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior
What you expected to happen

## Actual Behavior
What actually happened

## Environment
- OS: [e.g. Ubuntu 20.04]
- Python Version: [e.g. 3.11.0]
- Package Version: [e.g. 0.1.0]
- Database: [e.g. PostgreSQL 15]

## Additional Context
Any other context about the problem
```

## ✨ Feature Requests

### Feature Request Template

```markdown
## Problem Statement
Clear description of the problem you're trying to solve

## Proposed Solution
Description of the solution you'd like to see

## Alternative Solutions
Any alternative solutions you've considered

## Additional Context
Any other context, examples, or screenshots
```

## 📚 Documentation

### Documentation Standards

- **Clear and concise**: Write for developers, not for yourself
- **Examples**: Include practical examples for all features
- **API Reference**: Document all public methods and classes
- **Tutorials**: Provide step-by-step guides for common tasks

### Building Documentation

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build documentation
cd docs
make html

# View locally
open _build/html/index.html
```

## 🏷️ Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Process

1. **Update version** in `metronome_pulse_core/__init__.py`
2. **Update CHANGELOG.md** with new version
3. **Create release tag** on GitHub
4. **Publish to PyPI** (automated via GitHub Actions)

## 🤝 Community Guidelines

### Code of Conduct

- **Be respectful**: Treat everyone with respect
- **Be inclusive**: Welcome contributors from all backgrounds
- **Be constructive**: Provide helpful, constructive feedback
- **Be patient**: Remember that contributors are volunteers

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Pull Requests**: Code contributions and reviews

## 🙏 Acknowledgments

Thank you for contributing to DataPulse Core! Your contributions help make this project better for everyone in the data engineering community.

## 📞 Getting Help

If you need help with contributing:

1. **Check the documentation** first
2. **Search existing issues** for similar questions
3. **Create a new issue** with your question
4. **Join our community** discussions

---

**Happy coding! 🚀**

