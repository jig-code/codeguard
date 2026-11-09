---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Write a codeguard judge rule for this project: a parameter's default is the choice that can't destroy data when a caller leaves it out, which export_orders in src/shop/archive.py gets wrong with overwrite. Call the rule safe-defaults and its gate safe-defaults-gate. Give it a gate and an eval.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/archive.py, .codeguard/config.yaml
