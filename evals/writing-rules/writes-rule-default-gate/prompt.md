---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Write a codeguard judge rule for this project: a parameter's default is a value that can be computed once when the module loads, not something each call should compute afresh, which record in src/shop/audit.py gets wrong with stamp. Call the rule import-time-defaults and its gate import-time-defaults-gate. Give it a gate and an eval.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/audit.py, .codeguard/config.yaml
