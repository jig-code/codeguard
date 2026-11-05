---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Write a codeguard judge rule for this project: an exception handler that doesn't re-raise says why the failure is safe to ignore, which load_rates in src/shop/rates.py doesn't. Call the rule handler-says-why and its gate handler-says-why-gate. Give it a gate and an eval.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/rates.py, .codeguard/config.yaml
