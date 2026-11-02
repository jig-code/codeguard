---
type: llm
focus: {source: file, path: .codeguard/rule-evals/created-flag-results.yaml}
weight: 1
---

This file follows codeguard's rule eval format: a top-level `cases` list and no other keys; each case has a `name`, `inputs` with `file` and `after` (and optionally `before` and `unchanged`), and `expected_output` with an `outcome` of `invalid`, `valid` or `skipped`.
