---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Add a codeguard rule so every module in src/shop has a test file in tests/, the way src/shop/customers.py has tests/test_customers.py. codeguard isn't available here, so write the files without running it.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/customers.py, tests/test_customers.py, .codeguard/config.yaml
