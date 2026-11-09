---
type: llm
focus: { source: file, path: .codeguard/gates/safe-defaults-gate.yml }
weight: 1
---

The node this ast-grep gate matches is the one its top-level rule selects: its own `kind` or `pattern`, or each branch of a top-level `any` or `all`. An `inside`, `has` or `not` constraint narrows where it matches but doesn't change the node.

The skill says: "A gate matches the code a violation needs and nothing around it: not the statement, block or function that holds that code."

PASS if that node is the code the violation is in, a parameter with a default, or a part of it such as the default value, and not code that holds the parameter.
FAIL if that node is code that holds the parameter, such as the parameter list, the function, class or decorated definition, a block or the module.
