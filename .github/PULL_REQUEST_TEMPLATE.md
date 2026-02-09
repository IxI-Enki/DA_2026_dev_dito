## Summary

<!-- Brief description of what this PR does and why -->


## Spec Reference

- **Spec Directory**: `specs/NNN-feature-name/`
- **GitHub Issue**: Relates to #

<!-- Use "Closes #N" only when the feature is fully complete and human-reviewed -->

## Changes

<!-- List the key changes in this PR -->

-
-
-

## Checklist

### Spec Kit Compliance

- [ ] `spec.md` exists for this feature branch
- [ ] `plan.md` exists (or N/A for bug fixes)
- [ ] `tasks.md` exists (or N/A for bug fixes)

### Code Quality (Constitution Articles III, IV)

- [ ] Tests added or updated
- [ ] All tests pass (`pytest tests/`)
- [ ] Python linting passes (`ruff check .` + `black --check .`)
- [ ] PHP follows PSR-12 (if applicable)

### Security (Constitution Article VI)

- [ ] No secrets in diff (API keys, tokens, passwords)
- [ ] No hardcoded URLs or paths (use config/env.yaml)
- [ ] Secret files referenced via `*_file` pattern, not inline values

### Documentation

- [ ] Code has docstrings/PHPDoc for public functions
- [ ] README updated if public API changed

## Test Results

<!-- Paste or summarize test output -->

```
pytest tests/ -v --tb=short
```

## Screenshots / Evidence

<!-- If applicable, add screenshots or terminal output -->
