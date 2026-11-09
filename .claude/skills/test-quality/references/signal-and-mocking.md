# Mocking, assertions and names (gates 2, 3, 4, 8)

- Gate 2: real objects over mocks
- Gate 3: `==` over `in`
- Gate 4: whole result objects
- Gate 8: names

## Gate 2: real objects over mocks

Replace a collaborator with `MagicMock`, `patch()` or `monkeypatch.setattr` only at the
process boundary: a call to a model provider's API, an HTTP request to a third party, or
a service that needs external credentials. codeguard's judge CLIs (claude, codex, gemini)
are replaced at that boundary by the fake CLIs.

Git and the filesystem are not a boundary. Use a real repository (`GitRepo`, the `repo`
fixture) and real files under `tmp_path`; mocked git output drifts from real git (diff
ranges, untracked files, flags).

`monkeypatch.setattr` on a module constant or function so that real work doesn't run is
stubbing the SUT; inject the dependency instead. Vary an environment variable
(`monkeypatch.setenv`, `mock.patch.dict(os.environ)`) when that setting is what the test
exercises, never to stop production code from running. If a patch seems to need a written
justification, build the injected version: it usually exposes a missing seam.

Pass real data for every input the SUT reads. An empty or dummy value
(`make_binding(triggers=frozenset())` where real triggers belong) is fine for an input the
SUT provably never reads. When real data makes the test fail, that failure is a
production bug to fix.

Use the first that works: a real object; a shared fake (`RecordingJudge` in
`tests/recording_judge.py`, `ScriptedGemini` in `tests/gemini_provider/test_gemini_judge.py`,
the fake CLIs); an inline protocol stub, for a framework contract test whose fake is the
domain; `patch()`/`MagicMock` at the process boundary. Search other test modules for an
equivalent stub before writing one, and share it when one exists.

### Drive the production factory

When a production factory or builder assembles the SUT, the test calls it and injects the
double through its constructor. A fixture that rebuilds the same graph, or re-derives what
the factory derives from its input, keeps passing when the factory changes. When the
factory has no seam for the double, add a constructor parameter with the production
default. For a derived value, build the factory's input (a `Binding`, files in a
`GitRepo`) and call it (`JudgeRequest.of_change`).

### Extend a shared fake by configuration

A shared fake abstracts one layer. Configure it (a canned verdict, scripted answers) and
assert on its in-layer state in the test body. Don't subclass it to assert inside an
override or to read another subsystem:

```python
# Not this: a judge fake that checks the cache's store inside judge()
class StoreCheckingJudge(RecordingJudge):
    def judge(self, request):
        assert list(self.store) == []
        return super().judge(request)


# This
wrapped = RecordingJudge()
CachedJudge(wrapped=wrapped, store=store, root=repo.root).judge(request)
assert wrapped.received == [request]
```

A lower-layer invariant (the cache was empty) gets its own test at that layer.

## Gate 3: `==` over `in`

Use `==` against the full expected value. Containment (`in`, `<=`) is right when all three
hold:

1. The fragment is exact and complete: a whole line, token or value the SUT produces.
2. It sits inside a larger value whose content another component authors.
3. A whole-value `==` would pin that component's content, so the test would break on edits
   to code it doesn't target.

Authorship decides ownership, not who runs the `join`. A SUT that joins sections authored
elsewhere (a `SKILL.md` read verbatim by `Skill.from_file`, the changes
`JudgeRequest.of_change` renders) owns only their selection and order. So asserting the
`<rule name=...>` line of `JudgeRequest.prompt`, or one whole section extracted with a
`_section_lines`-style helper, is the exception. Check: breaking the logic under test
fails the assertion, and editing an unrelated rule's `SKILL.md` doesn't.

Using `in` because you can't predict the SUT's own output is the smell; pin the value.

## Gate 4: whole result objects

```python
assert diagnostic == make_diagnostic(judged=True, line=2)
```

When the result type has `__eq__`, use one whole-object `==`, even when separate `==`
lines cover every current field. When one field carries noise you can't control, assert it
as gate 12 describes. A bare `len()` has the same gap. Consolidate per-index
checks into one structural assertion (`assert [d.line for d in diagnostics] == [1, 2]`).

When the result has no `__eq__`, or is a scalar, assert every observable field by name,
not as a tuple, which loses the field names in the failure.

## Gate 8: names

A test name says what its assertion proves, in the production code's words: no synonyms
(inject vs resolve, build vs assemble) and no coined terms. `test_quiet_judge_*` for a
verdict with no violations invents a term; `test_no_violations_*` uses the real one. A
word in the name that appears nowhere in the code under test is the tell.
