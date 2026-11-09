# Telemetry

Set `LOGFIRE_TOKEN` to a Logfire write token and codeguard sends a trace of each run.
Without it, codeguard sends nothing. Set it where the agent runs: your shell profile, or
`env` in `~/.claude/settings.json`.

- `claude judges {rule} on {file}`: one span per Claude call, with `model`, `num_turns`,
  `duration_ms`, `cost_usd`, `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
  `cache_creation_input_tokens`, `thinking_tokens` and `tool_calls`.
- `gemini judges {rule} on {file}`: one span per Gemini judgement, with `model`,
  `num_turns`, `input_tokens`, `output_tokens`, `cache_read_input_tokens` and
  `thinking_tokens`, summed over its requests, and `tool_calls`. Its time starts once the call has a slot,
  not while it waits for one. Inside it, Pydantic AI's spans record each request and
  tool call with its content: the prompt, which holds the rule and the changed
  code, Gemini's thought summaries, the files it read and its verdict.
- `tool_calls` on a Claude or Gemini span is each call the judge made to its read-only
  tools, in order: the tool's name and the arguments it gave, such as the path it read or
  the pattern it searched for. It records a call that failed, and on Gemini, the calls of
  a judgement that returned no verdict. Claude's call that returns the verdict isn't one.
- `judge {rule} on {file}`: one span per rule and file, with `cache_hit`, `violations`,
  `loaded_files` (the files the verdict depends on) and `changed_files` (the loaded files
  that changed since the cached verdict, which is why it was judged again). The Claude or
  Gemini span inside it has that judgement's time and tokens.
- `review {repository}`: `files`, `diagnostics`, `errors`, and `host` (the caller passed
  with `--host`, such as `claude-code` or `codex`).

In CI, pass the token as the action's `logfire-token` input.
