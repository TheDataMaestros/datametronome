# Contributing to DataPulse SQLite

Thank you for your interest in contributing to DataPulse SQLite! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- pip or conda for package management

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/metronome-pulse-sqlite.git
   cd metronome-pulse-sqlite
   ```

2. **Install in development mode**
   ```bash
   make install-dev
   ```

3. **Install test dependencies**
   ```bash
   make install
   ```

4. **Run tests to verify setup**
   ```bash
   make test
   ```

## 🧪 Testing

### Test Structure

- **Unit Tests** (`test_unit.py`): Fast, isolated tests for individual components
- **Integration Tests** (`test_integration.py`): Database interaction tests with proper setup/teardown
- **Performance Tests**: Benchmark and stress testing

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test types
make test-unit        # Fast unit tests
make test-integration # Slower integration tests
make test-slow        # Performance tests
```

### Writing Tests

- Follow the existing test patterns
- Use descriptive test names and docstrings
- Mark tests appropriately (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.)
- Use fixtures for common setup
- Test both success and failure scenarios

## 🔧 Code Quality

### Linting and Formatting

```bash
# Check code quality
make lint

# Format code automatically
make format
```

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints throughout
- Write comprehensive docstrings
- Keep functions focused and single-purpose
- Use meaningful variable and function names

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality:

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## 📝 Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following the project standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Run quality checks**
   ```bash
   make lint
   make test
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create a PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

## 🐛 Reporting Issues

When reporting issues, please include:

- **Description**: Clear description of the problem
- **Steps to reproduce**: Detailed steps to reproduce the issue
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Environment**: Python version, OS, etc.
- **Code example**: Minimal code to reproduce the issue

## 💡 Feature Requests

We welcome feature requests! Please:

- Describe the feature clearly
- Explain the use case and benefits
- Provide examples if possible
- Consider implementation complexity

## 📚 Documentation

### Code Documentation

- All public functions and classes should have docstrings
- Use Google-style docstrings
- Include type hints
- Document exceptions and edge cases

### User Documentation

- Update README.md for user-facing changes
- Add examples for new features
- Update API reference as needed

## 🔒 Security

- Never commit sensitive information (API keys, passwords, etc.)
- Report security vulnerabilities privately
- Follow secure coding practices
- Validate all inputs

## 🤝 Community Guidelines

- Be respectful and inclusive
- Help other contributors
- Provide constructive feedback
- Follow the project's code of conduct

## 📞 Getting Help

- **Issues**: [GitHub Issues](https://github.com/datametronome/metronome-pulse-sqlite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/datametronome/metronome-pulse-sqlite/discussions)
- **Documentation**: [Project Docs](https://datametronome.dev/docs/pulse-sqlite)

## 🏆 Recognition

Contributors will be recognized in:

- Project README
- Release notes
- Contributor hall of fame

Thank you for contributing to DataPulse SQLite! 🎉
