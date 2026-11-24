---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Add a codeguard judge rule, no-secrets-in-logs, that flags code that logs a password, token or API key.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/accounts.py
