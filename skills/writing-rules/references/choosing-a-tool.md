# Choosing a tool

codeguard adds the checks a project's linters can't do. The cheapest exact tool decides a
convention: take the first row that can express it, judged by what decides a violation,
not by the words the convention is asked in. A judge rule is for judgment, never
for something syntax, types or a symbol lookup decide, because an exact tool gives the
same answer every run, costs nothing, and already runs in the editor.

When a convention isn't codeguard's to check, write no rule and say it isn't codeguard's
responsibility. Don't name or set up the tool that checks it.

| The convention | Checked by |
|---|---|
| A linter or type checker the project runs already has the check | That linter or type checker (Ruff, ESLint, RuboCop; basedpyright, mypy, `tsc`) |
| A linter or type checker can express it through configuration, whether or not the project turns that setting on | Its configuration: ESLint `no-restricted-syntax` (AST selectors) or `no-restricted-imports`, Ruff `banned-api`, a configurable RuboCop cop; a type checker's strictness settings |
| Which modules may import which | The project's import linter (import-linter, `import/no-restricted-paths`) |
| A code shape in one file | A codeguard pattern rule |
| Logic across nodes (counting, state, types), or an autocorrect | The linter's custom rule: a Pylint checker, an ESLint plugin rule, a RuboCop custom cop |
| Who implements, calls or references a symbol | A language-server lookup (find references, find implementations), or a dead-code tool built on one |
| Judgment | A judge rule |

## Type checker settings

A convention about where untyped values flow is a type checker's job, including one
asked as validation: that data from a parse, a deserializer or a network response is
checked before it's used. Such data is untyped until code checks it, so a setting that
reports values typed `Any` catches every unchecked use at once, with no rule to
maintain, and leaves checked values alone.

## Language-server lookups

Implementers, callers and references are exact lookups across the repository. A judge
rule can't decide them: the violation spans files, and a review drops a violation whose
lines the change didn't touch. That holds for a function nobody calls, an interface
without implementers, and a symbol used from one module only.

## Pattern rules and custom linter rules

A codeguard pattern rule replaces a custom rule that only matches a shape: a YAML file
and test cases instead of a class and a spec. A custom rule with an autocorrect stays
in the linter.

Ruff has no custom rules and no syntax-selector config, so most Python shape
conventions land in codeguard. ESLint's `no-restricted-syntax` covers most
TypeScript shapes, so fewer land there.
