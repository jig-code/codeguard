---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Write a codeguard judge rule for this project: our own functions shouldn't return a (thing, created) pair, the way find_or_create_customer in src/shop/customers.py does. Call the rule no-created-flag-results. Give it an eval.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/customers.py, .codeguard/config.yaml
