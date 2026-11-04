---
type: regex
target: { source: file, path: .codeguard/bindings/import-time-defaults.yaml }
pattern: '(?:^triggers:[ \t]*\[?[ \t]*|,[ \t]*|^[ \t]+-[ \t]*)(?:any|code|comment|docstring|import|function-signature|function-body|test-function|fixture|helper-function|class-header|class-attribute|module-statement|annotation|call|control-flow|return-yield|collection-literal|string-literal|number-literal|attribute-access|subscript|conditional-expression|membership-test|assert|raise|definition-added-or-removed)(?=[ \t]*(?:[,\]]|$))'
flags: m
match: not_contains
weight: 1
---
