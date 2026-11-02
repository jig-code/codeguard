---
type: llm
focus: {source: file, path: .codeguard/bindings/created-flag-results.yaml}
weight: 1
---

Each trigger in this binding gates a node where a violation of this rule appears: `return-yield` (what a function returns or yields), `function-signature` (its return annotation), `class-attribute` (a field of a class the function returns, such as a named tuple's flag), or a gate the rule defines on those nodes. Any other of codeguard's built-in triggers fails, because it fires on edits where no violation appears: `comment`, `docstring`, `import`, `function-body`, `test-function`, `fixture`, `helper-function`, `class-header`, `module-statement`, `annotation`, `call`, `control-flow`, `collection-literal`, `string-literal`, `number-literal`, `attribute-access`, `subscript`, `conditional-expression`, `membership-test`, `assert`, `raise`, `definition-added-or-removed`, `code` and `any`.
