# Contributing to DataMetronome

Thank you for your interest in contributing to DataMetronome! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Python 3.9+
- Git
- pip or poetry
- Docker (optional, for development environment)

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/datametronome.git
   cd datametronome
   ```

2. **Set up the development environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install packages in development mode
   make install
   make install-dev
   ```

3. **Set up environment variables**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your configuration
   # Make sure to set DATAMETRONOME_SECRET_KEY
   ```

4. **Set up database**
   ```bash
   make setup-db
   ```

5. **Start services**
   ```bash
   # Terminal 1: Start backend
   make start-podium
   
   # Terminal 2: Start UI
   make start-ui
   ```

## Project Structure

```
datametronome/
├── podium/                 # Core backend API
├── ui-streamlit/           # Default Streamlit UI
├── plugins/                # Integration plugins
├── brain/                  # Analytics libraries
├── pulse/                  # Data connectors
├── docs/                   # Documentation
├── tests/                  # Test suite
└── scripts/                # Utility scripts
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests and Linting

```bash
# Run tests
make test

# Run linting
make lint

# Format code
make format
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

Use conventional commit messages:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for adding tests
- `chore:` for maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Create a pull request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots for UI changes

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for all functions and classes
- Maximum line length: 88 characters (Black formatter)

### Testing

- Write unit tests for new functionality
- Aim for 90%+ code coverage
- Use pytest for testing
- Mock external dependencies

### Documentation

- Update README files for package changes
- Add docstrings to new functions
- Update API documentation if endpoints change

## Architecture Guidelines

### Adding New Connectors

1. Create a new package in `pulse/`
2. Inherit from `BaseConnector`
3. Implement all required methods
4. Register with `ConnectorRegistry`
5. Add tests

### Adding New Check Types

1. Define check configuration schema
2. Implement check logic
3. Add to check type hierarchy
4. Update UI components
5. Add tests

### Adding New Analytics

1. Create new module in `brain/`
2. Follow existing patterns
3. Add configuration options
4. Include tests and examples

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
pytest --cov=datametronome --cov-report=html
```

### Writing Tests

- Test both success and failure cases
- Mock external dependencies
- Use fixtures for common setup
- Test edge cases and error conditions

## Documentation

### API Documentation

- Update OpenAPI schemas
- Add examples for new endpoints
- Document error responses

### User Documentation

- Update README files
- Add usage examples
- Include configuration examples

## Release Process

### Versioning

We use semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes, backward compatible

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version numbers updated
- [ ] Release notes written

## Getting Help

- **Issues**: Use GitHub issues for bug reports and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Documentation**: Check the docs/ directory
- **Code**: Review existing code for examples

## Code of Conduct

- Be respectful and inclusive
- Focus on technical discussions
- Help others learn and grow
- Report inappropriate behavior

## License

By contributing to DataMetronome, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to DataMetronome! 🎵
