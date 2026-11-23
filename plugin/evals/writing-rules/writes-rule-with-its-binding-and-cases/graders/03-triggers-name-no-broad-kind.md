---
type: regex
target: { source: file, path: .codeguard/bindings/exception-handling.yaml }
pattern: 'triggers:[^:]*?(\[|,|^\s*-)\s*(any|code|function-body|function-signature)\s*(,|\]|$)'
flags: m
match: not_contains
weight: 1
---
