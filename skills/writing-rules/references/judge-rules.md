# Writing a judge rule that judges reliably

A judge rule is ready when every eval case comes out the same way, for the same reason,
on every run. The judge gives a reason with every verdict, pass or fail, and each case
states the reason it expects; `codeguard eval` fails a case when the verdict or the
reason doesn't match. A result is unreliable when it flips between runs, rests on
another ground than the case states, is judged with low confidence, or comes back as a
warning. That is a defect in the rule's wording or in the case:

- Don't re-run until it passes.
- Don't loosen a gate to get past it.
- Don't add the failing case's code to the skill as an example, and don't add a
  carve-out for it. The judge would then pass the case by matching it, and the next
  piece of code fails the same way. Restate the convention so its statement decides the
  case, on the ground the case states.
- Don't change the rule's wording to get a weak case to pass. Fix the case, or drop it.

## Write the skill

The skill is the convention codeguard's judge reviews against, and the text the writing
agent loads before it edits. It holds, in this order, and nothing else:

1. A title.
2. The convention, as `SKILL.md` says to state it: one declarative sentence in the
   words a reviewer would use. "A function's result says what happened without the
   caller unpacking it", not "is this clean?". Where the sentence uses a term a reader
   could take two ways, a sentence that fixes its meaning.
3. `## Why`: the harm the rule prevents, in a sentence or two. It is part of the judge's
   prompt, so it helps the judge apply the convention to code the statement doesn't
   name, but it never widens the convention: the statement alone decides each case.

No examples. No `## Violation` list of the shapes a violation takes, and no `## Not a
violation` list of code near the boundary: each shape is decided by the statement, or
the statement is unclear. No forms of the convention in any language or library, and no
supplement per language: a rule in several languages is one skill, in no language's
names, syntax or libraries. Leave out the fix, and anything telling the judge how to
answer: the judge's own prompt sets its output and its confidence scale.

A judge that can't decide a piece of code from the statement, or decides it on the
wrong ground, has found an unclear statement. Reword the statement so it decides that
code. A rule that needs a new example each time it meets new code has a bad convention.

## Gate every form of the violation

A violation outside the binding's `triggers` is never reported; codeguard's README says
how triggers select what the judge sees.

- List the syntactic forms the violation takes, and give each one an `invalid` gate
  test, so a gate that stops matching a form fails `codeguard test`.
- Gate on where a violation appears, not on the rule's topic: a rule about passing enum
  members needs a gate on literals, because the enum is defined elsewhere.
- Gate on the narrowest node that holds the violation, such as the `except` clause
  rather than the whole `try`. A wider gate costs judge calls and tokens;
  `codeguard review --dry-run` counts the calls.

## Write a few clear eval cases

A rule eval has about three `invalid` and three `valid` cases per rule and language,
and a `skipped` case outside the gate. Each case tests one thing none of the others
does: a different thing the code does or fails to do, not another syntax for the same
thing. No edge cases: a case a reasonable reviewer could argue either way proves
nothing about the rule, and a judge that flips on it is right to.

- Each case states its `reason`: the ground the verdict rests on, in one sentence
  naming the code and what it does or fails to do. "The handler logs the exception with
  its traceback and re-raises it." The case passes only when the judge's reason gives
  the same ground, in whatever words. A `skipped` case states no reason.
- An `invalid` case breaks the rule beyond argument, and a `valid` case obviously keeps
  it. A reader of the case alone sees why the code is a problem or why it's fine, and
  its name says that, not only what the code does: "caller can't tell a new customer
  from an existing one", not "returns a tuple".
- A case tests one thing. It doesn't mix in a second defect, such as a CSV split on
  `","`, which is a bug whatever the rule says, so the judge can't flag the case for the
  wrong reason.
- Pair the cases: for what the convention allows, a `valid` case, and beside it an
  `invalid` case of the same shape that breaks the rule.
- A rule in several languages has cases in each, each case's `file` in its language.

A case is kept only while it is clear, tests something no other case does, and comes
from the statement or from a real miss. A new case comes only from a real miss: a review
that wrongly blocked or wrongly passed code. Write it as the smallest clear case of that
miss, state its reason, then reword the convention until the case passes on that reason;
never add the code to the skill. The bar stays 20 runs of 20, verdict and reason.
