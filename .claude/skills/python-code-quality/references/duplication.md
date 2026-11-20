# Duplication, overlapping responsibility and re-implemented orchestration

## What `dry` judges

The `dry` judge rule reviews production code for knowledge stated twice. Read its text in
the pinned rule package and follow it. Its binding leaves tests out; hold test code to
the same text, with `pytest-factoryboy` deciding how tests reuse builders and fakes.

## Overlapping responsibility

Two differently named types that both answer "who owns X?" are one responsibility split
in two, even when their bodies differ. Pick one owner, merge or delete the other, and
repoint callers. The defect shows only across files: when a change adds a type whose
name is a role (`Resolver`, `Factory`, `Loader`, `Planner`), search for an existing type
with the same role and noun first.

Shared fields alone aren't overlap. Two types at different boundaries that change for
different reasons and are mapped where they meet stay separate. Flag overlap only when
you can name the one reason to change both share.

## Re-implemented orchestration

When a component runs a multi-step pipeline, a caller that needs that work calls it,
rather than rebuilding the pipeline's inputs or wiring; a copy silently lacks every step
the pipeline gains later.

The tell, visible without finding the owner: two or more pipeline collaborators called
in sequence, one's output feeding the next. That is enough to stop and search for
anything that uses the same collaborators in the same order. Don't accept "no single
method does both": the owner may be a builder plus `run()`, a request object, or one
method hiding the chain. If its entry point is too coarse, add a narrow entry point on
the owner, never a copy of its internals.
