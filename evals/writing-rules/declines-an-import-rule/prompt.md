---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Add a codeguard rule so src/shop/billing.py never imports from shop.customers: billing must not depend on customer code. codeguard isn't available here, so write the files without running it.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/billing.py, src/shop/customers.py, .codeguard/config.yaml
