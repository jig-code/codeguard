---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Add a codeguard rule to this project so code never uses the untyped result of json.loads (or yaml.safe_load, or a response's .json()) before giving it a type.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/customers.py, .codeguard/config.yaml
