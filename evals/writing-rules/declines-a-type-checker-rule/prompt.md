---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Add a codeguard rule to this project so code never uses a value typed Any, like the result of json.loads in load_settings in src/shop/customers.py, until it has been narrowed to a real type. codeguard isn't available here, so write the files without running it.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/customers.py, .codeguard/config.yaml
