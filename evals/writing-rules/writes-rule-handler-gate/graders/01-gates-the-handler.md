---
type: llm
focus: { source: file, path: .codeguard/gates/handler-says-why-gate.yml }
weight: 1
---

The node this ast-grep gate matches is the one its top-level rule selects: its own `kind` or `pattern`, or each branch of a top-level `any` or `all`. An `inside`, `has` or `not` constraint narrows where it matches but doesn't change the node.

The skill says: "A gate matches the code a violation needs and nothing around it: not the statement, block or function that holds that code."

PASS if that node is the code the violation is in, an exception handler, or a part of it, and not code that holds it.
FAIL if not: for example the node is code that holds it, such as the try statement, a block holding the try, the function, class or decorated definition or the module, or code unrelated to it.
