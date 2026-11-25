# Choosing a tool

Three tools can check a convention: an exact tool, a pattern rule and a judge rule. An
exact tool is any linter, type checker or similar tool for the project's language, and
gives the same answer on every run. Choose the tool by what decides whether code keeps or
breaks the rule, not by the words of the request.

- Choose an exact tool whenever one can check the convention with a check that it ships
  with. codeguard doesn't replace exact tools: it adds the checks that they can't do.
- Choose a pattern rule when the convention is about a code shape within one file, and an
  exact tool could check that shape only through a custom rule. A rule that you would
  write yourself in the exact tool's configuration counts as a custom rule.
- Choose a judge rule when the convention needs judgment. A convention that syntax or
  types decide doesn't need judgment. When syntax decides only some of the code that
  would break the rule, the convention needs judgment.
