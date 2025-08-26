# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial package structure and setup
- Core SQLite connector classes
- Read-only and write-only specialized connectors
- Comprehensive test suite
- Development tooling and linting

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.1.0] - 2024-01-XX

### Added
- Initial release of DataPulse SQLite connector
- `SQLitePulse` - Full-featured connector implementing both read and write operations
- `SQLiteReadonlyPulse` - Optimized for read-only operations and analytics
- `SQLiteWriteonlyPulse` - Specialized for high-volume data ingestion
- Async-first architecture with proper connection management
- Comprehensive error handling and validation
- Support for parameterized queries and bulk operations
- Transaction support with ACID compliance
- Type hints throughout the codebase
- Integration with DataPulse core interfaces

### Features
- Local database file management
- Automatic directory creation
- Efficient bulk insert operations
- Table schema introspection
- Connection pooling and resource management
- Comprehensive test coverage
- Professional PyPI package structure

## [0.0.1] - 2024-01-XX

### Added
- Initial development version
- Basic package structure
- Core connector implementation
