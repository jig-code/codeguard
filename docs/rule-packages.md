# Make a rule package

For whoever maintains a rule package: rulesets that projects opt into
([Opt into a rule package](add-codeguard.md#opt-into-a-rule-package)).

## A package is a git repo

A rule package is a git repo with a `codeguard-package.yaml` at its root and a
directory for each ruleset it lists:

```yaml
name: codeguard
rulesets: [python]
ast-grep: ">=0.45"         # the ast-grep versions its pattern rules work with
codeguard: ">=0.2"         # the codeguard versions that can load it
judge:                     # optional: see Choose a judge (judges.md)
  provider: bedrock
  model: us.anthropic.claude-haiku-5-5
```

A project's config never names the package: it picks it by git URL and ref, and its
rulesets and rules by their own names. The `name` shows only in diagnostics, as in
`codeguard/python/no-del-param`.

Each ruleset directory has the layout of a project's `.codeguard/`
([Where rules live](write-rules.md#where-rules-live)), and its rules are written and
tested the same way ([Write rules](write-rules.md)).

## CI and releases

Run `codeguard test` and `codeguard eval` at the package root; they cover every ruleset.
Tag releases `v<major>.<minor>.<patch>`; projects name the tag as their `ref`.
[jig-code/codeguard-rules](https://github.com/jig-code/codeguard-rules) is
an example.

## Try a local package

`kind: path` with `path: ../my-rules` in place of `git` uses a local package, for
working on one. To use it without editing the committed config, put that config in a
gitignored file such as `codeguard.local.yaml` and set
`CODEGUARD_CONFIG=codeguard.local.yaml`. The path is relative to the repository root.

## A private package

For a private package in CI, pass the action a token that can read it:

```yaml
      - uses: jig-code/codeguard@v0.11.0
        with:
          claude-code-oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          packages-token: ${{ secrets.CODEGUARD_PACKAGES_TOKEN }}
```
