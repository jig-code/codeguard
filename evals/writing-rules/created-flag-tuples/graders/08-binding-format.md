---
type: llm
focus: {source: file, path: .codeguard/bindings/created-flag-results.yaml}
weight: 1
---

This binding follows codeguard's format: `skill: .codeguard/skills/created-flag-results`, a `paths` list of globs, and a `triggers` list whose entries are codeguard change kinds (such as `return-yield` or `function-signature`) or gate ids.
