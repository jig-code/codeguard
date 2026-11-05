---
type: regex
target: { source: file, path: .codeguard/rule-evals/no-created-flag-results.yaml }
pattern: '^([ \t]*)(?=-[ \t])(?=(?:(?!\n(?!\1[ \t]|[ \t]*(?:\n|$)))[\s\S])*?(?:[-{,][ \t]*|\n[ \t]*)["'']?(?:name|inputs|expected_output)["'']?:[ \t]*["'']?)(?!(?=(?:(?!\n(?!\1[ \t]|[ \t]*(?:\n|$)))[\s\S])*?(?:[-{,][ \t]*|\n[ \t]*)["'']?name["'']?:[ \t]*["'']?[Ff]lags\b)(?=(?:(?!\n(?!\1[ \t]|[ \t]*(?:\n|$)))[\s\S])*?(?:[-{,][ \t]*|\n[ \t]*)["'']?outcome["'']?:[ \t]*["'']?invalid\b)|(?=(?:(?!\n(?!\1[ \t]|[ \t]*(?:\n|$)))[\s\S])*?(?:[-{,][ \t]*|\n[ \t]*)["'']?name["'']?:[ \t]*["'']?[Aa]llows\b)(?=(?:(?!\n(?!\1[ \t]|[ \t]*(?:\n|$)))[\s\S])*?(?:[-{,][ \t]*|\n[ \t]*)["'']?outcome["'']?:[ \t]*["'']?valid\b)|(?=(?:(?!\n(?!\1[ \t]|[ \t]*(?:\n|$)))[\s\S])*?(?:[-{,][ \t]*|\n[ \t]*)["'']?name["'']?:[ \t]*["'']?[Ss]kips\b)(?=(?:(?!\n(?!\1[ \t]|[ \t]*(?:\n|$)))[\s\S])*?(?:[-{,][ \t]*|\n[ \t]*)["'']?outcome["'']?:[ \t]*["'']?skipped\b))|^cases:[ \t]*\['
flags: m
match: not_contains
weight: 1
---
