# Overlapping responsibility and re-implemented pipeline assembly

## Overlapping responsibility

Two differently named types that both answer "who owns X?" are one responsibility split
in two, even when their bodies differ. Pick one owner, merge or delete the other, and
repoint callers. The defect shows only across files: when a change adds a type whose
name is a role (`Resolver`, `Factory`, `Loader`, `Planner`), search for an existing type
with the same role and noun first.

## Re-implemented pipeline assembly

When a component assembles a pipeline (loads its configuration, builds its inputs,
chooses its steps), a caller that needs that work calls the component rather than
assembling the same inputs or steps itself; a copy silently lacks whatever the component
gains later. Don't accept "no single method does both": the owner may be a builder plus
`run()`, a request object, or one method hiding the assembly. If its entry point is too
coarse, add a narrow entry point on the owner, never a copy of its internals.
