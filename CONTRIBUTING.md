# Contributing to VPN Simulator

Thank you for your interest in contributing to VPN Simulator! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project adheres to the Contributor Covenant Code of Conduct. By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (optional)
- Git

### Setup Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/vpn-simulator.git
cd vpn-simulator/v2

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Install frontend dependencies
cd web-ui
npm install
cd ..
```

## Development Workflow

1. **Create a branch** from `main` for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines.

3. **Write tests** for any new functionality.

4. **Run the test suite**:
   ```bash
   pytest tests/ -v
   ```

5. **Run linting and type checking**:
   ```bash
   make lint
   make type-check
   ```

6. **Commit your changes** with a clear message:
   ```bash
   git commit -m "feat: add new protocol support"
   ```

7. **Push to your fork** and submit a pull request.

## Code Style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide.
- Use [Black](https://black.readthedocs.io/) for code formatting.
- Use [Ruff](https://docs.astral.sh/ruff/) for linting.
- Use [mypy](https://mypy.readthedocs.io/) for type checking.

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/vpn_simulator
```

### TypeScript/React

- Use [ESLint](https://eslint.org/) for linting.
- Use [Prettier](https://prettier.io/) for formatting.

```bash
cd web-ui
npm run lint
npm run format
```

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, missing semi colons, etc
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests
- `chore`: Updating build tasks, package manager configs, etc

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=vpn_simulator --cov-report=html

# Run specific test file
pytest tests/unit/test_events.py -v

# Run specific test
pytest tests/unit/test_events.py::TestEventBus::test_emit_calls_handler -v
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use fixtures from `tests/conftest.py`
- Follow the naming convention `test_<module>.py`

Example test:

```python
import pytest
from vpn_simulator.core.events import EventBus, EventTypes

@pytest.mark.asyncio
async def test_emit_calls_handler():
    bus = EventBus()
    results = []
    
    async def handler(event):
        results.append(event.name)
    
    bus.on_async(EventTypes.CONNECTION_CREATED, handler)
    await bus.emit(EventTypes.CONNECTION_CREATED, {"id": "123"})
    
    assert len(results) == 1
    assert results[0] == EventTypes.CONNECTION_CREATED
```

## Pull Request Process

1. **Update documentation** if needed.
2. **Add tests** for new functionality.
3. **Ensure all tests pass**.
4. **Update the CHANGELOG.md** with your changes.
5. **Request review** from maintainers.

### PR Template

```markdown
## Description

Brief description of the changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (please describe)

## Checklist

- [ ] My code follows the project's code style
- [ ] I have added tests that prove my fix/feature works
- [ ] All new and existing tests pass
- [ ] I have updated the documentation accordingly
```

## Questions?

Feel free to open an issue or reach out to the maintainers if you have any questions.

Thank you for contributing!
