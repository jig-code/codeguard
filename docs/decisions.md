# Decisions

The standing choices about codeguard that govern future work and that the code and docs don't
show on their own. Each record states the decision as plain statements, and a Why when the
decision came with a reason. A decision that replaces an earlier one replaces the record. The
current design is in [architecture](architecture.md).

## 1. The architecture doc is the source of truth

- `docs/architecture.md` is the source of truth for codeguard's requirements and design.
- A requirement change is checked against it, and every doc that contradicts it is fixed in the same change.
- Code that differs from it is a conflict, not a new requirement.

## 2. codeguard builds its own review engine

- codeguard builds its own engine. It does not adopt an existing reviewer.

Why: none of the existing reviewers uses one convention source for both writing and review, and adopting one means conforming to its rule format.

## 3. codeguard is verified only by its own tests and evals

- codeguard is verified by its own tests and judge evals, never by a consuming repository.

## 4. A rule is declarative, not code

- A rule is a declarative rule in the target language's syntax, not a Python module.

Why: Python-module checks would make every rule Python parsing another language.

## 5. Dead code is found by the project's own lint task

- Code whose last use a change removes is deleted, and each language's own tool finds it.
- codeguard has no engine that wraps a linter and does not judge dead code.

Why: codeguard doesn't wrap linters the project runs.

## 6. A deterministic check comes before a judge rule

- A judge rule is never used when a deterministic check could decide the convention.
- Prefer an existing tool. When none supports it, a project script in CI beats a judge rule.
- A judge rule with a mechanical part is split, and the mechanical part becomes a pattern rule.

Why: a judge is less reliable and costs more.

## 7. codeguard's plugin ships its CLI

- The plugin ships the CLI, so installing the plugin is the only install step.
- codeguard is not installed with `uvx` from a git tag or from PyPI.

Why: requiring a separate install step as well as the plugin wasn't standard.

## 8. Dependencies are pinned to a minimum version only

- A dependency such as ast-grep is pinned to a minimum version with no ceiling.

Why: under 0.x a ceiling breaks every install at the next minor release.

## 9. codeguard has no sandbox support

- codeguard has no hook that builds it to run inside Claude Code's sandbox.

Why: it was only needed because of the old testing approach, and under the testing guide nothing needs codeguard to run inside the sandbox.

## 10. Evals run on pull requests, not on pushes to main

- Evals gate pull requests. They do not run again on pushes to main.

Why: re-running them after a merge spends model calls on what the pull request already judged.

## 11. An internal error never fails closed

- An internal error never blocks all work because something broke.

Why: a broken hook would stop all work.

## 12. A review's time limit is set in the config

- A review's time limit is set in `config.yaml`, not by an environment variable set from an action input and not by the workflow's `timeout-minutes`.

Why: a stuck `claude` call hung the CI review for 30 minutes and reported nothing, and the workflow's timeout can't read the config.

## 13. Low-confidence findings go to the user, not the agent

- Low-confidence findings go to the user through the Stop `systemMessage`. Stop `additionalContext` is not used.

Why: `additionalContext` continues the turn, so it would act as a block.

## 14. Concerns are never batched into one judge request

- Several concerns are never batched into one judge request.

Why: several concerns in one request hurt each rule's accuracy.

## 15. No orchestrating agent judges a review

- No orchestrating agent chooses what to spawn or load, and no reviewer subagent loads skills through the Skill tool.
- The `claude` provider never uses `--bare`.

Why: an orchestrating agent would choose what to spawn and load, and `--bare` needs `ANTHROPIC_API_KEY`.

## 16. Configuration is project scope, and only the judge's provider and model come from the environment

- One committed config file holds the configuration. There are no user or uncommitted scopes.
- Only the judge's provider and model come from the environment, and they override the file. Every other setting comes only from the committed config. Telemetry variables are also allowed.
- codeguard has no template language of its own and no shell-style fallback code in its config.

Why: user and uncommitted scopes never reach CI.

## 17. A rule package is pinned by its git ref

- A git package's `ref` pins the rules.
- There are no versioned packages, no lock, no `codeguard update` and no `--latest`.

Why: the range only chose a tag when someone ran `codeguard update`, which saves little for a project with one package it upgrades on purpose.

## 18. codeguard computes no cross-file context for the judge

- codeguard computes no cross-file context kinds. The judge reads other files itself.

Why: reading a named file is deterministic for a commit, and recording the files read keeps the cache correct.

## 19. The judge gets a standard unified diff

- The judge is sent the change as a git unified diff with function context, never an excerpt codeguard builds itself.

Why: a custom excerpt reinvents diffs, and function context appears with the change as it does in a GitHub review.

## 20. Changed lines come from a git library's diff

- Changed lines come from a git library's diff, not from parsing git's diff text.

Why: a git library numbers every diff line on both sides, includes untracked content and finds renames, so the hand-written parsing reinvented it.

## 21. A judged violation names a line range

- A violation names the start and end lines of the code that breaks the rule.
- A rule broken by code in two places reports the range of the copy the change added and names the other copy in its message. Only changed lines decide what a review keeps.

Why: architecture rules are often violated by more than one line.

## 22. Eval cases carry no expected reason

- Eval cases carry no expected reason, and no model call compares reasons. Evals check verdict and lines, and the report prints the judge's reason for every case.

Why: the judge's reason is context for a person troubleshooting, not a result to check.

## 23. Reading other code never lowers confidence

- Confidence is about how certain the verdict is after the judge has read whatever it needed, never about how much it read.

Why: without this, a judge that reads more reports less confidence in the same verdict.

## 24. The CLI judge omits the model when none is configured

- When no level names a model, the model flag is omitted, the CLI runs its own default, and the verdicts are keyed on the literal model `default`.
- codeguard never asks the CLI which model it runs, never reads its settings and never reads back which model ran.

Why: codeguard can't detect a change in the CLI's own default, so those verdicts get their own key.

## 25. The CLI judges locally and cloud providers judge in CI

- The `claude` CLI provider is for local work and runs from the hook in the user's session. CI never uses a subscription, so it never uses a CLI tool.
- Which judge runs is configuration, never code that knows the surface.
- One or two config values swap the judge provider for the entire system.
- The Claude Code CLI never runs against a live model in CI. Unit tests cover its call and its parsing.

Why: the goal of the project is to minimize the effort to switch between models.

## 26. A model is named once and its provider is never inferred

- A model is named once, by its vendor's id, and each provider maps that id to its own form.
- A model whose provider can't be told from configuration is a configuration error saying to set the provider. A provider is never inferred from a model name.
- A variable that apps use to drive codeguard is prefixed with `codeguard` and names no provider.

Why: a provider is a configuration detail that environment variables shouldn't leak.

## 27. codeguard owns the environment variables its judges use

- A cloud judge's location and sign-in come from environment variables codeguard names and reads, never from the provider's default variables.
- Every cloud judge is configured the same way.

Why: otherwise a user cannot specify what credentials codeguard gets versus direct use of the provider's own tools.

## 28. codeguard supports only the current Gemini model

- codeguard defaults to, documents and tests with one Gemini model, the one its rule bindings use.
- codeguard handles faults only for that model, never for older ones.

Why: the current model is more reliable and cheaper, and older ones need no support.

## 29. Gemini runs on Standard PayGo credits, 10 calls at once

- The default for Gemini calls at once is 10.
- Priority PayGo, a custom tier and Provisioned Throughput through sales are ruled out. Gemini stays only if Standard PayGo on credits gives acceptable throughput, and otherwise another provider is used.

Why: 10 keeps the peak inside the documented 500K tokens-per-minute tier, which matters on credits-only Standard PayGo.

## 30. A timed-out judge request is never re-sent

- A judge request that times out is not re-sent. 60 seconds is the high end for a request.
- A request over 60 seconds means something is wrong, not that the limit is too low.

Why: re-sending a timed-out request blocks CI for minutes waiting on a single test.

## 31. codeguard's own CI runs the judged review for real

- The job that reviews codeguard's pull requests runs judge rules. It has no `dry-run`.

Why: dogfooding means codeguard reviews its own changes against the rules it loads, exactly as it reviews any other project.

## 32. A rule can be CI-only through the main config

- A ruleset or rule has a CI-only option in the main config. There is no second full config and no local override file.

Why: copying a whole second config is the wrong approach, and a local override file suggests a local override that doesn't go in git.

## 33. One eval framework serves codeguard's judge evals and package evals

- codeguard's own judge evals and package evals share one framework. pydantic-evals runs inside codeguard only, with no custom evaluators from packages.

Why: codeguard stays language agnostic.

## 34. A judge rule is not a skill

- Rules and skills are different things, and a judge rule is not named like a skill.
- codeguard loads no language supplements, and the writing-rules skill drops them.
- Rule processing reads the old and new formats side by side during a format change. The writing-rules skill and the docs teach only the new format, and every new rule uses it.

Why: a supplement either restates the statement, carves out an exception, or is a second convention that belongs in its own rule with language-scoped binding paths.

## 35. codeguard corrects and never gates edits on a loaded skill

- codeguard corrects through deterministic checks and the judge, at Stop and in CI. It does not gate edits on a loaded skill.
- It does not enforce skill loading, and whether a skill loads is the skill evals' concern.
- Prevention, giving the writing agent the rules before it edits, is a future enhancement.

Why: enforcing a skill load needed the transcript, and hook inputs come only from documented host payloads.

## 36. A rule is its statement and its Why

- A rule is one statement and its Why, nothing else.
- A rule's statement is written out in full, with no relative pronoun dropped where a phrase could misparse and no pronoun whose noun isn't plain.

Why: the judge reads any other text as a test of its own.

## 37. Code may break any number of rules, and rules don't contradict

- Two rules may flag the same code. A new rule never contradicts another.
- codeguard doesn't validate contradictions between rules.

Why: codeguard cannot verify that a package's rules don't conflict with rules from other packages or the app being checked.

## 38. A convention that isn't codeguard's is declined without naming a tool

- When a convention is the kind typically given to a class of tool, such as a linter, type checker, import linter or language server, it is not codeguard's. The agent writes no rule and says it isn't codeguard's responsibility.
- Nothing in the skill, eval cases or graders names a specific tool, rule or setting.

Why: a reference to a specific tool breaks when a different, similar tool is chosen instead.

## 39. The writing-rules skill only writes the rule

- The skill's scope is writing the rule. Running tests or evals belongs to `docs/testing.md`, never to the skill.
- The skill holds no example rules and no examples. A miss is fixed by making the failing check check a single thing, stated clearly.

Why: the skill writes the rule and the evals verify the rule follows the skill, and nothing else is in scope.

## 40. Testing text lives in the testing docs

- Anything about testing codeguard, its rules or its skill goes in `docs/testing.md` or `docs/skill-evals.md`, never in the writing-rules skill.
- `docs/testing.md` is the one statement of how a change is tested. CLAUDE.md only points to it.

Why: one statement of testing policy means the docs can't drift apart.

## 41. An eval case has one clear answer

- A rule eval case is a test: unambiguously valid or invalid from its code alone. No borderline cases, in rule evals or skill evals.
- Evals are few, a handful of clear valid and invalid cases per rule and language, each testing something the others don't.
- A new case comes only from real data: a false block or a missed violation seen in use.
- An eval that fails after a change is a signal about the change first. An eval is deleted only when its requirement changed.

Why: a borderline case isn't what an eval is for, and a grader should never have to rule on a judgment call.

## 42. Skill evals grade the files the agent produced

- The writing-rules skill evals measure whether the rule the agent wrote complies with the skill. Whether the rule works is out of scope.
- Graders read the files the agent produced, never the conversation trace.
- Skill evals run only the with-skill arm.

Why: the CLI truncates the trace, so graders reading it judged from the agent's closing summary.

## 43. A grader checks only what its prompt asks for

- A grader checks only what the case's prompt asks for and the skill tells the agent to do. A grader on work the prompt doesn't name is a broken case, not a requirement on the skill.
- A grader states the check it makes, not a proxy for it.

Why: graders on work the prompts never asked for failed every run, and the skill was edited to satisfy them.

## 44. A fixed marker is a regex grader and prose is an llm grader

- A check of a fixed marker in a produced file is a `regex` grader whose pattern reads at a glance. A check that reads prose is an `llm` grader on short text.
- An `llm` grader checks one criterion, with one concrete PASS line and one concrete FAIL line that names the wrong output.

Why: a judge is most accurate when it judges one thing at a time.

## 45. A test states each expectation once

- A test states each expectation once, where its framework keeps it: a rule eval case in its expected outcome, a pattern or gate test case by its place in the valid or invalid list. A case's name or comment states only its situation.
- A name never states harm or why. The rule's Why holds that.

Why: a verdict repeated in names and comments has nothing checking that they agree.

## 46. Work touching pydantic-ai follows its documented practice

- Work that touches pydantic-ai follows the framework's current documented practice, checked against its documentation.

## 47. codeguard and codeguard-rules are two repositories pinned by commit

- codeguard and its rules package stay two repositories, and each pins the other by commit with no release tags while iterating.

Why: tags and per-PR merges made each engine change take several PRs and a release before the rules could use it.

## 48. A removed feature returns as its own feature

- Build the simplest thing first. A feature built and then removed returns as its own feature when it is needed.

## 49. Bindings route by `paths` until a binding needs a detector

- Routing by framework through `detects` (ast-grep framework detectors) is designed, not built, and `paths` stays required until a binding needs a detector.

## 50. codeguard runs claude through the Agent SDK

- codeguard runs `claude` through the Agent SDK instead of parsing `stream-json`.
- The Agent SDK only runs `claude`. Agent SDK tools and the Messages API stay rejected for searches.

Why: `stream-json` isn't documented as stable.

## 51. Duplicated skill-eval graders stay copies, checked in CI

- The writing-rules skill's eval cases keep their own copies of a duplicated grader, and a CI check fails when copies of one grader differ.
- Symlinks and a copy script are rejected.

Why: the eval tool has no shared graders, symlinks aren't documented and could silently skip, and a copy script goes stale.

## 52. codeguard keeps private rules for dogfooding

- codeguard ships no public rules, but it keeps private rules for dogfooding. The first is a rule that enforces the architecture's judge contract against the judge prompt.
- This bends the invariant that the framework has no rules built in. The exception is recorded as a decision when the work starts.

## 53. Docs and commits use a placeholder for the Google Cloud project

- Docs write `<project>` for the Google Cloud project, never a real key or the project number.
- The placeholder governs every new file, commit and PR text.

Why: the public testing guide must not list the project number.
