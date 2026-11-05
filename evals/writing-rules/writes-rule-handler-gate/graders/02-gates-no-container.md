---
type: regex
target: { source: file, path: .codeguard/gates/handler-says-why-gate.yml }
pattern: '^rule:[ \t]*(?:\{[ \t]*kind:[ \t]*(?:try_statement|if_statement|with_statement|for_statement|while_statement|match_statement|expression_statement|function_definition|decorated_definition|class_definition|module)\b|\n(?:[ \t]*(?:#.*)?\n)*(?:  kind:[ \t]*(?:try_statement|if_statement|with_statement|for_statement|while_statement|match_statement|expression_statement|function_definition|decorated_definition|class_definition|module)\b|  pattern:[ \t]*(?:[|>][-+]?[ \t]*\n[ \t]+)?["'']?(?:(?:try|if|with|for|while|match|def|async|class)\b|@)|  (?:any|all):[ \t]*\n(?:(?:      .*|    -.*|[ \t]*(?:#.*)?)\n)*?    -[ \t]*(?:kind:[ \t]*(?:try_statement|if_statement|with_statement|for_statement|while_statement|match_statement|expression_statement|function_definition|decorated_definition|class_definition|module)\b|pattern:[ \t]*(?:[|>][-+]?[ \t]*\n[ \t]+)?["'']?(?:(?:try|if|with|for|while|match|def|async|class)\b|@))))'
flags: m
match: not_contains
weight: 1
---
