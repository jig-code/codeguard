# The review pipeline

**Triggers and gates** decide whether a judge rule runs on a change at all. A judge rule
is called only when the change touches one of its triggers. A trigger is a change kind
(`import`, `function-body`, …) or a gate. A gate is an ast-grep rule that matches where a
violation could appear.

**The review pipeline** is the same code on every surface (the Stop hook, CI and
`codeguard review`):

1. Take the changeset.
2. Bindings and triggers pick the candidate rules.
3. Pattern rules run. A file with a blocking pattern diagnostic skips the judge.
4. Classify (planned): a model drops the rules the change can't make fail.
5. The judge makes one call per rule and file, in parallel.
6. Verify (gated): a second model call confirms each violation.
7. The confidence threshold applies: a violation below 0.9 is reported as a warning,
   never dropped.
8. The results merge into one.

**The verdict cache** stores verdicts keyed on the template, model, skill, path, changed
code and whole file. When a provider exposes file-read tracking, recorded context-file
changes also invalidate the verdict. Evals and CI never use the cache.
