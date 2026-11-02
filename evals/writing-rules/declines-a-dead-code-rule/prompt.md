---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Add a codeguard judge rule that flags a function nobody calls any more, like legacy_export in src/shop/customers.py. codeguard isn't available here, so write the files without running it.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/customers.py, .codeguard/config.yaml
