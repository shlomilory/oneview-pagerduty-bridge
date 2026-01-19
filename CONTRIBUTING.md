# Contributing to HPOneView-PagerDuty Bridge

First off, thank you for considering contributing to this project! This project demonstrates production-grade DevOps practices, and contributions that maintain or improve these standards are welcome.

## 🎯 Project Goals

This project serves as:
1. **Portfolio demonstration** of enterprise Kubernetes and DevOps skills
2. **Educational resource** for production-grade patterns
3. **Reusable template** for alert routing systems

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful of differing viewpoints and experiences.

### Our Standards

- **Be respectful** and professional
- **Be constructive** in feedback
- **Be collaborative** and helpful
- **Focus on what is best** for the community

## 🤝 How Can I Contribute?

### Reporting Bugs

**Before submitting a bug report:**
- Check the [Troubleshooting Guide](README.md#-troubleshooting)
- Search existing [Issues](https://github.com/YOUR_USERNAME/hponeview-pagerduty-bridge/issues)

**When submitting a bug report, include:**
- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Environment details (K8s version, Python version, etc.)
- Logs and error messages
- Screenshots if applicable

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use case**: Why is this enhancement useful?
- **Describe the solution**: What you want to happen
- **Describe alternatives**: Other solutions you've considered
- **Additional context**: Screenshots, examples, etc.

### Pull Requests

We actively welcome your pull requests:

1. Fork the repo and create your branch from `main`
2. If you've added code, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

## 💻 Development Setup

### Prerequisites

- Python 3.11+
- Docker
- Kubernetes cluster (minikube, kind, or cloud)
- kubectl
- Helm 3
- Git

### Local Environment Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/hponeview-pagerduty-bridge.git
cd hponeview-pagerduty-bridge

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r src/requirements.txt

# Install development dependencies (if you create this file)
pip install pytest pytest-cov flake8 black mypy
```

### Running Locally

```bash
# Set environment variables
export ONEVIEW_HOST="oneview.example.com"
export ONEVIEW_USERNAME="admin"
export ONEVIEW_PASSWORD="password"
export PAGERDUTY_ROUTING_KEY="your-test-key"
export GUNICORN_MAIN_PROCESS="true"
export LOG_LEVEL="debug"

# Run application
cd src
python app.py
```

### Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (requires running infrastructure)
pytest tests/integration -v

# All tests with coverage
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Code Quality Checks

```bash
# Linting
flake8 src/ tests/

# Code formatting
black src/ tests/ --check

# Type checking
mypy src/
```

### Building Docker Image

```bash
# Build image
docker build -f src/Dockerfile -t hponeview-bridge:dev .

# Run container
docker run -p 5000:5000 \
  -e ONEVIEW_HOST="oneview.example.com" \
  -e ONEVIEW_USERNAME="admin" \
  -e ONEVIEW_PASSWORD="password" \
  -e PAGERDUTY_ROUTING_KEY="your-key" \
  hponeview-bridge:dev
```

### Testing Helm Chart

```bash
# Lint chart
helm lint ./helm

# Template and validate
helm template hponeview-bridge ./helm \
  --values ./helm/values.yaml \
  --validate

# Install to local cluster
helm install hponeview-bridge ./helm \
  --namespace dev \
  --create-namespace \
  --values ./helm/values.yaml \
  --set externalSecrets.enabled=false
```

## 🔄 Pull Request Process

### Branch Naming Convention

- `feature/` - New features
- `bugfix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test improvements
- `chore/` - Maintenance tasks

Examples:
- `feature/add-slack-integration`
- `bugfix/fix-session-refresh`
- `docs/improve-deployment-guide`

### Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat(alerts): add support for Warning severity alerts

- Extended alert processing to handle Warning level
- Added new Prometheus metric for warning count
- Updated documentation

Closes #123
```

```
fix(session): prevent race condition in token refresh

- Added mutex lock around session refresh logic
- Improved error handling for concurrent requests
- Added unit tests for concurrent scenarios

Fixes #456
```

### Pull Request Template

When creating a PR, include:

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
- [ ] Added new tests for changes

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Comments added to complex code
- [ ] Documentation updated (README, API docs, etc.)
- [ ] No new warnings generated
- [ ] Tests added/updated as needed
- [ ] All tests passing
```

### Review Process

1. **Automated Checks**: GitHub Actions must pass
2. **Code Review**: At least one approval required
3. **Testing**: All tests must pass
4. **Documentation**: Docs must be updated if needed

## 📝 Coding Standards

### Python Style Guide

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/):

- **Indentation**: 4 spaces
- **Line length**: 100 characters max
- **Imports**: Grouped (stdlib, third-party, local)
- **Naming**:
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`

### Type Hints

Use type hints for function signatures:

```python
from typing import Dict, List, Optional

def process_alert(
    alert: Dict[str, str], 
    routing_key: str
) -> Optional[str]:
    """Process alert and send to PagerDuty.
    
    Args:
        alert: Alert data from OneView
        routing_key: PagerDuty routing key
        
    Returns:
        Dedup key if successful, None otherwise
    """
    pass
```

### Documentation

- **Docstrings**: Use Google style
- **Comments**: Explain "why", not "what"
- **README**: Update for new features
- **Examples**: Provide usage examples

### Error Handling

```python
# ✅ Good: Specific exceptions, logging, context
try:
    response = send_to_pagerduty(alert, routing_key)
except requests.exceptions.Timeout as e:
    logger.error(f"PagerDuty timeout for alert {alert_id}: {e}")
    ALERTS_FAILED.labels(reason='timeout').inc()
    return False
except requests.exceptions.RequestException as e:
    logger.error(f"PagerDuty request failed for alert {alert_id}: {e}")
    ALERTS_FAILED.labels(reason='network').inc()
    return False

# ❌ Bad: Generic exception, no logging
try:
    send_to_pagerduty(alert, routing_key)
except Exception:
    pass
```

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests (fast, isolated)
│   ├── test_app.py
│   ├── test_oneview_client.py
│   └── test_deduplication.py
├── integration/       # Integration tests (with dependencies)
│   ├── test_oneview_api.py
│   └── test_pagerduty_api.py
└── e2e/              # End-to-end tests (full workflow)
    └── test_alert_flow.py
```

### Test Coverage

- **Minimum**: 80% coverage
- **Target**: 90% coverage
- **Critical paths**: 100% coverage

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch

def test_alert_deduplication():
    """Test that duplicate alerts are not sent to PagerDuty."""
    # Given
    alert = {"uri": "/rest/alerts/123", "severity": "Critical"}
    
    # When
    first_send = send_to_pagerduty(alert, "test-key")
    second_send = send_to_pagerduty(alert, "test-key")
    
    # Then
    assert first_send is True
    assert second_send is False  # Duplicate blocked
```

## 🚀 Release Process

### Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in Chart.yaml
- [ ] Git tag created
- [ ] Docker image built and pushed
- [ ] Helm chart version updated
- [ ] Release notes written

## 📞 Getting Help

- **Documentation**: Check [docs/](docs/) folder first
- **Issues**: Search [existing issues](https://github.com/YOUR_USERNAME/hponeview-pagerduty-bridge/issues)
- **Discussions**: Use [GitHub Discussions](https://github.com/YOUR_USERNAME/hponeview-pagerduty-bridge/discussions) for questions

## 🙏 Recognition

Contributors will be acknowledged in:
- README.md
- Release notes
- CONTRIBUTORS.md (if we create one)

## 📋 Development Tips

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL="debug"

# Run with auto-reload (development)
export FLASK_ENV="development"
flask run --reload

# Check health status
curl http://localhost:5000/health | jq

# View metrics
curl http://localhost:5000/metrics | grep oneview
```

### Common Issues

**Issue**: Import errors when running tests
```bash
# Solution: Install package in editable mode
pip install -e .
```

**Issue**: Kubernetes connection errors
```bash
# Solution: Verify kubeconfig
kubectl cluster-info
kubectl get nodes
```

## 🎓 Learning Resources

- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Helm Chart Guide](https://helm.sh/docs/chart_template_guide/)
- [ArgoCD Patterns](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
- [Prometheus Metrics](https://prometheus.io/docs/practices/naming/)

---

**Thank you for contributing to production-grade DevOps practices!** 🚀

*Questions? Open an issue or discussion on GitHub!*
