---
type: regex
target: { source: file, path: .codeguard/bindings/no-swallowed-exceptions.yaml }
pattern: '(^|[\s\[,])(any|code|function-body|function-signature)([\s\],]|$)'
flags: m
match: not_contains
weight: 1
---
