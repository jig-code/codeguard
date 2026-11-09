---
type: regex
target: { source: file, path: .codeguard/skills/no-swallowed-exceptions/SKILL.md }
pattern: '^# .*\n(?:(?!^##)[^?])*\?|^# .*\n(?:(?!^##)[\s\S])*?[.!](?=\s)(?:(?!^##)[\s\S])*?[.!](?=\s)(?:(?!^##)[\s\S])*?[.!](?=\s)(?:(?!^##)[\s\S])*?^## '
flags: m
match: not_contains
weight: 1
---
