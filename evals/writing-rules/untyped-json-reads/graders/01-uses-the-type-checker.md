---
type: llm
focus: { source: file, path: pyproject.toml }
weight: 1
---

This pyproject.toml turns on a type checker setting that reports values typed Any, such as basedpyright's reportAny = "error" (or mypy's disallow_any_expr), so untyped reads are caught by the type checker rather than a codeguard rule.
