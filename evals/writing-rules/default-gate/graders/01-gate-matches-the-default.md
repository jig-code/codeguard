---
type: llm
focus: { source: file, path: .codeguard/gates/import-time-defaults-gate.yml }
weight: 1
---

PASS if the node this ast-grep gate's top-level rule selects (its own kind or pattern, or each branch of a top-level any/all; not an inside, has or not constraint) is one parameter with a default, `default_parameter` or `typed_default_parameter`, or the default value inside one.
FAIL if it selects the parameter list, the function, class or decorated definition, a block, the module, or any other node that contains the parameter.
