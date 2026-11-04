---
type: regex
target: { source: file, path: .codeguard/gates/handler-says-why-gate.yml }
pattern: '\b(?:except_clause|except)\b'
flags: m
weight: 1
---
