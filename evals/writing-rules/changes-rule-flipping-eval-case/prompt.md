---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

The case 'a handler that logs the error and re-raises' in .codeguard/rule-evals/no-swallowed-exceptions.yaml flips between valid and invalid across codeguard eval --repeat 3 runs. Fix it.

Input files: .codeguard/config.yaml, .codeguard/skills/no-swallowed-exceptions/SKILL.md, .codeguard/bindings/no-swallowed-exceptions.yaml, .codeguard/rule-evals/no-swallowed-exceptions.yaml, src/shop/__init__.py, src/shop/orders.py
