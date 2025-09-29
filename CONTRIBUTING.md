# Contributing to Half Marathon Predictor

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/halfmarathon-predictor.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit: `git commit -m "Add: your feature description"`
7. Push: `git push origin feature/your-feature-name`
8. Open a Pull Request

## 📋 Development Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# Run tests
python test_app.py
```

## 🎨 Code Style

We follow PEP 8 guidelines with the following tools:

- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking

```bash
# Format code
black .

# Lint code
flake8 .

# Type check
mypy utils/
```

## ✅ Testing

All new features should include tests:

```bash
# Run all tests
python test_app.py

# Run specific test
python -m pytest test_app.py::TestTimeParser -v

# Run with coverage
python -m pytest test_app.py --cov=utils
```

## 📝 Commit Messages

Use clear, descriptive commit messages:

- `Add: new feature`
- `Fix: bug description`
- `Update: improvement description`
- `Docs: documentation update`
- `Test: add/update tests`
- `Refactor: code restructuring`

## 🐛 Reporting Bugs

When reporting bugs, include:

1. Description of the issue
2. Steps to reproduce
3. Expected behavior
4. Actual behavior
5. System information (OS, Python version)
6. Relevant logs or error messages

## 💡 Feature Requests

For feature requests, describe:

1. The problem you're trying to solve
2. Your proposed solution
3. Alternative solutions considered
4. Additional context

## 🔍 Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new features
3. **Ensure all tests pass**
4. **Update CHANGELOG.md**
5. **Request review** from maintainers

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No merge conflicts
- [ ] All CI checks pass

## 🏗️ Project Structure

```
halfmarathon-predictor/
├── notebooks/          # Training notebooks
├── utils/             # Core utilities
│   ├── data_loader.py
│   ├── llm_extractor.py
│   └── model_predictor.py
├── app.py             # Main application
├── test_app.py        # Unit tests
└── requirements.txt   # Dependencies
```

## 🤝 Areas for Contribution

We welcome contributions in:

- **Features**: New prediction features, UI improvements
- **Models**: Better ML models, feature engineering
- **Testing**: Increase test coverage
- **Documentation**: Improve guides, add examples
- **Performance**: Optimize code, reduce latency
- **Localization**: Add language support

## 📞 Getting Help

- Open an issue for questions
- Join discussions in GitHub Discussions
- Check existing issues and PRs

## 📜 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## 🎯 Priority Areas

Current focus areas:

1. **Model improvements**: Add more features (10km time, training volume)
2. **UI enhancements**: Better mobile experience
3. **Testing**: Increase coverage to 90%+
4. **Documentation**: More examples and tutorials
5. **Performance**: Reduce prediction latency

## 📈 Development Workflow

1. **Check issues**: Look for open issues or create one
2. **Discuss**: Comment on the issue before starting work
3. **Develop**: Create a branch and implement your changes
4. **Test**: Ensure all tests pass
5. **Document**: Update relevant documentation
6. **Submit**: Open a PR with clear description
7. **Review**: Address feedback from reviewers
8. **Merge**: Maintainers will merge approved PRs

## 🔄 Keeping Your Fork Updated

```bash
# Add upstream remote
git remote add upstream https://github.com/original-owner/halfmarathon-predictor.git

# Fetch upstream changes
git fetch upstream

# Merge upstream main
git checkout main
git merge upstream/main

# Push to your fork
git push origin main
```

## 📦 Release Process

1. Update version in relevant files
2. Update CHANGELOG.md
3. Create release branch
4. Tag release: `git tag -a v1.x.x -m "Release v1.x.x"`
5. Push tags: `git push --tags`
6. Deploy to production

## 💬 Questions?

Feel free to open an issue for any questions or clarifications needed!

Thank you for contributing! 🎉