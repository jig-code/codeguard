# Decisions

The decisions that shape codeguard and still hold. Each record states the decision as plain
statements, and a Why when the decision came with a reason. A decision that replaces an
earlier one replaces the record. The current design is in [architecture](architecture.md).

## 1. codeguard is built as the framework's first wired surface

- The PR and CI review surface is built in codeguard, with otter as its first consumer.
- codeguard is not an otter-local reviewer migrated later.

Why: building it here forced the content extraction and the canonical model the framework needs anyway.

## 2. codeguard is renamed jig as v1.0.0

- The project is renamed jig, under the `jig-code` GitHub org, with no fallback to the old names.
- The rules package keeps the name `codeguard` until the rename and takes the name `jig` after it.

Why: "guard" read as security and undersold a tool that guides the agent before an edit as well as checking the change.

## 3. codeguard is Python, managed with uv

- The engine is written in Python and managed with uv.

## 4. The architecture doc is the source of truth

- `docs/architecture.md` is the source of truth for codeguard's requirements and design.
- A requirement change is checked against it, and every doc that contradicts it is fixed in the same change.
- Code that differs from it is a conflict, not a new requirement.

## 5. codeguard builds its own engine and adopts ast-grep, Logfire and the host hook systems

- codeguard builds its own engine. It adopts ast-grep, Logfire and the host hook systems.
- It does not adopt Continue, CodeRabbit, Bugbot, Anthropic's `code-review` plugin or another existing reviewer.

Why: none of them uses one convention source for both writing and review, and adopting one means conforming to its rule format.

## 6. An existing tool or library is used, never rebuilt

- Before building something, check what the adopted library or tool already supports.
- Do not rebuild what it already does.

Why: Craig, "there should be a decision that we don't reinvent things."

## 7. codeguard is verified only by its own tests and evals

- codeguard is verified by its own tests and judge evals, never by a consumer repository such as otter.

## 8. Checks run through a check-engine plugin interface, with ast-grep first

- A check engine takes a file and rules in and gives diagnostics out. ast-grep is the first engine and Semgrep can follow for dataflow rules.
- A rule is a YAML rule in the target language's syntax, not Python code.

Why: Python-module checks would make every rule Python parsing another language.

## 9. Dead code is found by the project's own lint task

- Code whose last use a change removes is deleted, and each language's own tool finds it.
- The tool runs in the project's lint task. codeguard has no engine that wraps a linter and does not judge dead code.

Why: codeguard doesn't wrap linters the project runs.

## 10. A deterministic check comes before a judge rule

- A judge rule is never used when a deterministic check could decide the convention.
- Prefer an existing tool. When none supports it, a project script in CI beats a judge rule.
- A judge rule with a mechanical part is split, and the mechanical part becomes a pattern rule.

Why: a judge is less reliable and costs more.

## 11. A rule's scope is set by its binding

- A binding's `paths` and `exclude_paths` choose where a rule runs, and a project can override them per binding.
- A pattern rule may set ast-grep `files` and `ignores` when the file name is part of the convention.
- A ruleset has a severity, so a project can trial a package as warnings.

Why: a glob `paths` can't say "every Python file but tests", and a package can't know a project's source folders.

## 12. codeguard is a host plugin that ships its CLI

- One repository holds `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`, and each plugin's hooks call the same engine.
- The plugin ships the CLI: `bin/codeguard` runs through `uv run` in `$CLAUDE_PLUGIN_DATA`.
- codeguard is not installed with `uvx` from a git tag or from PyPI.

Why: requiring a separate install step as well as the plugin wasn't standard.

## 13. ast-grep is a package dependency with a minimum version only

- ast-grep is a dependency of the package, pinned to a minimum version with no ceiling.

Why: under 0.x a ceiling breaks every install at the next minor release.

## 14. codeguard has no sandbox support

- codeguard has no SessionStart hook that builds it to run inside Claude Code's sandbox.

Why: it was only needed because of the old testing approach, and under the testing guide nothing needs codeguard to run inside the sandbox.

## 15. Evals run on pull requests, not on pushes to main

- Evals gate pull requests. They do not run again on pushes to main in the `jig-code` repositories.

Why: re-running them after a merge spends model calls on what the pull request already judged.

## 16. An internal error fails loud

- An internal error shows a visible message and records an error span. It does not fail closed.
- A failed judge call takes the rule's severity: a `warning` rule can't block when it runs, so it doesn't block when it fails.
- Locally, judge errors go to the developer and never to the agent, and a failed judge call never blocks the agent's stop. Rule errors still block every stop until fixed.
- In CI a judge error fails the review unless the per-PR label sets `--judge-errors-as-warnings`.

Why: the agent can't fix a judge error, and a per-PR label shows each bypass in the PR's history.

## 17. A review has a time limit

- A review's time limit defaults to 5 minutes in `config.yaml`, and CI's hard limit is that plus 2 minutes.
- The limit is not an environment variable set by an action input and not the workflow's `timeout-minutes`.

Why: a stuck `claude` call hung the CI review for 30 minutes and reported nothing.

## 18. Verdicts are cached per rule and file

- A verdict is cached under a key of rule and file path.
- The cache fingerprint covers codeguard's own judging inputs, so a template or schema change re-judges everything with no manual versioning.
- Evals never use the verdict cache, and `--repeat` is the number of independent runs.

Why: an eval tests the rule, not the code.

## 19. Only high-confidence violations block

- A high-confidence violation blocks. A low-confidence one is reported.
- Low-confidence findings go to the user, not the agent, through the Stop `systemMessage`. Stop `additionalContext` is not used.

Why: `additionalContext` continues the turn, so it would act as a block.

## 20. A change is classified by one model step that only removes candidates

- Change classification may remove a candidate rule only when it decides the change cannot make it fail.
- It never adds a rule.

## 21. Each rule is judged in its own request

- Each concern is one judge request, run in parallel. Several concerns are never batched into one request.

Why: several concerns in one request hurt each rule's accuracy.

## 22. The judge is a provider interface with no orchestrating agent

- A judge provider takes a request and returns a verdict and usage. The request and verdict schema do not depend on the provider.
- Claude runs through `claude --safe-mode -p` and Codex through `codex exec --output-schema`.
- `--bare` is not used.
- No orchestrating agent chooses what to spawn or load, and no reviewer subagent loads skills through the Skill tool.

Why: `--bare` needs `ANTHROPIC_API_KEY`, and an orchestrating agent would choose what to spawn and load.

## 23. Configuration is project scope, and only the judge's provider and model come from the environment

- One committed `config.yaml` at fixed `.codeguard/` paths holds the configuration. There are no user or uncommitted scopes.
- Only `judge.provider` and `judge.model` come from the environment, as `CODEGUARD_JUDGE__PROVIDER` and `CODEGUARD_JUDGE__MODEL`. They override the YAML file, and an unset variable leaves the file's value. Telemetry variables are also allowed.
- Every other setting comes only from the committed config.
- The project config is a pydantic-settings model. codeguard has no template language of its own and no shell-style fallback code.
- This covers codeguard reviewing a project in CI, including codeguard reviewing itself. It does not cover the pytest LLM tests or the skill evals.

Why: user and uncommitted scopes never reach CI.

## 24. A rule package is pinned by its git ref

- A git package's `ref` pins the rules, in one file.
- There are no versioned packages, no lock, no `codeguard update` and no `--latest`.

Why: the range only chose a tag when someone ran `codeguard update`, which saves little for a project with one package it upgrades on purpose.

## 25. Stop reviews uncommitted and untracked files

- The Stop hook reviews the uncommitted and untracked files of the `cwd` checkout.

Why: that is the common practice.

## 26. The judge reads other files itself with tools

- The judge reads other files with `Read`, `Grep` and `Glob`. codeguard computes no cross-file context kinds.
- The judge's reads are recorded, so the verdict cache stays correct.

Why: reading a named file is deterministic for a commit, and recording the files read keeps the cache correct.

## 27. The judge prompt embeds only what the judge will certainly have to read

- The prompt embeds what the judge will certainly have to read and nothing it only might need. The judge reads the rest when the convention needs more.
- The prompt describes the context and the tools. It never directs which files the judge reads.

Why: deferring a required read to a tool call isn't cheaper, because the judge reads the same lines and adds a turn.

## 28. The judge gets a unified diff with function context

- The judge is sent the change as a git unified diff with function context, in place of codeguard's own excerpt. Hunk headers mark every gap.
- Triggers still decide which files are judged.
- Every judged change is sent with the smallest enclosing function or class for each changed line, found with ast-grep through the syntax tables.
- A language is supported by its syntax table. The extension point for others is a syntax table plus, where ast-grep has no built-in grammar, its custom-language support.
- codeguard's judge evals check that the judge still reports the right line numbers.

Why: Craig, "it feels like we are reinventing diffs again", and the context appears with the change as it does in a GitHub review.

## 29. Changed lines come from a git library's diff

- Changed lines come from a libgit2 binding's diff, not from parsing git's diff text.
- A scope protocol replaces the two-type union, and classifier results are separate from the changed-lines type.
- `codeguard/repository/` holds git, working_tree, unified_diff and line_scope, and exports WorkingTree, LineScopes and the scope types. An import contract keeps git and unified_diff private to it. line_range and file_lock stay top-level.

Why: a git library numbers every diff line on both sides, includes untracked content and finds renames, so the hand-written parsing reinvented it.

## 30. A judged violation names a line range

- A violation names the start and end lines of the code that breaks the rule, as one `LineRange` value with `start` and `end`. The value checks that `end` is not before `start` and whether a changed line falls inside it.
- A review keeps a judged violation when a changed line or a deletion point is among its lines, as it keeps a pattern rule's range.
- A rule broken by code in two places reports the range of the copy the change added and names the other copy in its message. Only changed lines decide what a review keeps.

Why: architecture rules are often violated by more than one line.

## 31. A review reports a violation when the changed code is part of it

- A violation is reported when the changed code is part of it, whether or not the base had it. Scope goes up, never sideways: the other blocks of a statement are siblings.
- Removed lines are shown to the judge as `-` and count as part of a violation.
- The module is not an enclosing node.
- Blank lines are never changed lines, in any language. A blank line added inside a multi-line string, YAML block scalar or Markdown also counts as no change.

Why: reporting only what the base passed left an edited line that already broke a rule unreported.

## 32. Triggers and gates decide which rules judge a change

- A binding's triggers say which changes trigger a rule, and `triggers` defaults to `[any]`.
- A gate is a pattern rule that asks what code a violation needs.
- `codeguard eval` runs no model review of a rule's own skill and gate agreement. Its deterministic checks stay.

Why: change kinds asked which edits could break a rule, and nearly every edit touches a body, so a 3-line `__init__.py` still ran 25 rules.

## 33. A gate matches the code a violation needs and nothing around it

- A gate matches the code a violation needs, not the statement, block or function that holds that code.
- The writing-rules skill states this as a general rule with no example.

## 34. The judge reports violations only

- The judge reports violations and never proposes fixes. A pattern rule keeps its note, which its author wrote.
- The judge gives a reason for every verdict, pass or fail. The reason is for a person troubleshooting and to fix a rule's wording when the why is wrong.
- Eval cases carry no expected reason and no model call compares reasons. Evals check verdict and lines, and the report prints the judge's reason for every case.

Why: the judge's fix notes were flagged by the next pass and stalled the rule fixes.

## 35. Confidence is a fixed scale

- The judge's confidence is one of CERTAIN 1.0, HIGHLY_PROBABLE 0.9, PROBABLE 0.7 and POSSIBLE 0.5, documented on the enum's values, one schema for every provider and the cache.
- A verdict, violation or no violation, is the result. Confidence is the judge's assessment of how accurate that result is, and the threshold is a separate blocking policy.
- Confidence is about how certain the verdict is after the judge has read whatever it needed, never about how much it read. Reading other code never lowers it.

Why: without anchors, scores sat at 0.80 to 0.88 and invalid cases failed the 0.9 threshold.

## 36. The judge's provider and model resolve separately

- A binding's provider or model wins over the project default, and the project default wins over the rule package default. The provider and the model each take the first level that names them.
- A binding that names only a model runs on the provider CI sets.
- When no level names a judge, the built-in default is the `claude` CLI.

Why: a model-only binding can't then force a CLI judge into CI.

## 37. The CLI judge omits the model when none is configured

- A configured model, from a binding, the project or the package, is passed to the CLI as `--model` and keys the verdicts.
- When no level names a model, the flag is omitted, the CLI runs its own default, and the verdicts are keyed on the literal model `default`.
- codeguard never asks the CLI which model it runs, never reads its settings and never reads back which model ran.
- A user who changes the CLI's default clears the cache themselves.

Why: Craig, "if the user changes the default we can't rely on that breaking our cache."

## 38. The CLI judges locally and cloud providers judge in CI

- The `claude` CLI provider is for local work and runs from the hook in the user's session. CI never uses a subscription, so it never uses a CLI tool. It uses Gemini or Bedrock.
- Which judge runs is configuration, never code that knows the surface.
- One or two config values swap the judge provider for the entire system.
- The Claude Code CLI never runs against a live model in CI. Unit tests cover its call and its parsing.

Why: the goal of the project is to minimize the effort to switch between models.

## 39. A model is named once and each provider maps it

- A model is named once, by its vendor's id, and each provider maps that id to its own form. Bedrock maps it to its inference-profile id.
- `judge.model` also takes the provider's own id, such as a Bedrock application profile ARN, passed through as Claude Code's `--model` does.
- For an application profile ARN, the Bedrock provider reads the profile's `ModelId` tag once per profile per process. A missing tag is an error.
- A model whose provider can't be told from configuration is a configuration error saying to set the provider. A provider is never inferred from a model name.
- A variable that apps use to drive codeguard is prefixed with `codeguard` and names no provider.

Why: Craig, "bedrock is a configuration provider. env vars for codeguard shouldn't be leaking that detail."

## 40. codeguard owns the environment variables its judges use

- A cloud judge's location and sign-in come from environment variables codeguard names and reads, never from the provider's default variables.
- Every cloud judge is configured the same way.

Why: otherwise a user cannot specify what credentials codeguard gets versus direct use of the provider's own tools.

## 42. codeguard uses one Gemini model and supports only the current one

- codeguard defaults to, documents and tests with one Gemini model, the one its rule bindings use, currently `gemini-4-argon`.
- codeguard handles faults only for that model, never for older ones.

Why: Craig, "argon 4 is more reliable and cheaper than 3.1 pro", and "we don't need to support older models".

## 43. Gemini runs 10 calls at once, on Standard PayGo credits

- Gemini calls at once is 10.
- Priority PayGo and a custom tier or Provisioned Throughput through sales are ruled out. Gemini stays only if Standard PayGo on credits gives acceptable throughput.

Why: 10 keeps the peak inside the documented 500K tokens-per-minute tier, and "if we can't leverage the solution with credits, we'll use another provider."

## 44. A timed-out judge request is never re-sent

- A judge request that times out is not re-sent. 60 seconds is the high end for a request.
- A request over 60 seconds means something is wrong, not that the limit is too low.

Why: Craig, "i don't want to block CI for 10 minutes waiting for a test to pass."

## 45. CI signs in to Gemini with the existing secret and variable

- CI signs in to Gemini with the `GOOGLE_CREDENTIALS` secret and the `GOOGLE_CLOUD_PROJECT` variable, as codeguard-rules' CI does.

Why: Craig, "one of these repos was already running gemini in a CI matrix and I didn't do this."

## 46. codeguard's own CI runs the judged review for real

- The job that reviews codeguard's pull requests has no `dry-run`, and it has the Gemini credentials the LLM tests use.
- For a binding that names no provider, the judge is the rules package's default, Haiku 5.5 on Bedrock.
- Dogfooding means codeguard reviews its own changes against the rules it loads, exactly as for otter.

Why: Craig, "CI should run the judged review for real."

## 47. A rule can be CI-only through the main config

- A ruleset or rule has a CI-only option in the main config. There is no second full config and no local override file.

Why: Craig, "if a rule should be CI only, that should be an option in the main config file."

## 48. A project opts into rulesets with a list of names

- A package entry's `rulesets` takes a list of names, such as `rulesets: [general, python]`, each running every rule.
- A mapping form stays for a ruleset with `include`, `exclude`, `severity`, `ci_only` or `rules.<id>` overrides.
- `include` lists the only rules that run and can't be combined with `exclude`. `include: []` runs nothing.

Why: Craig, "I would expect an empty set to include nothing, not everything."

## 53. One eval framework serves codeguard's judge evals and package evals

- codeguard's own judge evals and package evals share one framework. pydantic-evals runs inside codeguard only, with no custom evaluators from packages, so codeguard stays language agnostic.
- The eval file format is codeguard's own YAML, and results go to stdout.
- A test names a model only when the model is what it checks.
- Rule evals and bindings may end in `.yml` or `.yaml`, and having both for one rule is an error.

## 54. Two test kinds cover rules

- Pattern and gate tests share one format and runner.
- A trigger test is a `skipped` rule eval case.

## 55. A judge rule is a plain file named as a rule, not a skill

- A judge rule is one plain Markdown file at `rules/judge/<id>.md`: a title, one statement sentence and `## Why`. Every binding names it with `rule: <id>`, and its text goes to the judge unparsed.
- Rules and skills are different things, and a judge rule is not named like a skill.
- codeguard loads no language supplements, and the writing-rules skill drops them.
- The format check ships in the same PR that moves the writing-rules skill to the new format, and the skill tells the author to run `codeguard test` on the rule it wrote.
- Rule processing reads the old and new formats side by side during a format change. The writing-rules skill and the docs teach only the new format, and every new rule uses it.

Why: a supplement either restates the statement, carves out an exception, or is a second convention that belongs in its own rule with language-scoped binding paths.

## 56. codeguard corrects and never gates edits on a loaded skill

- codeguard corrects through deterministic checks and the judge, at Stop and in CI. It does not gate edits on a loaded skill.
- It does not enforce skill loading, and whether a skill loads is the skill evals' concern.
- Rule-only conventions reach the agent only as a check failure, the standard linter loop.
- Prevention, giving the writing agent the rules before it edits, is a future enhancement, and the architecture says so instead of claiming it.

Why: enforcing a skill load needed the transcript, and hook inputs come only from documented host payloads.

## 57. A rule is its statement and its Why

- A rule is one statement and its Why, nothing else.
- A rule's statement is written out in full, with no relative pronoun dropped where a phrase could misparse and no pronoun whose noun isn't plain. The skill checks this and a skill-eval grader checks it.

Why: the judge reads any other text as a test of its own.

## 58. A rule names a class only when it is about that class

- A rule names a specific class, function or file only when its convention is about that one. A rule meant for many matches what they share.

Why: Craig, "a rule that is meant to apply to multiple scenarios should not use a single class, but a rule that is meant for a single class is ok to use that class."

## 59. Code may break any number of rules, and rules don't contradict

- Two rules may flag the same code. A new rule never contradicts another.
- codeguard doesn't validate contradictions between rules.

Why: Craig, "there is no limit to how many rules code can break, but rules cannot contradict each other."

## 60. A convention that isn't codeguard's is declined without naming a tool

- When a convention is the kind typically given to a class of tool, such as a linter, type checker, import linter or language server, it is not codeguard's. The agent writes no rule and says it isn't codeguard's responsibility.
- The skill describes tools by class, with no table of tools. Nothing names a tool, rule or setting: not the skill, eval cases, graders or PR text.
- Eval fixtures configure no third-party tool.

Why: Craig, "if specific tools are used or referenced, that is going to break if a different, similar tool is chosen instead."

## 61. The writing-rules skill only writes the rule

- The skill's scope is writing the rule: the kind, the convention and why, the gate and the cases. Running tests or evals belongs to `docs/testing.md`, never to the skill.
- The skill keeps gating as a step of writing a judge rule, without the mechanics: the binding's triggers decide which changed code the judge sees.
- The skill restricts no trigger value. Which values warn is `codeguard test`'s business.
- The skill holds no example rules and no examples. A miss is fixed by making the failing check check a single thing, stated clearly.

Why: Craig, "The skill writes the rule, the evals verify that a rule was written that follows the instructions of the skill and that is it."

## 62. Skills follow Anthropic's skill guidance

- A skill has a short `SKILL.md`, detail in linked files inside the skill folder, and only what Claude doesn't already know. It says what it does, not what it doesn't.
- A skill holds no history. It can state the why, which is the impact.
- A rule is absolute with no exception, or it is written as a conditional ("use X unless Y").
- The test-quality and pytest-factoryboy skills are codeguard's test governance. They live in `.claude/skills/`, not `skills/`, which ships in the plugin.

Why: Craig, "skills don't include history. they can include 'why' to follow them, but that is the impact, not a history lesson."

## 63. Testing text lives in the testing docs

- Anything about testing codeguard, its rules or its skill goes in `docs/testing.md` or `docs/skill-evals.md`, never in the writing-rules skill.
- `docs/testing.md` is the one statement of how codeguard, a rule package and an app test a change. CLAUDE.md only points to it, and each row lists every check a change needs.
- A codeguard pytest judge fixture that tests review scope may hold a pre-existing violation of the rule under test, on lines the change leaves untouched.

Why: the text is about testing, and keeping testing policy in one doc means the two can't drift.

## 64. One pass verifies a change and the rest of N proves it stable

- Every live-model check runs once to verify a change. Once that passes with nothing changed since, the stability check runs N-1 more. Any change restarts at one pass.
- Each live-model CI check is two jobs. The validity job runs one pass and fails fast. The reliability job starts only when it passes, runs N-1, never fails fast, reports every case's pass rate and gates on N of N.
- Locally the one pass may stop at the first failure, and the N-1 run always completes.

Why: Craig, "one pass to verify a change, multiple passes to verify its stable. That needs to be applied everywhere."

## 65. Every eval case's bar is 3 of 3

- Every eval case passes 3 runs of 3: judge rule evals, the judge's LLM tests and the skill evals. That is 1 run to verify the change, then 2 more.
- A doc's command runs one eval to verify the change, then `--repeat 2`. A doc never gives `--repeat 3`. "3 runs of 3" names only the bar.

Why: Craig, "we are only going to use 3/3 for all cases."

## 66. Tests pass locally before any push

- Before any push to GitHub, the tests the change affects run locally and pass: pytest and the offline checks for code, `codeguard rules test` and `codeguard rules eval` for rules, and the skill evals for a skill or eval change. CI confirms; it doesn't find failures.
- A push to a new `backup/` branch with no pull request is exempt.

Why: Craig, "run tests locally instead of burning github action minutes on every change."

## 67. An eval case has one clear answer

- A rule eval case is a test: unambiguously valid or invalid from its code alone. No borderline cases, in rule evals or skill evals.
- Evals are few, a handful of clear valid and invalid cases per rule and language, each testing something the others don't.
- A new case comes only from real data: a false block or a missed violation seen in use.
- When a case is ambiguous, the requirement it quietly tests goes into the rule as a clause, with cases for that clause.
- An eval that fails after a change is a signal about the change first. An eval is deleted only when its requirement changed.

Why: Craig, "Evals should not have borderline cases. That is not the purpose of evals."

## 68. Skill evals grade the files the agent produced

- The writing-rules skill evals measure whether the rule the agent wrote complies with the skill. Whether the rule works is out of scope.
- Graders read the files the agent produced, never the conversation trace. The eval doesn't grant Bash.
- Skill evals run only the with-skill arm, with `--ablation none`.
- The agent runs on Opus and the graders on Haiku, each set by its own required repository variable with no fallback.

Why: the graders were reading the trace, which the CLI truncates, so they judged from the agent's closing summary.

## 69. A grader checks only what its prompt asks for

- A grader checks only what the case's prompt asks for and the skill tells the agent to do. A grader on work the prompt doesn't name is a broken case, not a requirement on the skill.
- A grader states the check it makes, not a proxy for it. One idea has one term.

Why: two cases carried graders the prompts never asked for, and the skill was edited to satisfy them.

## 70. A fixed marker is a regex grader and prose is an llm grader

- A check of a fixed marker in a produced file is a `regex` grader whose pattern reads at a glance. A check that reads prose is an `llm` grader on short text. No pytest step runs over eval output.
- An `llm` grader checks one criterion, with one concrete PASS line and one concrete FAIL line that names the wrong output. It states the convention and any limit the docs set on what it checks, and never refers to the prompt or the docs.
- Skill-eval graders and prompts are written in short, plain sentences, one check per sentence.

Why: Craig, "ask a judge to judge one thing at a time to get the best accuracy."

## 71. Test and eval names state the situation

- A pytest test is named `test_<situation>_<result>`.
- A skill eval case is named `<expected outcome>-<subject>`, the outcome being `writes-rule`, `changes-rule` or `declines`. A grader is named `NN-<what the agent's output does>`.
- A name never states harm or why. The rule's Why holds that.
- A test states each expectation once, where its framework keeps it: a rule eval case in its expected outcome, a pattern or gate test case by its place in the valid or invalid list. A case's name or comment states only its situation.
- codeguard's own tests build their eval cases inline, and a table of inputs and results is one parametrized test.

Why: Craig, "These are tests aren't they? Name them like tests."

## 72. Tests are deterministic

- A test's result never depends on the machine, clock or environment it runs on.
- A test fixes such an input to a value it chooses, distinct from every other value the code could return.
- Live-model evals are measured by repeated runs and aren't covered here.

Why: Craig, "if this ran on a machine with 2 cpus and it took the gemini path it would incorrectly pass."

## 73. A test targets the type that owns the behaviour

- Each test targets the type that owns the behaviour it checks, through that type's own interface. A test of an orchestrator checks only the orchestration.
- Code that a test writes across several lines is an indented triple-quoted block in the test body, not one string with escaped newlines. A test about the escape characters themselves keeps them.

Why: escaped `\n` strings packing several lines are hard to read.

## 74. Code comments say why

- A comment is minimal and explains why. It never explains how a host or the code works.
- A comment or docstring stays only when it states what the code can't and is unlikely to drift.
- A comment that narrates the code is deleted. One that makes up for a name or design is replaced by a better name or design.

Why: Craig, "comments are not a substitute for documentation or poor design."

## 75. Work touching pydantic-ai follows its documented practice

- Work that touches pydantic-ai follows the framework's current documented practice, checked through the Context7 connector.

## 76. Docs are an entry point plus one page per reader

- `README.md` is the entry point: what codeguard is, why, a short quick start and links. Everything else lives in `docs/`, one page per audience and type.
- A page says only what code, config files and workflows can't, and each fact has one page.
- Design docs explain why. How-to pages cover the public interface only, never how the internals work.
- Docs hold guidance. History lives elsewhere and is linked.

Why: Craig, "a lot of information ... and not for a single audience. that makes it hard to discover the information the person is looking for."

## 77. Docs don't restate what lives elsewhere

- Docs don't describe codeguard's own workflows. A reader who needs CI's mechanics reads `.github/workflows/`.
- Docs don't explain how a dependency or host works, such as GitHub Actions, Claude Code, Codex, `claude plugin eval`, ast-grep or a provider's SDK. They say what codeguard needs from it and link the vendor's page.
- Docs name a variable and what it sets, never a value set outside the repository.
- `docs/architecture.md` states each invariant once, in Invariants, and the other sections restate none.

Why: Craig, "Redundant docs are a drift risk and not helpful."

## 78. No betterwithranch references remain

- Docs and config point at `jig-code/codeguard-rules`. No reference to `betterwithranch` remains.
- The rules package's `name` is `codeguard`, so rule ids read `codeguard/<ruleset>/<id>`.

Why: Craig, "there shouldn't be any references to betterwithranch remaining."

## 79. codeguard and codeguard-rules are two repositories pinned by commit

- codeguard and codeguard-rules stay two repositories, and each pins the other by commit with no release tags while iterating.
- Usability is measured by codeguard reviewing its own pull requests in CI with the rules it loads. otter is outside the development loop and updates periodically, when codeguard is stable.

Why: tags and per-PR merges made each engine change take several PRs and a release before the rules could use it.

## 80. Every change reaches main through a pull request

- Every change reaches main through a pull request with green CI. There are no direct pushes or merges to main.
- Craig reviews and merges a pull request once its CI is green.
- A pushed PR branch takes main by merging main into it, never by rebasing, so every push is a plain fast-forward and never a force-push.

Why: trunk-based work needs one integration point.

## 81. Each PR passes CI on its own

- A PR merges only with its own CI green. A failure it shows is fixed in that PR, or the case is skipped there, naming the PR that restores it.
- A later PR is never counted on to turn an earlier one green.
- A codeguard change to the rule package format keeps reading the old format alongside the new until codeguard-rules has moved. A later codeguard PR then drops the old format. Only rule processing reads both.

Why: Craig, "the red case should be fixed in 45 or skipped pending 55."

## 82. A PR description follows the template

- A PR description follows `.github/pull_request_template.md` and describes the change as it stands.
- It states the final head's results against the bar and nothing else. It leaves out commit lists, extraction or porting history and the checks CI already shows.

Why: Craig, "that's not what a PR description is supposed to do."

## 83. A doc edit ships with the change it describes

- A doc edit goes in the PR whose change it describes, not in a docs-only PR. A feature's docs are written first on the feature's branch as its spec, its code follows, and they ship together in one PR.

Why: Craig, "we don't need docs only PRs for simple doc edits."

## 84. A rename that comes with edits is its own PR

- A file that is renamed or moved and also edited goes in its own rename-only PR that merges first. The edits follow in a later PR.
- A change split from an open PR for scope goes in a new PR from main that merges first, and the open PRs then merge main and follow it. An open PR isn't merged with code a later PR is planned to fix.

Why: Craig, "delete and add does not capture the history cleanly."

## 86. A PR doesn't fix violations already on main

- A PR fixes what it adds or changes, not violations already on main, even in a file it touches. Reviews flag only the PR's own lines.
- Older code that predates a standard is brought in line in its own PR.

Why: Craig, "we don't need to change existing violations."

## 87. codeguard's workflows follow GitHub's secure-use practices

- A workflow uses least-privilege permissions, job timeouts and no persisted checkout credentials, and pins the version of Claude Code it runs.
- Steps shared by the validity and reliability jobs are a local composite action, not a reusable workflow, because the Bedrock role trusts only the named workflow files.
- Skill-eval results go through the documented `--output-dir`. A job has a cost ceiling.

Why: Craig, "make sure that we are also using github workflow best practices."

## 88. The CLI has `test` and `eval` under `codeguard rules`

- `codeguard rules test` and `codeguard rules eval` are the subcommands, with no old top-level aliases.

## 89. Variable names say what uses them and how

- A CI variable's name says what uses it and what its value is used as. A variable that feeds a flag taking a model id or a profile is named `MODEL`.
- The skill evals' variables are `SKILL_EVALS_AGENT_BEDROCK_MODEL` and `SKILL_EVALS_GRADER_BEDROCK_MODEL`.

Why: Craig, "I can't tell if this is for running codeguard, pytest evals, or the plugin skill evals. a name that describes it would clear that up."

## 90. Adapters are standard-library scripts that import nothing from codeguard

- `stop.sh` is a standard-library Python script run with `uv run --script`, so uv is the only prerequisite. `jq` is not required.
- Adapters import nothing from codeguard, so they can ship separately.
- Build the simplest thing first. A feature removed under this rule returns as its own feature when it is needed.

Why: `python3` may not be on PATH.

## 91. Telemetry goes to Logfire

- Logfire records one span per hook run, stage, concern and check. `judge` spans record `loaded_files` and `changed_files`.
- Claude Code's own OTel export goes to Logfire, not a separate collector.
- Better Stack is not used.

Why: Better Stack is logs and uptime, not per-stage traces.

## 92. CLI judge concurrency follows the machine

- CLI judge processes run `os.process_cpu_count()` at a time.

Why: each process waits on the network and costs about 270 MB of memory, so the count follows the machine.

## 93. A judge prompt is tested by codeguard's own LLM tests

- The judge prompt is tested by codeguard's LLM tests, `pytest -m llm`, not by `codeguard eval`, which is a client command for a project's own rules.

Why: the judge prompt is codeguard's, so its check is a codeguard test.

## 94. Bindings route by `paths` until a binding needs a detector

- A binding routes files to rules by `paths`, which is required.
- Routing by framework through `detects` (ast-grep framework detectors) is designed, not built, and `paths` stays required until a binding needs a detector.

## 95. The judge's prompt is ordered so concerns on one file share the cache

- The judge's system prompt holds what every concern on a file shares, so concerns on one file share the cached prefix.
- The rule is not part of the shared prefix.

Why: putting the rule before the code wrote the file to the cache at the write price on every call.

## 96. The first judge call for a prefix finishes before the others on it start

- The first call for a cached prefix finishes before the other calls that share the prefix start.

Why: waiting one call's latency saves a file-sized cache write on every other concern.

## 97. codeguard plans to run claude through the Agent SDK

- codeguard runs `claude` through the Agent SDK instead of parsing `stream-json`. This is not built yet: the claude CLI provider still runs the CLI with `stream-json`.
- The Agent SDK only runs `claude`. Agent SDK tools and the Messages API stay rejected for searches.

Why: `stream-json` isn't documented as stable.

## 98. Duplicated skill-eval graders stay copies, checked in CI

- The writing-rules skill's eval cases keep their own copies of a duplicated grader, and a CI check fails when copies of one grader differ. The check is not built yet.
- Symlinks and a copy script are rejected.

Why: the eval tool has no shared graders, symlinks aren't documented and could silently skip, and a copy script goes stale.

## 99. codeguard keeps private rules for dogfooding

- codeguard ships no public rules, but it keeps private rules for dogfooding. The first is a rule bound to `judge.md` that enforces the architecture's judge contract.
- This bends the invariant that the framework has no rules built in. The exception is recorded as a decision when the work starts. The work is deferred.

## 100. A project can't override a binding's provider or model

- A project can override a binding's `paths`, `exclude_paths`, `severity` and `ci_only`, but not its `provider` or `model`. This stands until the queued binding-override work ships.
- Still open: whether an overridden model needs a rule eval pass on it, and how a project shows that.

Why: a rule is then judged with the model its evals pass on.

## 101. Invariants keep their numbers

- The architecture's invariants keep their numbers. Invariant 10 is retired and not reused.

## 102. Docs and commits use a placeholder for the Google Cloud project

- Docs write `CODEGUARD_JUDGE__GEMINI__PROJECT=<project>` and the dummy key `proxy-injected`, never a real key or our project number.
- The placeholder governs every new file, commit and PR text.
- main's history is not rewritten for earlier commits that held the number: it is an identifier, not a credential, because using the project still needs the key or the proxy's sign-in.

Why: Craig, "The public testing guide should not list our project number. it should use a placeholder."
