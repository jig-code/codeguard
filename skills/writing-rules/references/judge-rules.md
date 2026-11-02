# Writing a judge rule that judges reliably

A judge rule is ready when every eval case comes out the same way on every run. A
result is unreliable when it flips between runs, is judged with low confidence, or comes
back as a warning. That is a defect in the rule or in the case:

- Don't re-run until it passes.
- Don't loosen a gate to get past it.
- Don't add a failing case's code to the skill as an example. The case would then pass
  by memory; restate the convention instead.

## Write the skill

The skill is the convention codeguard's judge reviews against. The judge reports each
violation of it on a changed line a fix would change, and gives its highest confidence
to code that matches a case, sign or example the skill describes. Write the skill in
this order:

1. A title.
2. The convention, as `SKILL.md` says to state it: "A function named as a query
   changes no state", not "is this clean?".
3. Definitions of the convention's terms.
4. `## Violation`: statements of what breaks the convention, and the line a violation is
   reported on: the line a fix would change. The judge reports a violation only where a
   fix changes a changed line.
5. The language's and its common libraries' forms on both sides of the convention, as
   illustrations of it. A judge wavers on code in a form the skill doesn't place, such
   as a framework's validated data or an ORM's rows.
6. `## Not a violation`: code near the boundary that keeps the convention.
7. `## Why`: the harm the rule prevents, in one or two sentences. It is part of the
   judge's prompt, so it helps the judge apply the convention to code the examples don't
   name, but it never widens the convention: the convention alone decides each case.
   Leave out the fix and the alternative to the flagged code: the judge reads them as
   more conventions to apply.

For a rule in several languages, `SKILL.md` holds every item but the forms (5), in no
language's names, syntax, libraries or frameworks. Each language's supplement, which the
judge reads after it, holds that language's forms on both sides and its framework code
that keeps the convention. A supplement places the language's code on either side of the
convention; it never changes or widens it.

Leave out the fix, and anything telling the judge how to answer: the judge's own prompt
sets its output and its confidence scale. A question inside the skill can walk the judge
through a hard case ("follow the value: does it go into building a declared value?");
the convention itself is never a question.

When a judge can't decide a case, restate the convention so the case is decided by it.

## Gate every form of the violation

A violation outside the binding's `triggers` is never reported; codeguard's README says
how triggers select what the judge sees.

- List the syntactic forms the violation takes, including forms the skill doesn't name,
  and give each one an `invalid` gate test, so a gate that stops matching a form fails
  `codeguard test`.
- Gate on where a violation appears, not on the rule's topic: a rule about passing enum
  members needs a gate on literals, because the enum is defined elsewhere.
- Gate on the narrowest node that holds the violation, such as the `except` clause
  rather than the whole `try`. A wider gate costs judge calls and tokens;
  `codeguard review --dry-run` counts the calls.

## Write eval cases at the boundary

- Every judge rule's eval has an `invalid` case.
- A case shows what's at stake. A reader of the case alone sees why the code is a
  problem or why it's fine, and its name says that, not only what the code does:
  "a getter that saves surprises a caller who only reads", not "calls save".
- A case tests one thing. Besides its one point, it holds no code a reviewer could
  question, so the judge can't flag the case for the wrong reason. Any other code that
  might be a defect is a second defect: a CSV split on `","`, a parse that raises on
  input it should handle, a function named as a check that writes. If you're unsure
  whether a line could be questioned, rewrite it so it can't be. A helper the case
  calls without defining it isn't a second defect: the judge treats code it can't see as
  ordinary.
- Pair the cases: for each form the convention allows, a `valid` case, and beside it an
  `invalid` case of the same shape that breaks the rule.
- Add `invalid` cases in forms the skill doesn't name, so the eval shows the judge
  applies the convention rather than matching its examples.
- A rule in several languages has cases in each, each case's `file` in its language.
- A case never reuses code from the skill's examples: not the same snippet, and not the
  same code with renamed identifiers or changed literals. Use different code, a
  different domain and different names that keep or break the same convention. The
  judge gives its highest confidence to code that matches an example the skill
  describes, so a case that copies an example measures that match, not whether the
  judge applies the convention, and proves nothing.
