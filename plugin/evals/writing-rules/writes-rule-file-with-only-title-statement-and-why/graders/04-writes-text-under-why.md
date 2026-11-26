---
type: regex
target: { source: file, path: .codeguard/rules/judge/no-secrets-in-logs.md }
pattern: '^## Why[ \t]*\n\s*[^#\s]'
flags: m
weight: 1
---
