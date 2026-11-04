---
type: regex
target: { source: file, path: .codeguard/gates/import-time-defaults-gate.yml }
pattern: '^rule:[ \t]*\n(?:[ \t]*(?:#.*)?\n)*  kind:[ \t]*(?:parameters|lambda_parameters|function_definition|decorated_definition|class_definition|block|module)\b'
flags: m
match: not_contains
weight: 1
---
