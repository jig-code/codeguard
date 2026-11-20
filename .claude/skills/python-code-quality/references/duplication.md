# Duplication, overlapping responsibility and re-implemented orchestration

One concept that should have one owner, copied at three scales: a function body, a
responsibility, or a whole pipeline.

## What `dry` already judges

The `dry` judge rule (`general` ruleset) reviews production `.py` files for code that
states a piece of knowledge a second time instead of using the place that already states
it: repeated steps under different names or argument orders, a process's stages run in
order outside the process, a collection that relists another set's members, and a second
type with the fields of one that already models the same outside thing. Read its text in
the pinned package and follow it; it isn't restated here.

Its binding excludes test files, and its severity is `warning`. Hold test code to the
same requirement: a test helper that repeats production's derivation, or a second fake
that repeats a shared one, is the same defect. `pytest-factoryboy` decides how tests reuse
builders and fakes.

## Overlapping responsibility

Two differently-named types that both answer "who owns X?" are one responsibility split
in two, even when their bodies don't match, so `dry`'s repeated-steps test doesn't catch
them. Examples: a `ModelResolver` beside `JudgeChoice.judge_model` that also decides a
provider and model from a binding and the project; two places that each decide whether a
diagnostic blocks.

Pick one owner, merge or delete the other, and repoint callers. This needs a comparison
across files: each type looks reasonable alone. Whenever a change adds a type whose name
is a role (`Resolver`, `Factory`, `Loader`, `Planner`), search for an existing type with
the same role and noun first.

### Not overlap: the same fields at two boundaries

Identical fields are a candidate, not a finding. Two shapes at different boundaries,
each changing for its own reason and mapped explicitly where they meet, are two owners
that share a shape today. `BindingConfig` is what a binding file says; `Binding` is what
the review runs with. They overlap in fields, change for different reasons (the file
format, the review's needs) and meet in `Binding.from_config`. Unifying them would couple
the file format to the review. Flag overlap only when you can name the one reason to
change both types share.

## Re-implemented orchestration

When one component runs a multi-step pipeline, a caller that needs that work calls the
component; it doesn't rebuild the pipeline. `dry` covers a caller that runs the same
stages in order. This section adds the cases where the caller rebuilds the pipeline's
inputs or wiring rather than its exact stages.

`Rules.review(scope)` loads the config, classifies the change, builds the bindings,
checks sign-ins and runs a `Reviewer` with the pattern and judge steps. A new entry point
(a CLI subcommand, an LLM test, an eval) that builds `Bindings.from_rulesets(...)` and a
`Reviewer(steps=...)` itself has copied that wiring. When `Rules.review` gains a step,
the copy silently lacks it.

The tell is visible without finding the owner: a body that calls two or more pipeline
collaborators in sequence, feeding one's output into the next (`classify` then `plan`,
`load` then `select`, `run` then `parse`). Two chained stage calls is enough to stop and
search for the owner.

Don't accept "there is no single method that does both": the owner may expose a request
object, a builder plus `run()`, or one method that hides the chain. Search for anything
that uses the same collaborators in the same order. If the owner's entry point is too
coarse for your case, add a narrow entry point on the owner (as `Rules.check_patterns`
runs only the pattern step), never a copy of its internals.

Test code follows the same rule: LLM tests review through `Rules.review`
(`test-quality` gate 7), and fixtures build objects through production's builders
(`pytest-factoryboy`).
