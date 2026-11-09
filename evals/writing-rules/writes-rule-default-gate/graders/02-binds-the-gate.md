---
type: regex
target: { source: file, path: .codeguard/bindings/safe-defaults.yaml }
pattern: '^triggers:[\s\S]*\bsafe-defaults-gate\b'
flags: m
weight: 1
---
