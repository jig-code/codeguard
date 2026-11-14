from collections.abc import Iterable
from fnmatch import fnmatchcase
from pathlib import PurePath

# The languages a judge rule's paths name, by their files' extensions.
LANGUAGES: dict[str, tuple[str, ...]] = {
    "javascript": ("js", "jsx", "mjs", "cjs"),
    "python": ("py", "pyi"),
    "ruby": ("rb",),
    "typescript": ("ts", "tsx", "mts", "cts"),
}


def language_of(file: str) -> str | None:
    extension = PurePath(file).suffix.removeprefix(".")
    return next(
        (language for language, extensions in LANGUAGES.items() if extension in extensions), None
    )


def named_languages(patterns: Iterable[str]) -> frozenset[str]:
    """The languages a path pattern names by its file extension, as `**/*.py` names Python."""
    return frozenset(
        language
        for pattern in patterns
        if (extension := _extension(pattern)) is not None
        for language, extensions in LANGUAGES.items()
        if any(fnmatchcase(known, extension) for known in extensions)
    )


def _extension(pattern: str) -> str | None:
    name = PurePath(pattern).name
    return name.rsplit(".", 1)[1] if "." in name else None
