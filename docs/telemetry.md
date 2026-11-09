# Telemetry

Set `LOGFIRE_TOKEN` to a Logfire write token and codeguard sends a trace of each run to
Logfire. Without it, codeguard sends nothing. Set it where the agent runs: your shell
profile, or `env` in `~/.claude/settings.json`. In CI, pass the token as the action's
`logfire-token` input.

When it's on, each trace holds the repository's name and, for every judge call, the
rule, the file's path, the model, the call's tokens and cost, and the paths the judge
read and the patterns it searched for. A rule judged with Gemini or on Bedrock also sends
its content: the prompt, which holds the rule's text and the changed code, what the
judge's tools returned, including the contents of the files it read, and its verdict.
Calls through the `claude` and `codex` CLIs send no content.

What each span records is in the code: [`cli.py`](../src/codeguard/cli.py) and each
provider's judge under [`src/codeguard/`](../src/codeguard/).
