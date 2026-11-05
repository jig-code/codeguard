---
type: llm
focus: { source: file, path: .codeguard/gates/import-time-defaults-gate.yml }
weight: 1
---

The node this ast-grep gate matches is the one its top-level rule selects: its own `kind` or `pattern`, or each branch of a top-level `any` or `all`. An `inside`, `has` or `not` constraint narrows where it matches but doesn't change the node.

PASS if that node holds the code a violation of this rule needs, a parameter's default value, and nothing around it: a `default_parameter`, a `typed_default_parameter`, or the default value inside either. A node of another kind, such as a `call`, that the rule's constraints place as a parameter's default value is that default value and passes.
FAIL if that node holds code around the parameter, such as the parameter list, the function, class or decorated definition, a block or the module, or if it can match code that is not in a parameter's default value.
