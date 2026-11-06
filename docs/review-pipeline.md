# The review pipeline

How a review picks its rules, calls the judge and reuses verdicts. [codeguard's
architecture](architecture.md) has the overview and the invariants this keeps;
[How a review works](how-a-review-works.md) is the same review from the user's side.

## Stages

The review pipeline runs in the Stop hook, in CI and in `codeguard review`:

1. Take the changeset.
2. Pick the candidate rules.
3. Pattern rules run. A file with a blocking pattern diagnostic skips the judge.
4. Classify (planned): a model call narrows the candidates.
5. The judge makes one call per rule and file ([The judge](judge-design.md)).
6. Verify (gated): a second model call confirms each violation.
7. The confidence threshold applies: a violation below 0.9 is reported as a warning,
   never dropped.

## Triggers and gates

Triggers and gates decide whether a judge rule runs on a change at all. A judge rule is
called only when the change touches one of its triggers. A trigger is a change kind
(`import`, `function-body`, …) or a gate. A gate is an ast-grep rule that matches where a
violation could appear. [The binding](rule-packages.md#the-binding) lists the change
kinds.

## Verdict cache

The verdict cache stores verdicts keyed on the template, model, skill, path, changed code
and whole file, so a verdict is reused until the changed code, the rest of the file, the
rule or the model changes. Verdicts are cached per provider and model, so switching
providers doesn't reuse another provider's verdicts; when no level names a model, the key
is `default` ([Judge input](judge-design.md#judge-input)).

When a provider exposes file-read tracking, a change to a file the judge loaded also
invalidates the verdict. A loaded file is one the judge read, or one its searches
returned: a file a grep matched or a glob listed. A file a search would only start
returning later doesn't count.

Evals and CI never use the cache.
