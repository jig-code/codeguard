---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Write a codeguard judge rule for this project, with the id created-flag-results: our own functions shouldn't return a (thing, created) pair, the way find_or_create_customer in src/shop/customers.py does. Give it an eval. codeguard isn't available here, so write the files without running it.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/customers.py, .codeguard/config.yaml
