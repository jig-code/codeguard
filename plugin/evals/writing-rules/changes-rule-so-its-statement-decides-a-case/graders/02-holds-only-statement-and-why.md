---
type: regex
target: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
pattern: '^#{2,} (?!Why\s*$)'
flags: m
match: not_contains
weight: 1
---
