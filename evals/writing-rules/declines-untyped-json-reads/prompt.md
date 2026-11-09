---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Add a codeguard rule to this project so code never uses the result of json.loads (or yaml.safe_load, or a response's .json()) without validating it first.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/customers.py, .codeguard/config.yaml
