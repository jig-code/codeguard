---
type: regex
target: { source: file, path: .codeguard/gates/handler-says-why-gate.yml }
pattern: '^rule:[ \t]*(?:\{[ \t]*kind:[ \t]*(?:except_clause|except_group_clause)\b|\n(?:[ \t]*(?:#.*)?\n)*(?:  kind:[ \t]*(?:except_clause|except_group_clause)\b|  pattern:[ \t]*(?:[|>][-+]?[ \t]*\n[ \t]+)?["'']?except\b|  kind:[ \t]*block\b[\s\S]*?^  inside:[ \t]*(?:\{[ \t]*kind:[ \t]*(?:except_clause|except_group_clause)\b|\n    kind:[ \t]*(?:except_clause|except_group_clause)\b)|  (?:any|all):[ \t]*\n(?:(?:      .*|    -.*|[ \t]*(?:#.*)?)\n)*?    -[ \t]*(?:kind:[ \t]*(?:except_clause|except_group_clause)\b|pattern:[ \t]*(?:[|>][-+]?[ \t]*\n[ \t]+)?["'']?except\b)))'
flags: m
weight: 1
---
