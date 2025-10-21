# Contributing to RadStream

## 🤝 Team Collaboration Guidelines

### Team Members
- **Rahul Sharma** - Data & Serving Performance Lead
- **Mukul Rayana** - Platform & Autoscaling Lead  
- **Karthik Ramanathan** - Security, Edge & Evaluation Lead

### Branch Strategy

#### Main Branches
- `main` - Production-ready code, stable releases
- `develop` - Integration branch for features

#### Feature Branches
- `feature/rahul-*` - Rahul's feature development
- `feature/mukul-*` - Mukul's feature development
- `feature/karthik-*` - Karthik's feature development

#### Example Branch Names
```
feature/rahul-s3-setup
feature/rahul-lambda-functions
feature/mukul-eks-cluster
feature/mukul-triton-deployment
feature/karthik-security-setup
feature/karthik-dashboards
```

### Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-name-feature-name
   ```

2. **Work on Your Feature**
   - Make commits with clear messages
   - Test your changes locally
   - Update documentation if needed

3. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-name-feature-name
   ```
   - Create PR to `develop` branch
   - Request review from other team members
   - Address feedback and merge

4. **Integration Testing**
   - Test integration with other components
   - Update shared documentation
   - Merge to `main` when ready

### Code Organization

#### Directory Structure
```
RadStream/
├── shared/                    # Common infrastructure
│   ├── infrastructure/        # Core AWS setup
│   ├── docs/                 # All documentation
│   └── requirements.txt
├── rahul/                    # Rahul's implementations
│   ├── preprocessing/
│   ├── telemetry/
│   └── scripts/
├── mukul/                    # Mukul's implementations
│   └── inference/
└── karthik/                  # Karthik's implementations
    └── security/
```

#### Naming Conventions
- **Files**: `snake_case.py`
- **Functions**: `snake_case()`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Branches**: `feature/name-description`

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

#### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

#### Examples
```
feat(infrastructure): add S3 bucket creation script
fix(lambda): resolve timeout issue in preprocessing
docs(architecture): update system diagram
test(telemetry): add unit tests for Kinesis producer
```

### Code Review Process

1. **Self Review**
   - Test your code thoroughly
   - Check for linting errors
   - Update documentation

2. **Peer Review**
   - Request review from at least one team member
   - Address all feedback
   - Ensure code follows standards

3. **Integration Review**
   - Test integration with other components
   - Verify no breaking changes
   - Update shared documentation

### Testing Requirements

#### Unit Tests
- Test individual functions and classes
- Aim for >80% code coverage
- Use pytest framework

#### Integration Tests
- Test component interactions
- Test AWS service integrations
- Test end-to-end workflows

#### Performance Tests
- Benchmark critical paths
- Test under load
- Monitor resource usage

### Documentation Standards

#### Code Documentation
- Docstrings for all functions and classes
- Inline comments for complex logic
- Type hints for function parameters

#### README Files
- Clear setup instructions
- Usage examples
- Troubleshooting guides

#### Architecture Documentation
- System diagrams
- Component interactions
- Data flow descriptions

### AWS Resource Management

#### Naming Convention
- Prefix: `radstream-`
- Environment: `dev`, `staging`, `prod`
- Component: `images`, `results`, `telemetry`, `artifacts`

#### Example Resource Names
```
radstream-images-{account-id}
radstream-results-{account-id}
radstream-telemetry-{account-id}
radstream-artifacts-{account-id}
```

#### Cost Management
- Use free tier services when possible
- Implement cost monitoring
- Clean up test resources
- Use lifecycle policies

### Security Guidelines

#### Secrets Management
- Never commit secrets to git
- Use AWS Secrets Manager
- Rotate credentials regularly
- Use least privilege access

#### Code Security
- Validate all inputs
- Sanitize user data
- Use secure coding practices
- Regular security reviews

### Communication

#### Daily Standups
- Progress updates
- Blocker identification
- Next day priorities

#### Weekly Reviews
- Progress against timeline
- Risk assessment
- Plan adjustments

#### Issue Tracking
- Use GitHub Issues for bugs
- Use GitHub Projects for task tracking
- Label issues appropriately

### Release Process

#### Version Numbering
- Major.Minor.Patch (e.g., 1.0.0)
- Major: Breaking changes
- Minor: New features
- Patch: Bug fixes

#### Release Checklist
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Security review completed
- [ ] Performance benchmarks met
- [ ] Cost analysis completed

### Getting Help

#### Team Communication
- Use GitHub Discussions for questions
- Tag relevant team members
- Provide context and error messages

#### External Resources
- AWS Documentation
- Python Documentation
- Kubernetes Documentation
- GitHub Help

### Best Practices

#### Code Quality
- Write clean, readable code
- Follow PEP 8 for Python
- Use meaningful variable names
- Keep functions small and focused

#### Git Workflow
- Commit often with clear messages
- Use feature branches
- Keep main branch stable
- Regular rebasing and merging

#### AWS Best Practices
- Use Infrastructure as Code
- Implement monitoring and logging
- Follow security best practices
- Optimize for cost and performance

Remember: This is a collaborative project. Communication, code quality, and teamwork are key to success! 🚀
