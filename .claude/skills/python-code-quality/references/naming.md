# Naming

## Name and body correspond

This test applies to every type, method, function, constant and module. State in one
sentence what the symbol does, read from its body, then check both directions:

- the salient verb and nouns of the sentence appear in the name;
- every word of the name is borne out by the body.

A mismatch either way is the defect. Suppose a change adds this to `Review`:

```python
def merge_diagnostics(self, other: "Review") -> "Review":
    return Review(diagnostics=tuple(d for d in self.diagnostics if d.blocks))
```

The body keeps this review's blocking diagnostics and ignores `other`. Nothing is merged,
so the name is false, and `blocking` appears nowhere in it. Rename it after what it does
(`blocking_only`) and drop the parameter it never reads.

Token lists ("don't use `process`") are illustrations, never the rule: judge by
correspondence.

## Misleading is worse than vague

A vague name (`process`, `handle`, `run_step`) under-informs. A name that implies
behavior the code doesn't perform misinforms, and sends readers and reviewers down the
wrong model of the code. Treat a misleading name as the more severe finding.

Both the verb and the noun carry meaning: `handle_data` restates "does something to
something". `with_judge_errors_as_warnings` says what changes and to what.

## A constant's name is its contract

A constant's name says what it is for. Reuse it only for that. When another use needs the
same value today, give that use its own constant, because the two will change for
different reasons. For example, `_READ_ONLY_TOOLS` in `claude_judge.py` names the tools
the judge may call. A new call that needs a tool list for a different purpose, say the
tools a warmup call allows, gets its own name even if the value is identical: the day the
judge gains a tool, the warmup must not silently gain it too. Likewise `DEFAULT_MODEL_KEY`
names the cache key for an unnamed model; it isn't a display label for "the default
model" (that is `JudgeModel.label`).

## Specific rules

- **Name a type or function after what it produces, owns or does.** Not a generic role
  (`Manager`, `Processor`, `Preparer`).
- **`Builder` only for the Builder pattern**: a type that assembles a product step by
  step through a builder interface. Otherwise name it after what it creates.
- **`Params`, not `Request`, for a group of arguments.** `Request` is for a real request
  to something outside, as `JudgeRequest` is a request to a model.
- **Named constructors are named after their source, not their caller**:
  `Binding.from_config`, `Bindings.from_rulesets`, `JudgeRequest.of_change`. Choose a
  variant by what it builds, not by which caller wants it.
- **One verb per concept** across collaborating types. Don't mix `load`/`read` or
  `build`/`assemble` for the same operation.
- **A module is named after its primary type or concept** (`claude_result.py` holds
  `ClaudeResult` and the private shapes it parses). Bucket names:
  `no-bucket-module-names`. A module holding a second unrelated public class is a bucket
  whatever its name: [module-structure.md](module-structure.md).
