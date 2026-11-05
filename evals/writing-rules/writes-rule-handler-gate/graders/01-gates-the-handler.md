---
type: llm
focus: { source: file, path: .codeguard/gates/handler-says-why-gate.yml }
weight: 1
---

The node this ast-grep gate matches is the one its top-level rule selects: its own `kind` or `pattern`, or each branch of a top-level `any` or `all`. An `inside`, `has` or `not` constraint narrows where it matches but doesn't change the node.

PASS if that node holds the code a violation of this rule needs, an exception handler and what it does, and nothing around it. An `except_clause` or an `except_group_clause` passes. A node inside a handler passes if it still holds everything that decides whether the handler re-raises or says why the failure is safe to ignore.
FAIL if that node holds code around the handler, such as the try statement, a block holding the try, a function, class or decorated definition or the module, or if it leaves out code that decides whether the handler keeps the convention.
