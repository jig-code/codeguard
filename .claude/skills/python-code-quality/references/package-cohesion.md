# Package cohesion

Modules that collaborate as one flow or feature live in one package. Naming each module
well isn't enough: the directory layout groups the concepts too. The test is whether a
reader who knows what a concept does could guess which package it lives in.

codeguard's packages each own one concern, and the import-linter layers in
`pyproject.toml` fix the direction between them: `review` runs the pipeline and defines
the judge interface, each `*_provider` package runs one kind of judge, `config` reads
configuration, `repository` reads git, `syntax` classifies changes, and `rules` wires them
together for the CLI.

## The four shapes to flag

- **A flow split across siblings.** Several packages form one flow but reach into each
  other sideways. Put the stages under one package, or, if the split is deliberate, make
  the direction a layer in import-linter so the seam is designed, not accidental.
- **A thin wrapper package.** A package that only re-exports another's symbols gives one
  concept two homes. Fold it into the package it wraps.
- **A misplaced module.** A module whose concept belongs to a neighbouring package: a
  provider's output parser in `review/`, a binding helper in `cli.py`, a config reader
  outside `config/`. Move it to the owner. A package with a vague name is renamed after
  what it does.
- **A bucket package.** A directory of unrelated single-purpose modules is the package
  form of a `utils.py`. Each module needs an owning concept the package name predicts.

## Why predictability is the test

Each shape breaks the guess differently: the split hides a concept among siblings, the
wrapper gives it two homes, the misplaced module puts it beside the wrong neighbours, and
the bucket has a name that predicts nothing. When the guess fails, flag the layout, not
only the file.
