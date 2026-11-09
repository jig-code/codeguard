# Choosing a tool

codeguard adds the checks a project's exact tools can't do. Decide by what decides a
violation, not by the words the convention is asked in.

A convention that a linter, a type checker, an import linter, a language server or a
similar exact tool can check, directly, through its configuration or with a custom rule,
isn't codeguard's, whether or not the project runs that tool or turns that check on. An
exact tool gives the same answer every run, costs nothing, and already runs in the editor.
A way past the tool, such as a cast or a comment that silences it, doesn't make the
convention a judgment when the tool's configuration can forbid it. Write no rule, and say
the convention isn't codeguard's responsibility. Don't name or set up the tool that checks
it.

A codeguard pattern rule is for a code shape in one file that those tools can't express.

A judge rule is only for what needs judgment, never for something syntax, types or a
lookup across the repository decide.
