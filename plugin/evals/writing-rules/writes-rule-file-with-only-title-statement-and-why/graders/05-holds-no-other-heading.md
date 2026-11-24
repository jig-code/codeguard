---
type: regex
target: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
pattern: '^#+ '
flags: m
match: "count:2"
weight: 1
---
