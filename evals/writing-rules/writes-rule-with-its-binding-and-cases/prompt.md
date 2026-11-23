---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Add a codeguard rule, exception-handling, so that an exception handler re-raises the exception it caught, returns an error to its caller, or logs the exception with its traceback.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/orders.py
