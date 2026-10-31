import functools
import itertools
import re
import subprocess
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import JsonValue
from pydantic_ai import Tool

_MAX_LINES = 2000
_MAX_RESULTS = 200


def _answering_errors[**P](tool: Callable[P, str]) -> Callable[P, str]:
    # A path or pattern the model got wrong is an answer it can act on, not a failed run.
    @functools.wraps(tool)
    def answer(*args: P.args, **kwargs: P.kwargs) -> str:
        try:
            return tool(*args, **kwargs)
        except (OSError, ValueError, re.error) as error:
            return f"Error: {error}"

    return answer


def _tool(function: Callable[..., str]) -> Tool[object]:
    return Tool(
        function, takes_ctx=False, docstring_format="google", require_parameter_descriptions=True
    )


@dataclass(frozen=True)
class FileTools:
    root: Path
    loaded_files: list[str] = field(default_factory=list)
    calls: list[dict[str, JsonValue]] = field(default_factory=list)

    @property
    def tools(self) -> list[Tool[object]]:
        return [_tool(self.read_file), _tool(self.grep), _tool(self.glob)]

    @_answering_errors
    def read_file(self, path: str, offset: int = 1) -> str:
        """Read a file in the working directory.

        Use it when the convention needs code the `changes` element doesn't show: the rest of
        the file under review, or a file it imports, calls or names. Don't use it to see lines
        the `changes` element already shows.

        Args:
            path: The file's path relative to the working directory, such as `orders/order.py`.
            offset: The number of the first line to return. Default: 1.

        Returns:
            Up to 2000 lines from `offset`, each starting with its line number and a tab.
        """
        self.calls.append({"tool": "read_file", "path": path, "offset": offset})
        file = self._inside(path)
        self.loaded_files.append(path)
        lines = file.read_text(errors="replace").splitlines()
        start = max(offset, 1)
        return "".join(
            f"{number:>6}\t{line}\n"
            for number, line in enumerate(lines[start - 1 : start - 1 + _MAX_LINES], start=start)
        )

    @_answering_errors
    def grep(self, pattern: str, glob: str = "**/*") -> str:
        """Search the contents of the files in the working directory.

        Use it to find code by what it contains when you don't know which file holds it: where
        a name is defined, what calls it, or other code that does the same thing. When you know
        the file, use `read_file`. Hidden files and files git ignores aren't searched.

        Args:
            pattern: A Python regular expression, matched against each line.
            glob: Only search files whose paths match this glob, such as `**/*.py`. Default: all
                files.

        Returns:
            Up to 200 matching lines, each as `path:line:text`, or `No matches.`.
        """
        self.calls.append({"tool": "grep", "pattern": pattern, "glob": glob})
        expression = re.compile(pattern)
        matches = (
            (relative, f"{relative}:{number}:{line}")
            for relative, file in self._files(glob)
            for number, line in enumerate(_text_lines(file), start=1)
            if expression.search(line)
        )
        return self._shown(matches) or "No matches."

    @_answering_errors
    def glob(self, pattern: str) -> str:
        """List the files in the working directory whose paths match a glob.

        Use it to find files by name or place, such as the modules of a package or the tests of
        a module. It doesn't read the files: use `grep` to search their contents and
        `read_file` to read one. Hidden files and files git ignores aren't listed.

        Args:
            pattern: A glob matched against paths relative to the working directory, such as
                `orders/**/*.py`.

        Returns:
            Up to 200 paths, one per line, or `No files.`.
        """
        self.calls.append({"tool": "glob", "pattern": pattern})
        return (
            self._shown((relative, relative) for relative, _ in self._files(pattern)) or "No files."
        )

    def _shown(self, lines: Iterator[tuple[str, str]]) -> str:
        kept = list(itertools.islice(lines, _MAX_RESULTS + 1))
        shown = kept[:_MAX_RESULTS]
        self.loaded_files.extend(dict.fromkeys(file for file, _ in shown))
        text = "\n".join(line for _, line in shown)
        if len(kept) > _MAX_RESULTS:
            return f"{text}\n(stopped at {_MAX_RESULTS} results)"
        return text

    def _inside(self, path: str) -> Path:
        root = self.root.resolve()
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"{path} is outside the working directory")
        return resolved

    def _files(self, pattern: str) -> Iterator[tuple[str, Path]]:
        root = self.root.resolve()
        for file in _candidates(root):
            relative = file.relative_to(root)
            hidden = any(part.startswith(".") for part in relative.parts)
            if (
                relative.full_match(pattern)
                and file.is_file()
                and not hidden
                and file.resolve().is_relative_to(root)
            ):
                yield str(relative), file


def _candidates(root: Path) -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if listed.returncode != 0:
        return sorted(root.rglob("*"))
    return sorted(root / name for name in listed.stdout.decode().split("\0") if name)


def _text_lines(file: Path) -> list[str]:
    try:
        return file.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
