# Isolation and behavior

## Isolation

- Files and repositories live under `tmp_path`, not in the working tree.
- Change process state with `monkeypatch` or a fixture that `yield`s and then restores
  it, so the next test starts clean.

## Test behavior through public methods

Call the SUT's public methods and assert on what they return, store or send across the
boundary. Don't test private methods (`_build_deps`), and don't assert on the arguments
internal components pass each other: such tests break on refactoring while behavior holds.

Where a test needs to see what reaches the model, script it through the seam the code
already takes (see [pydantic-ai-testing-guidelines.md](pydantic-ai-testing-guidelines.md)).

## Error paths

Raise the error where production would meet it: from the scripted model
(`ScriptedGemini([http_error(400, "Bad request.")])`), the fake CLI or a real file on
disk, not by patching an internal method.

## Time

Control time with an injected clock or start time rather than a patch.
