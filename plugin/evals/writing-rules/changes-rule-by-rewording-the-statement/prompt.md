---
tags: [skill-creator]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

codeguard reports the handler in the no-swallowed-exceptions rule's eval case 'a handler that logs the error and re-raises'. Fix the rule.

Input files: .codeguard/rules/judge/no-swallowed-exceptions.md, .codeguard/bindings/no-swallowed-exceptions.yaml, .codeguard/rule-evals/no-swallowed-exceptions.yaml, src/shop/__init__.py, src/shop/orders.py
