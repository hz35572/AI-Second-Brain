---
name: python-code-style
description: Python code style, linting, formatting, naming conventions, and documentation standards for this repository. Use when writing or reviewing Python code in the backend, configuring linters or type checkers, or establishing project standards.
---

# Python Code Style

Use this skill when working on Python code in this repository, especially under `backend/`.

## Project Baseline

- Target Python version: `3.11`
- Prefer modern type annotations on public APIs
- Keep imports absolute when possible
- Use clear, descriptive names over abbreviations
- Keep docstrings aligned with the code they describe

## Style Rules

### Formatting

- Prefer automated formatting over manual style debates
- Use a line length of `120` characters unless a file already follows a stricter local convention
- Keep function signatures and fluent chains wrapped for readability

### Tooling

- Prefer `ruff` for linting and formatting when configuring or updating Python tooling
- Prefer strict or near-strict type checking for production code
- If adding or changing tooling config, keep it consistent with `backend/pyproject.toml`

### Naming

- Modules and files: `snake_case`
- Classes: `PascalCase`
- Functions and variables: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`

### Imports

- Group imports as standard library, third-party, then local
- Prefer absolute imports over relative imports

### Docstrings

- Add docstrings to public functions, classes, and methods
- Use concise Google-style docstrings for complex APIs
- Document arguments, return values, and raised exceptions when the behavior is non-obvious

## Recommended Patterns

```python
from __future__ import annotations

from typing import Any

import httpx

from app.core.settings import Settings


DEFAULT_TIMEOUT_SECONDS = 30


def get_timeout(settings: Settings) -> int:
    """Return the configured timeout in seconds."""
    return settings.request_timeout_seconds or DEFAULT_TIMEOUT_SECONDS
```

```toml
# Suggested baseline if the project adds ruff config later
[tool.ruff]
line-length = 120
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
```

## Practical Checklist

Before finalizing Python changes:

1. Check imports are ordered and absolute
2. Check public APIs have type hints
3. Check public functions and classes have docstrings
4. Check line length and wrapping are readable
5. Check the change matches existing backend conventions
