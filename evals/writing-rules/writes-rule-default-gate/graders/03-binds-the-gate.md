---
type: regex
target: { source: file, path: .codeguard/bindings/import-time-defaults.yaml }
pattern: '^triggers:[\s\S]*\bimport-time-defaults-gate\b'
flags: m
weight: 1
---
