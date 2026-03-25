# Contributing to FIG-MAC

Thank you for your interest in contributing to FIG-MAC! This document provides guidelines and instructions for contributing.

## 🚀 Getting Started

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/fig-mac.git
   cd fig-mac
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## 📋 Contribution Guidelines

### Code Style

We use the following tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Linting

```bash
# Format code
black Myexamples/

# Sort imports
isort Myexamples/

# Check linting
flake8 Myexamples/
```

### Commit Message Convention

Use conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:
```
feat(agent): add new ethics evaluator agent

Implement Prof. Qwen Ethics agent for comprehensive
ethical impact assessment of generated hypotheses.

Closes #123
```

## 🔧 Areas for Contribution

### 🎯 High Priority

1. **Agent Improvements**
   - Enhance system prompts for better output quality
   - Add new specialized agents
   - Improve agent collaboration mechanisms

2. **Workflow Optimization**
   - Reduce token usage and context truncation
   - Optimize iteration strategies
   - Improve error handling and recovery

3. **Evaluation Enhancement**
   - Add more evaluation dimensions
   - Implement automated quality metrics
   - Create benchmark datasets

### 📝 Documentation

- API documentation
- Tutorial notebooks
- Example use cases
- Architecture diagrams

### 🧪 Testing

- Unit tests for agents
- Integration tests for workflows
- Performance benchmarks
- End-to-end testing

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the bug
2. **Reproduction Steps**: Step-by-step instructions
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**:
   - Python version
   - Operating system
   - Dependency versions
6. **Logs**: Relevant error messages or logs

Example:
```markdown
**Bug**: Context truncation still uses 32768 limit despite setting 40000

**Steps to Reproduce**:
1. Set CAMEL_CONTEXT_TOKEN_LIMIT=40000
2. Run hypothesis generation
3. Check logs for truncation messages

**Expected**: No truncation below 40000 tokens
**Actual**: Truncation at 32768 tokens

**Environment**: Python 3.10, Ubuntu 22.04
```

## 💡 Feature Requests

Feature requests are welcome! Please provide:

1. **Use Case**: Why is this feature needed?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: Other approaches considered
4. **Additional Context**: Any relevant information

## 🔒 Security

If you discover a security vulnerability, please:

1. **DO NOT** open a public issue
2. Email security concerns to: figmac-team@example.com
3. Include detailed description and reproduction steps

## 📊 Performance Optimization

When optimizing performance:

1. **Measure First**: Profile before optimizing
2. **Benchmark**: Include before/after comparisons
3. **Document**: Explain the optimization strategy
4. **Test**: Ensure correctness is maintained

## 🎓 Code Review Process

All contributions go through code review:

1. **Submit PR**: Create a pull request with clear description
2. **Automated Checks**: CI will run tests and linting
3. **Review**: Maintainers will review within 3-5 days
4. **Feedback**: Address review comments
5. **Merge**: Approved PRs will be merged

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts
- [ ] CHANGELOG.md updated (if applicable)

## 🏆 Recognition

Contributors will be:

- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in relevant documentation

## 📞 Contact

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: figmac-team@example.com

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to FIG-MAC! 🔬🤖
