# Writing a judge rule

## Write the rule file

The rule file, `rules/judge/<id>.md`, is the convention codeguard's judge reviews against,
and the judge gets its text unparsed. It holds, in this order, and nothing else:

1. A title.
2. The convention: one declarative sentence, stated as the writing-rules skill's The
   convention section says. It goes directly under the title, with no heading of its own.
3. `## Why`: the harm the rule prevents, in a sentence or two. It is part of the judge's
   prompt, so it helps the judge apply the convention to code the statement doesn't
   name, but it never widens the convention: the statement alone decides each case.

Nothing else goes in the rule file, in any section or for any language: each piece of
code is decided by the statement, or the statement is unclear. Leave out the fix, and anything telling the judge how to answer: the judge's own prompt sets its
output.

## Gate every form of the violation

A violation outside the binding's `triggers` is never reported; codeguard's
`docs/rule-formats.md` (A judge rule's binding) says how triggers select what the judge
sees.

- List the syntactic forms the violation takes, and give each one an `invalid` gate
  test, so a gate that stops matching a form fails `codeguard test`.
- Gate on where a violation appears in the changed code, not on the rule's topic: what
  the topic names may be defined elsewhere, in code the change doesn't touch.
- Gate on the narrowest node that holds the violation. A wider gate costs judge calls
  and tokens;
  `codeguard review --dry-run` counts the calls.
- A trigger is a built-in change kind or a gate. The built-in kinds are `comment`,
  `docstring`, `import`, `function-signature`, `function-body`, `test-function`,
  `fixture`, `helper-function`, `class-header`, `class-attribute`, `module-statement`,
  `annotation`, `call`, `control-flow`, `return-yield`, `collection-literal`,
  `string-literal`, `number-literal`, `attribute-access`, `subscript`,
  `conditional-expression`, `membership-test`, `assert`, `raise`,
  `definition-added-or-removed`, `code` and `any`. When no kind fits the node, write a
  gate: an ast-grep rule in `gates/<id>.yml` that matches the node, named in `triggers`
  and tested like a pattern rule.

## Write a few clear eval cases

A rule eval has a few cases per rule and language: one `invalid` case for each distinct
ground on which code breaks the convention and one `valid` case for each distinct
situation near the boundary in which code keeps it, and a `skipped` case outside the
gate. A convention broken on one ground has one `invalid` case. No edge cases: a case that a reasonable reviewer could
argue either way proves nothing about the rule, and a judge that flips on it is right to.

- An `invalid` case breaks the convention beyond argument, and a `valid` case obviously
  keeps it. A reader of the case alone sees why the code is a problem or why it's fine.
- Each case also follows the writing-rules skill's Cases section: its name, one ground
  per case, and one defect at most.
- A rule in several languages has cases in each, each case's `file` in its language.

A case is kept only while it is clear, tests something no other case does, and comes
from the statement or from a real miss. A new case comes only from a real miss: a review
that wrongly blocked or wrongly passed code. Write it as the smallest clear case of that
miss.
