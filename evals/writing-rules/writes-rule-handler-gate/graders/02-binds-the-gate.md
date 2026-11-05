---
type: regex
target: { source: file, path: .codeguard/bindings/handler-says-why.yaml }
pattern: '^triggers:[\s\S]*\bhandler-says-why-gate\b'
flags: m
weight: 1
---
