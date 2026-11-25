# Choosing a tool

codeguard adds the checks that a project's exact tools can't do. An exact tool, which
gives the same answer every run and costs nothing, is any linter, type checker or similar
tool for the project's language. Choose by what decides whether code keeps or breaks the
rule, not by the words the request uses.

A convention that an exact tool can check, directly or through its configuration, isn't
codeguard's, whether or not the project runs that tool or turns that check on. A way past
the tool that the tool's configuration can forbid doesn't make the convention a
judgment. Write no rule, and say that the convention isn't codeguard's to check.

A codeguard pattern rule is for a code shape in one file that an exact tool could check
only with a custom rule: the pattern rule takes the place of that custom rule.

A judge rule is for what needs judgment, never for something that syntax or types
decide. When syntax decides only some of the shapes that would break the rule, the
convention needs judgment: write a judge rule, not a pattern rule.
