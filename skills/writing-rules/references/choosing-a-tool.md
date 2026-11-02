# Is it a codeguard rule?

codeguard adds the checks a project's linters and type checker can't do. Before writing
a rule, decide whether the convention is codeguard's at all, and if it is, which kind of
rule it needs.

## Conventions that aren't codeguard's

Write no codeguard rule for a convention a deterministic check can decide exactly, even
when asked for one, and whether or not the project runs that check or has it turned on.
Prefer another tool's check; when no tool has one, a project script run in CI decides it.
A deterministic check gives the same answer every run and costs nothing; a judge rule
sees one changed file, guesses at the rest and costs a model call. Tell the user the
convention isn't a codeguard rule and which kind of check can decide it. Setting up or
writing that check isn't part of writing rules.

| The convention | Decided by |
|---|---|
| A check a linter or type checker has, or can be configured to have | That linter or type checker |
| A value's type and where it flows, such as an argument that may be `None` | A type checker |
| Which modules may import which | An import linter |
| Logic across nodes (counting, state, types), or an autocorrect | A custom linter rule |
| Who implements, calls or references a symbol, such as every class that implements an interface | A language server's find-references |
| A fact about the whole repository, such as every package being covered by the import contract | The tool's own check if it has one, else a project script run in CI |

## Pattern rule or judge rule

| The convention | Rule |
|---|---|
| A code shape in one file | A codeguard pattern rule |
| Judgment | A judge rule |

A judge rule is for judgment, never for something syntax, types or a symbol lookup
decide. A pattern rule replaces a custom linter rule that only matches a shape: a YAML
file and test cases instead of a class and a spec. Ruff has no custom rules and no
syntax-selector config, so most Python shape conventions land in codeguard; ESLint's
`no-restricted-syntax` covers most TypeScript shapes, so fewer land there.
