# Writing a judge rule

## Write the rule file

The rule file, `rules/judge/<id>.md`, holds these, in order, and nothing else:

1. A title.
2. The statement, written as The convention section in `SKILL.md` says, directly under
   the title with no heading of its own.
3. `## Why`: the harm the rule prevents, in a sentence or two. It helps a reader apply the
   statement to code the statement doesn't name, but never widens it: the statement alone
   decides each case.

Leave out the fix and anything else. If the statement doesn't decide a piece of code, the
statement is unclear.

## Gate every form of the violation

A violation that no trigger in the binding matches is never reported; codeguard's
`docs/rule-formats.md` (A judge rule's binding) says how triggers work.

- Give each form the violation can take an `invalid` gate test, so a gate that stops
  matching a form fails `codeguard test`.
- Gate on where the violation appears in the changed code, not on the rule's topic: what
  the topic names may be defined in code the change doesn't touch.
- Gate on the smallest piece of code that holds the violation. A wider gate runs the rule
  on more changes; `codeguard review --dry-run` counts them.
- A trigger is a built-in change kind or a gate. The built-in kinds are `comment`,
  `docstring`, `import`, `function-signature`, `function-body`, `test-function`,
  `fixture`, `helper-function`, `class-header`, `class-attribute`, `module-statement`,
  `annotation`, `call`, `control-flow`, `return-yield`, `collection-literal`,
  `string-literal`, `number-literal`, `attribute-access`, `subscript`,
  `conditional-expression`, `membership-test`, `assert`, `raise`,
  `definition-added-or-removed`, `code` and `any`. When no kind fits, write a gate: an
  ast-grep rule in `gates/<id>.yml` that matches that code, named in `triggers` and
  tested like a pattern rule.

## Write a few clear eval cases

Write one `invalid` case for each different reason code breaks the rule, one `valid` case
for each different situation close to the line where code keeps it, and one `skipped`
case outside the gate.

- Make every case clear: an `invalid` case breaks the rule beyond argument, and a `valid`
  case plainly keeps it. A case a reasonable reviewer could argue either way proves
  nothing.
- Follow the Cases section of `SKILL.md` too: names, one reason per case, one defect at
  most.
- A rule in several languages has cases in each, each case's `file` in its language.

Write the first cases from the statement. After that, add a case only after a real miss,
a review that wrongly blocked or wrongly passed code, and write it as the smallest clear
case of that miss. Keep a case only while it's clear and tests something no other case
does.
