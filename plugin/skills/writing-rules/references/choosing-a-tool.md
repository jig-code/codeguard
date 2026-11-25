# Choosing a tool

Three tools can check a convention: an exact tool, a pattern rule and a judge rule. An
exact tool is any linter, type checker or similar tool for the project's language, and
gives the same answer on every run. Choose the tool by what decides whether code keeps or
breaks the rule, not by the words of the request.

- Choose an exact tool whenever a built-in check of one covers the convention. codeguard
  doesn't replace exact tools: it adds the checks that they can't do.
- Otherwise, choose a pattern rule when syntax alone, within one file, decides whether
  code keeps or breaks the rule.
- Choose a judge rule for every other convention.
