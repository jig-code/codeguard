---
type: regex
target: { source: file, path: .codeguard/rules/judge/no-created-flag-results.md }
pattern: '^#{2,} (?!Why\s*$)'
flags: m
match: not_contains
weight: 1
---
