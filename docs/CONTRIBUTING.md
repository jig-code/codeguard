# Contributing

[codeguard's architecture](architecture.md) says why codeguard works as it does and the
invariants every change must keep. Before changing the judge (its template, its
prompt, its tools or what it's given), the review pipeline, or anything an invariant
covers, read it and check the change against it.

[Testing](testing.md#changing-codeguard) says which checks a change to codeguard needs.

## Run the tests

```sh
uv run pytest
```

`uv run pytest` runs offline: it calls no model.

## LLM tests

The LLM tests check that the judge's instructions, request and tools still get the right
verdicts from a real model. Each one reviews an edit in a scratch repository the way
`codeguard review` does, with the fixture package's Gemini judge on Vertex AI, so they
need Gemini credentials ([Gemini on Google Cloud](judges.md#gemini-on-google-cloud)) and
cost tokens. They are
marked `llm`, which plain `pytest` deselects. `--judge-provider` and `--judge-model`
judge them with another model, as `codeguard eval --provider` does:
`--judge-provider bedrock` runs them on Haiku on Bedrock. CI runs them
([`ci.yaml`](../.github/workflows/ci.yaml)); run them after changing the judge's
instructions, request or tools, once to verify the change, then twice more:

```sh
uv run pytest -m llm -n 4 --llm-runs 1 -x
uv run pytest -m llm -n 4 --llm-runs 2
```

Local Codex checks use the same fixtures with
`--judge-provider codex-cli --judge-model gpt-6-luna`.

`-n 4` runs four tests at once, each making up to 2 Gemini calls at once. It only saves
time: any number gives the same result, though more may hit Gemini's tokens-per-minute
limit.

Their fixtures are the cases in `evals/judge/python/rule-evals/`, with the rule files and
bindings beside them. When a case fails or flips between runs, follow the
Rule failures bullet in [Architecture](architecture.md#testing-a-rule) and
[Testing](testing.md), and look at the judge prompt as well. The plain suite checks each
case's triggers.

The `writing-rules` skill has its own evals in `evals/writing-rules/`;
[docs/skill-evals.md](skill-evals.md) says how to run and write them.

## How codeguard reviews itself

codeguard reviews its own changes with the rules its
[`.codeguard/config.yaml`](../.codeguard/config.yaml) opts into: the `general` and
`python` rulesets of [codeguard-rules](https://github.com/jig-code/codeguard-rules), at
the commit its `ref` pins. Their pattern rules check code with no model; their judge
rule, `dry`, calls a judge. Every review uses the rules at that commit, locally and in
CI, until a pull request moves the pin. `.codeguard/` holds no rules of its own, so
`codeguard test`, which CI's action runs, has nothing to check here: the packaged rules
are tested in their package's CI.

Every review here runs this checkout's codeguard, never a release, so the version in
`pyproject.toml` doesn't say which build ran:

| Where | Runs | Reviews | Judge |
|---|---|---|---|
| When an agent or subagent stops | `hooks/stop.py` with `.venv/bin/codeguard`, set in `.claude/settings.json` | Uncommitted and untracked files | The `claude` CLI and its default model |
| By hand | `uv run codeguard review` | Uncommitted and untracked files; with `--base <branch>`, every change since that branch | The `claude` CLI and its default model |
| CI's `codeguard-rules` job | The action at the checkout's root (`uses: ./`) | The pull request's changes since its base branch | Gemini, which `ci.yaml` sets |

- The hook passes `--judge-errors-as-warnings` and `--skip-ci-only`, so a judge call
  that fails, and a `ci_only` rule, are left to CI.
- A local review reuses a verdict from `~/.cache/codeguard/judgements` until something
  the judge's answer depends on changes ([The verdict cache](architecture.md#components)).
  CI starts with an empty cache, so it judges every file afresh.
- A finding on codeguard's own code is fixed in the code, whatever its severity. `dry`
  is a `warning`, and the hook shows a warning to you, not to the agent, so read it.
  When a finding is wrong, fix the rule or its cases in its package, never the code to
  get past it.

## Run your clone in a project

Run the CLI from this clone. `--editable` links the tool to the source, so edits
apply on the next run; reinstall only after changing dependencies:

```sh
uv tool install --editable .
```

Point a project's hooks at this clone.

- Claude Code: in the project's `.claude/settings.local.json`, declare the marketplace
  as a directory, which replaces the GitHub entry for you only
  ([Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)).
  ```json
  {
    "extraKnownMarketplaces": {
      "codeguard": {
        "source": { "source": "directory", "path": "/path/to/codeguard" }
      }
    }
  }
  ```
  Python edits apply on the next hook run. Edits to `hooks.json` or `plugin.json`
  need `/reload-plugins`.

  This clone's own `.claude/settings.json` runs its hooks with `.venv/bin/codeguard`, the
  build `uv sync` keeps current. `CODEGUARD=<path>` makes the hook run any other build.
- Codex:
  ```sh
  codex plugin marketplace add /path/to/codeguard
  codex plugin add codeguard@codeguard
  ```
  Run `codex plugin add` again after each edit.

## Release

Release when a change on `main` should reach the projects using codeguard, or when a
rule package needs it (a package's `codeguard` range is checked against the CLI's
version). Engineers get only released versions; see [Keep the plugin up to
date](using-codeguard.md#keep-the-plugin-up-to-date).

1. Bump the version to the same `<version>` in all three files, in the PR with the
   change or in a PR of its own:
   - `version` in `pyproject.toml`, which rule packages' `codeguard` ranges are checked
     against;
   - `version` in `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`.
     Claude Code installs a plugin update only when this changes, so a release with
     the old version reaches no one.

   CI fails a PR whose three versions differ.
2. Validate:
   ```sh
   claude plugin validate .
   ```
3. Once it is merged, tag the merge commit and push the tag:
   ```sh
   git fetch origin main
   git tag v<version> origin/main
   git push origin v<version>
   ```
   The release workflow checks that the tag matches all three versions, then moves
   the major tag (`v0`) to the release. If it fails, fix the versions on `main`, then
   move the tag to the fixed commit and push it again:
   ```sh
   git tag --force v<version> origin/main
   git push --force origin v<version>
   ```
