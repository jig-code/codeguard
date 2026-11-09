# Pytest conventions

## Marks

Put a mark that covers a test class (`@pytest.mark.usefixtures("fake_cli_config")`,
`@pytest.mark.llm`) on the class as a decorator, not in a module-level `pytestmark`. The
decorator stays next to the tests it governs; `pytestmark` also applies to anything added
to the module later.

```python
@pytest.mark.usefixtures("fake_cli_config")
class TestCachedJudge:
    def test_stores_the_judgement(self): ...
```

## Environment variables

Set a fixed value with a decorator, which shows the precondition above the test and undoes
itself. Use `monkeypatch.setenv` when the value comes from another fixture, such as a path
under `tmp_path`.

```python
@mock.patch.dict(os.environ, {"CODEGUARD_CONFIG": "codeguard.local.yaml"})
def test_reads_the_local_config(self): ...
```

