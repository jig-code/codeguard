---
type: regex
target: { source: file, path: .codeguard/gates/handler-says-why-gate.yml }
pattern: '^rule:[ \t]*\n(?:[ \t]*(?:#.*)?\n)*  kind:[ \t]*(?:try_statement|if_statement|with_statement|for_statement|while_statement|match_statement|expression_statement|block|function_definition|decorated_definition|class_definition|module)\b'
flags: m
match: not_contains
weight: 1
---
