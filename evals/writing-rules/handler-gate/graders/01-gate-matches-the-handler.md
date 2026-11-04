---
type: llm
focus: { source: file, path: .codeguard/gates/handler-says-why-gate.yml }
weight: 1
---

PASS if the node this ast-grep gate's top-level rule selects (its own kind or pattern, or each branch of a top-level any/all; not an inside, has or not constraint) is the exception handler clause, `except_clause`.
FAIL if it selects the try statement, a block, a function, class or decorated definition, the module, or any other node that contains the handler.
