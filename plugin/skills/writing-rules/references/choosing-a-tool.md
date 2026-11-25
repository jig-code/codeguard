# Choosing a tool

codeguard adds the checks that a project's exact tools can't do. An exact tool, such as a
linter, a type checker, an import linter or a language server, gives the same answer
every run and costs nothing. Choose by what decides whether code keeps or breaks the
rule, not by the words the request uses.

A convention that an exact tool can check, directly, through its configuration or with a
custom rule, isn't codeguard's, whether or not the project runs that tool or turns that
check on. A way past the tool, such as a cast or a comment that silences it, doesn't
make the convention a judgment when the tool's configuration can forbid it. Write no
rule, and say that the convention isn't codeguard's to check.

A codeguard pattern rule is for a code shape in one file that the project's exact tools
can't check.

A judge rule is only for what needs judgment, never for something that syntax, types or
an exact search of the repository decides.
