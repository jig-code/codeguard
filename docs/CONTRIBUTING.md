# Contributing

[codeguard's architecture](architecture.md) says why codeguard works as it does and the
invariants every change must keep. Before changing the judge (its template, its
prompt, its tools or what it's given), the review pipeline, or anything an invariant
covers, read it and check the change against it.

[Testing](testing.md) says which tests a change needs you to run.

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

## Change the writing-rules skill

Before changing the `writing-rules` skill, in `plugin/skills/writing-rules/`, or its
evals, in `plugin/evals/writing-rules/`, load the [authoring-writing-rules skill](../.claude/skills/authoring-writing-rules/SKILL.md).
It says what the skill must be and how to write its evals.
[The skill evals](testing.md#the-skill-evals) says how to run them.

The authoring-writing-rules skill and the
[writing-skills skill](../.claude/skills/writing-skills/SKILL.md) it loads draw on these
sources. Guidance none of them covers is codeguard's own decision.

- [The new rules of context engineering for Claude 5 generation models](https://claude.dev/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/)
  (Jul 24, 2026):
  - writing only what the agent wouldn't know;
  - brevity;
  - progressive disclosure;
  - when examples constrain;
  - constraining a skill only in highly important areas.
- [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices):
  - plain words;
  - when to give a reason;
  - examples that steer format;
  - telling the agent what to do rather than what not to do.
- [Extend Claude with skills](https://code.claude.com/docs/en/skills):
  - the `description`;
  - a concise body;
  - what goes in `SKILL.md` versus a reference file.
- [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals.md):
  - eval prompts;
  - graders on the result and on the steps (`tool_used`);
  - `regex` versus `llm` graders;
  - rubrics.

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
  Edits to `plugin/hooks/stop.py` apply on the next hook run. Edits to `hooks.json` or
  `plugin.json` need `/reload-plugins`. The hook runs the codeguard release the plugin's
  version names, not this clone's code: to review with this clone, start the agent with
  `CODEGUARD=/path/to/codeguard/.venv/bin/codeguard`.

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

1. Set the release's `<version>` in all four places, in the PR with the change or in a
   PR of its own:
   - `version` in `pyproject.toml`, which rule packages' `codeguard` ranges are checked
     against;
   - `version` in `plugin/.claude-plugin/plugin.json` and
     `plugin/.codex-plugin/plugin.json`.
     Claude Code installs a plugin update only when this changes, so a release with
     the old version reaches no one;
   - `version` in `plugin/bin/codeguard`, the codeguard release the plugin runs.

   Between releases, `pyproject.toml`'s version may run ahead of the plugin's, which
   names a release that is already tagged. CI fails a PR whose plugin manifests and
   `plugin/bin/codeguard` give different versions.
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
   The release workflow checks that all four versions match the tag, then moves
   the major tag (`v0`) to the release. If it fails, fix the versions on `main`, then
   move the tag to the fixed commit and push it again:
   ```sh
   git tag --force v<version> origin/main
   git push --force origin v<version>
   ```
