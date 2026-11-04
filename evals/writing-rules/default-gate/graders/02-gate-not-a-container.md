---
type: regex
target: { source: file, path: .codeguard/gates/import-time-defaults-gate.yml }
pattern: '^rule:[ \t]*(?:\{[ \t]*kind:[ \t]*(?:parameters|lambda_parameters|function_definition|decorated_definition|class_definition|block|module)\b|\n(?:[ \t]*(?:#.*)?\n)*(?:  kind:[ \t]*(?:parameters|lambda_parameters|function_definition|decorated_definition|class_definition|block|module)\b|  pattern:[ \t]*(?:[|>][-+]?[ \t]*\n[ \t]+)?["'']?(?:(?:def|async|class|lambda)\b|@|\()|  (?:any|all):[ \t]*\n(?:(?:      .*|    -.*|[ \t]*(?:#.*)?)\n)*?    -[ \t]*(?:kind:[ \t]*(?:parameters|lambda_parameters|function_definition|decorated_definition|class_definition|block|module)\b|pattern:[ \t]*(?:[|>][-+]?[ \t]*\n[ \t]+)?["'']?(?:(?:def|async|class|lambda)\b|@|\())))'
flags: m
match: not_contains
weight: 1
---
