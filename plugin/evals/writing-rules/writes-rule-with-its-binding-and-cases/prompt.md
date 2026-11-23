---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Add a codeguard rule, exception-handling, so that every exception handler that catches a failure does one of these three things with the exception: re-raises it, makes the function it is in return an error instead of a normal result, or logs it.

Input files: pyproject.toml, src/shop/__init__.py, src/shop/orders.py
