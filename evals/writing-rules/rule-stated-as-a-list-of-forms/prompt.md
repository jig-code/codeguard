---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

The case 'logs the error and re-raises' in the no-swallowed-exceptions rule's eval, .codeguard/rule-evals/no-swallowed-exceptions.yaml, flips between valid and invalid across codeguard eval --repeat 20 runs (it failed 7 of 20 as invalid). Fix it. codeguard isn't available here, so change the files without running it.

Input files: .codeguard/config.yaml, .codeguard/skills/no-swallowed-exceptions/SKILL.md, .codeguard/bindings/no-swallowed-exceptions.yaml, .codeguard/rule-evals/no-swallowed-exceptions.yaml, src/shop/__init__.py, src/shop/orders.py
