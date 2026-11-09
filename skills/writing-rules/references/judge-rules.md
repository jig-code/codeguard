# Writing a judge rule

Don't add a case's code to the skill as an example, and don't add a carve-out for it.
Restate the convention so its statement decides the case.

## Write the skill

The skill is the convention codeguard's judge reviews against, and the text the writing
agent loads before it edits. It holds, in this order, and nothing else:

1. A title.
2. The convention, as `SKILL.md` says to state it: one declarative sentence in the
   words a reviewer would use, never a question. Where the sentence uses a term a reader
   could take two ways, one sentence that fixes its meaning, and no other: a sentence,
   or a clause joined to the convention's sentence, that restates the convention or says
   what it doesn't cover is a second statement.
3. `## Why`: the harm the rule prevents, in a sentence or two. It never widens the
   convention: the statement alone decides each case.

No examples. No `## Violation` list of the shapes a violation takes, no `## Not a
violation` list of code near the boundary, and no other section: each shape is decided
by the statement, or the statement is unclear. A shape that contradicts the statement
(a shape that the statement says keeps the convention) is dropped from the rule or moved
to a rule of its own; its mention in the skill, even as a non-violation, is a second
convention. No shapes of the convention in any language or library, and no supplement
per language: a rule in several languages is one skill, in no language's names, syntax
or libraries. Leave out the fix, and anything telling the judge how to answer.

## Gate every shape of the violation

- List the syntactic shapes the violation takes in the gate's tests, not in the rule's
  text: give each one an `invalid` gate test, so a gate that stops matching a shape
  fails a test.
- Gate on where a violation appears in the changed code, not on where the rule's topic
  is defined.
- A gate matches the code a violation needs and nothing around it: not the statement,
  block or function that holds that code. The judge is sent the whole of each node a
  gate matches, and is called for every change inside one.
- A trigger is a built-in change kind (codeguard's README, The binding, lists them) or
  a gate. When no kind fits the node, write a gate: an ast-grep rule in `gates/<id>.yml`
  that matches the node, named in `triggers` and tested like a pattern rule.

## Write a few clear eval cases

A rule eval has a few cases per rule and language: one `invalid` case for each distinct
way code breaks the convention and one `valid` case for each distinct way code keeps it,
and a `skipped` case outside the gate. A convention with one way to break it has one
`invalid` case. Each case tests one thing
none of the others does: a different thing the code does or fails to do, not another
syntax for the same thing. No edge cases: a case a reasonable reviewer could argue
either way proves nothing about the rule.

- An `invalid` case breaks the convention beyond argument, and a `valid` case obviously
  keeps it. A reader of the case alone sees why the code is a problem or why it's fine.
  It is named as `SKILL.md` says.
- Two cases that break or keep the convention on the same ground are one case, however
  their syntax, names or annotations differ: keep the clearer one. Two `valid` cases
  differ when their code keeps the convention in different situations, not merely by
  both lacking the violation. Before writing a case, say in one sentence what its code
  does or fails to do; a sentence another case already has means the case isn't written.
- A case tests one thing. Every line of it but the one under test is plainly correct
  code: a second bug anywhere in the case, whatever the rule says about it, lets the
  judge flag the case for the wrong reason. Read each line as a reviewer would before
  keeping the case.
- A rule in several languages has cases in each, each case's `file` in its language.

A case is kept only while it is clear, tests something no other case does, and comes
from the statement or from a real miss. A new case comes only from a real miss: a review
that wrongly blocked or wrongly passed code. Write it as the smallest clear case of that
miss; never add the code to the skill.
