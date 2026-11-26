# Choosing a tool

Three tools can check a convention: a static analysis tool other than codeguard, a
pattern rule and a judge rule. Choose the tool by what decides whether code keeps or
breaks the rule, not by the words of the request.

- Choose a static analysis tool whenever a built-in check of one that any project can use
  at no cost covers the convention. codeguard doesn't replace those tools: it adds the
  checks that they can't do.
- Otherwise, choose a pattern rule when syntax alone, within one file, decides whether
  code keeps or breaks the rule.
- Choose a judge rule for every other convention.
