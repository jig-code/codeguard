# Write rules

For whoever writes or changes a rule, in a project's `.codeguard/` or in a ruleset of a
[rule package](rule-packages.md).

Use the plugin's [writing-rules skill](../skills/writing-rules/SKILL.md): ask the agent
for the rule, and the skill decides which kind of rule fits the convention, states it
and writes its files. [Rule formats](rule-formats.md) has the format of each file.

## Where rules live

A project's own rules live in `.codeguard/` and run with no config. A package keeps
the same layout in each of its ruleset directories:

```
.codeguard/
  config.yaml                # the project's settings; not in a package's rulesets
  rules/pattern/<id>.yml     # pattern rules
  gates/<id>.yml             # pattern rules that gate judge rules
  rule-tests/<id>-test.yml   # tests for both, with __snapshots__/
  skills/<id>/SKILL.md       # judge rules: the rule the judge checks
  bindings/<id>.yaml         # a rule's paths; a judge rule's triggers and model
  rule-evals/<id>.yaml       # rule evals: edits and the review each should get
```

A binding or rule eval may end in `.yaml` or `.yml`. Pattern rule tests in
`rule-tests/pattern/`, the old layout, still run. codeguard rejects anything else, so a
rule moves between a project and a package unchanged.

## Why a rule exists

Every rule says why it exists. `codeguard test` reports each rule without a why
([`--missing-why`](cli.md#test)).

## The judge's model

The rule eval is what makes a judge rule trustworthy. It shows the rule flags the edits
it should and passes the ones it should, on the model that will judge it in reviews: the
binding's ([Choose a judge](judges.md)). To move a rule to another model, change its
binding and pass its rule eval again.

`codeguard eval` judges with the binding's model too, unless `--provider` names another.
That is for rules whose bar is passing on more than one model, such as a CI job per
provider; it changes nothing a review judges with.

## Test a rule

1. `codeguard test` checks pattern rules and gates against their tests, and judge rules'
   triggers on their eval cases, with no model call. A pattern rule needs only this.
2. For a judge rule, `codeguard eval` reviews every case once with the binding's model, the way
   `codeguard review` would, to verify the change.
3. Once it passes, `codeguard eval --repeat 2` reviews each case twice more, so an
   unstable verdict shows up as a failing run, named like
   `a second class added to the file [2/2]`. A case passes when it gets its expected
   review on all 3 runs.

`codeguard eval -h` lists its options for judging some of the rules, or with another
model ([CLI](cli.md#eval)). [What makes a case fail](rule-formats.md#what-makes-a-case-fail)
lists each command's failures.

An eval tests the rule, not the code, so every run calls the model. With a Logfire token
each rule's run is also in Logfire, as an experiment named `<rule> on <model>`, so runs
of the same rule compare ([Telemetry](telemetry.md)).

Run both in the project root for `.codeguard/`, or in a package's root for every
ruleset. [Testing](testing.md#changing-a-rule-package) says which test each change needs.
