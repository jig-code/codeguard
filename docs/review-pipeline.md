**Triggers and gates** decide whether a judge rule runs on a change at all. A judge rule
is called only when the change touches one of its triggers. A trigger is a change kind
(`import`, `function-body`, …) or a gate. A gate is an ast-grep rule that matches where a
violation could appear.

**The review pipeline** runs in the Stop hook, in CI and in `codeguard review`:

1. Take the changeset.
2. Pick the candidate rules.
3. Pattern rules run. A file with a blocking pattern diagnostic skips the judge.
4. Classify (planned): a model call narrows the candidates.
5. The judge makes one call per rule and file.
6. Verify (gated): a second model call confirms each violation.
7. The confidence threshold applies: a violation below 0.9 is reported as a warning,
   never dropped.

**The verdict cache** stores verdicts keyed on the template, model, skill, path, changed
code and whole file. When a provider exposes file-read tracking, recorded context-file
changes also invalidate the verdict. Evals and CI never use the cache.

