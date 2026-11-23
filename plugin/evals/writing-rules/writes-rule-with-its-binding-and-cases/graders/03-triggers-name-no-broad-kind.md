---
type: regex
target: { source: file, path: .codeguard/bindings/exception-handling.yaml }
pattern: 'triggers:[^:]*\b(any|code|function-body|function-signature)\b'
match: not_contains
weight: 1
---
