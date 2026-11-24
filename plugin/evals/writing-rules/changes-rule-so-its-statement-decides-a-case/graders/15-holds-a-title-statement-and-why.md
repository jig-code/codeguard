---
type: regex
target: { source: file, path: .codeguard/rules/judge/no-swallowed-exceptions.md }
pattern: '^# .+\n\n.+(?:\n.+)*\n\n## Why\s*\n'
match: contains
weight: 1
---
