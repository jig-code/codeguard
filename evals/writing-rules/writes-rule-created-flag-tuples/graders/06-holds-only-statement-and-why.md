---
type: regex
target: { source: file, path: .codeguard/skills/no-created-flag-results/SKILL.md }
pattern: '^#{2,} (?!Why\s*$)'
flags: m
match: not_contains
weight: 1
---
