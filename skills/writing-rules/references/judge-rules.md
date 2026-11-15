# Writing a judge rule that judges reliably

A judge rule is ready when every eval case comes out the same way on every run. A case
that flips between runs, is judged with low confidence, or comes back as a warning shows
a defect in the rule or in the case. Fix that defect:

- Make the case clear, or drop it. Re-running until it passes hides the defect.
- Keep the gate as narrow as it was. Loosening it to get past a case hides the defect too.
- Restate the convention when the judge can't decide a case. Bending the wording to pass
  one weak case, or adding the case's code to the skill as an example, makes the case
  pass by memory instead of by the convention.

## Write the skill

The skill is what codeguard's judge reviews a change against. The judge reports each
violation on a changed line that a fix would change. It is most confident on code that
looks like an example in the skill, which is why the eval's cases use different code
(below). Write the skill in this order:

1. A title.
2. The convention, stated as `SKILL.md` says: "A function's result says what happened
   without the caller unpacking it", not "is this clean?".
3. Definitions of the convention's terms.
4. `## Violation`: what breaks the convention, and the line a violation is reported on:
   the line a fix would change.
5. Examples: code in the language and its common libraries that keeps the convention,
   and code that breaks it. Add an example for any code the judge can't place on its
   own, such as a framework's validated data or an ORM's rows.
6. `## Not a violation`: code near the boundary that keeps the convention.
7. `## Why`: the harm the rule prevents. The judge reads it too, so it helps the judge
   decide code no example shows, but the convention alone decides each case.

For a rule in several languages, `SKILL.md` holds every item but the examples (5), in
words that belong to no language. Each language's supplement (`python.md`,
`typescript.md`), which the judge reads after `SKILL.md`, holds that language's examples.
A supplement shows where the language's code falls; it never changes the convention.

Leave out the fix, and anything about how to answer: the judge's own prompt sets its
output and confidence scale. A question can walk the judge through a hard case ("follow
the value: does it go into building a declared value?"), but the convention itself is a
statement.

When the judge can't decide a case, restate the convention so the convention decides it.
A carve-out for the code that was just flagged fixes one case; a rule that needs a new
example for each new piece of code has a convention that isn't clear yet.

## Gate every way the violation is written

The judge never sees a change outside the binding's `triggers`; codeguard's README says
how triggers select what the judge sees.

- List every way the violation can be written, including ways the skill doesn't show,
  and give each one an `invalid` gate test, so a gate that stops matching one fails
  `codeguard test`.
- Gate on where a violation appears, not on the rule's topic: a rule about passing enum
  members needs a gate on literals, because the enum is defined elsewhere.
- Gate on the narrowest node that holds the violation, such as the `except` clause
  rather than the whole `try`. A wider gate costs judge calls and tokens;
  `codeguard review --dry-run` counts the calls.

## Write eval cases

The eval shows that the judge applies the convention, not that it recognises the skill's
examples.

- Every eval has an `invalid` case.
- Each case is clear. An `invalid` case breaks the rule beyond argument, a `valid` case
  obviously keeps it, and a `skipped` case is outside the gate. If a reviewer could argue
  a case either way, make it clear or remove it.
- A case's name says why the code breaks or keeps the rule: "caller can't tell a new
  customer from an existing one", not "returns a tuple".
- A case tests one thing. It holds no second bug, such as a CSV split on `","`, that the
  judge could flag instead.
- For each example in the skill, write a `valid` case and an `invalid` case of the same
  shape.
- Write at least one `invalid` case that breaks the convention with a construct the skill
  doesn't show. To choose it, list the constructs the skill's examples use, then pick one
  that isn't on the list. An example's construct inside something else is still on the
  list: if an example is a written-out list, a membership test over a written-out list
  is that example. A judge that catches only what the skill shows is matching examples.
- Write each case's code fresh, in a domain no example in `SKILL.md` or a supplement
  uses: if an example is about sizes, no case is. The judge is most confident on code
  that looks like an example in its prompt, so a case that copies one, even with new
  names or values, passes from memory and shows nothing about the convention.

For example, take a skill whose convention is "an error is handled or passed on, never
dropped", and whose only example of a violation is `except Exception: pass`. Its eval
has:

| Case | Outcome | What it shows |
|---|---|---|
| a payment retry logs the timeout and re-raises it | `valid` | the pair for the skill's example |
| a payment retry catches the timeout and does nothing | `invalid` | the pair for the skill's example |
| a parser returns `None` from its `except`, and its caller can't tell bad input from empty input | `invalid` | a violation the skill doesn't show |

The first two use a different domain and code from the skill's example; the third is a
way of dropping an error that the skill never mentions.

### A rule in several languages

The judge reviews each language with a different prompt: `SKILL.md` plus that language's
supplement. Test each language against its own prompt, and don't translate every case
into every language. In each language, with each case's `file` in that language, write:

- a `valid` and `invalid` pair for each example in the language's supplement;
- an `invalid` case that breaks the convention with a construct neither `SKILL.md` nor
  the supplement shows, chosen the same way: list the constructs both files show, and
  pick one that isn't on the list. `SKILL.md`'s `## Violation` section counts: a
  construct it names is shown. Don't translate another language's case for it: that
  case was chosen against another supplement;
- a case whose violation shows only with the code around the change, if the language has
  no change kinds (every language but Python, today). There the judge sees only the
  changed lines, so an edit inside a long function is judged without the function.

Write a case whose outcome doesn't depend on the language, such as values that match by
coincidence, in one language only. Before you copy a case into a second language, ask
whether its outcome could differ there; if it can't, the copy tests nothing new.

For example, extending the error-handling rule above to TypeScript, whose supplement
shows `.catch(() => {})` as a violation, adds TypeScript cases for:

- `.catch` that reports the error, and `.catch` that drops it: the pair for the
  supplement's example;
- a `try`/`catch` that returns an empty list on failure: a violation neither file shows.
  A `.then(onDone, () => {})` would not do: its empty handler is the supplement's
  example in another place;
- an edit that adds an empty `catch` inside an existing 40-line handler: a violation
  the judge must see without the rest of the handler.

It doesn't repeat the Python `except Exception: pass` pair, which is Python's example, or
a Python case that doesn't depend on the language.
