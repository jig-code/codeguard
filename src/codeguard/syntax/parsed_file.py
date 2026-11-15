from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from typing import Self

from codeguard.config import ChangeKind
from codeguard.line_range import LineRange
from codeguard.syntax.syntax_node import SyntaxNode
from codeguard.syntax.syntax_table import NodeKind

_PROSE = frozenset({ChangeKind.COMMENT, ChangeKind.DOCSTRING})


@dataclass(frozen=True)
class ParsedFile:
    content: bytes
    nodes: tuple[SyntaxNode, ...]

    @property
    def definitions(self) -> tuple[str, ...]:
        return tuple(node.text for node in self.of_kind(NodeKind.DEFINITION))

    def scope_lines(self, points: frozenset[int]) -> frozenset[int]:
        scopes = self.of_kind(NodeKind.SCOPE)
        return frozenset(
            line
            for point in points
            if (innermost := min(_spanning(scopes, point), key=_length, default=None))
            for line in innermost.lines
        )

    def touched_kinds(
        self,
        points: frozenset[int],
        base: Self | None,
        removed_code: frozenset[int] = frozenset(),
    ) -> frozenset[str]:
        kinds = {kind for point in points for kind in self._kinds_spanning(point)}
        if base:
            kinds.update(kind for line in removed_code for kind in base._kinds_spanning(line))
        if points or removed_code:
            kinds.add(ChangeKind.ANY)
        if self._scope_names != (base._scope_names if base else Counter()):
            kinds.add(ChangeKind.DEFINITION_ADDED_OR_REMOVED)
        return frozenset(kinds)

    def kinds_on(self, lines: LineRange) -> frozenset[str]:
        kinds: set[str] = set()
        for number in lines.numbers:
            kinds |= self._kinds_spanning(number)
            if any(node.spans(number) for node in self.of_kind(NodeKind.SCOPE_NAME)):
                kinds.add(ChangeKind.DEFINITION_ADDED_OR_REMOVED)
        return frozenset(kinds)

    def of_kind(self, kind: NodeKind | str) -> list[SyntaxNode]:
        return sorted((node for node in self.nodes if node.kind == kind), key=lambda n: n.start)

    def text(self, node: SyntaxNode) -> bytes:
        return self.content[node.start : node.end]

    def replaced(self, replacements: Iterable[tuple[SyntaxNode, bytes]]) -> bytes:
        content = self.content
        for node, text in sorted(replacements, key=lambda pair: pair[0].start, reverse=True):
            content = content[: node.start] + text + content[node.end :]
        return content

    def _kinds_spanning(self, line: int) -> set[str]:
        found: set[str] = {
            node.kind
            for node in self.nodes
            if not isinstance(node.kind, NodeKind) and self._touches(node, line)
        }
        if not found or not found <= _PROSE:
            found.add(ChangeKind.CODE)
        return found

    def _touches(self, node: SyntaxNode, line: int) -> bool:
        return node.spans(line) and (line not in self._prose_only_lines or self._is_prose(node))

    def _is_prose(self, node: SyntaxNode) -> bool:
        if isinstance(node.kind, ChangeKind) and node.kind not in _PROSE:
            return False
        return any(_encloses(prose, node) or _same(prose, node) for prose in self._prose)

    @cached_property
    def _prose(self) -> list[SyntaxNode]:
        return [node for node in self.nodes if node.kind in _PROSE]

    @cached_property
    def _prose_only_lines(self) -> frozenset[int]:
        starts = [0, *(offset + 1 for offset, byte in enumerate(self.content) if byte == 10)]
        on_line: dict[int, list[SyntaxNode]] = {}
        for node in self._prose:
            for line in node.lines:
                on_line.setdefault(line, []).append(node)
        lines: set[int] = set()
        for line, nodes in on_line.items():
            start = starts[line - 1]
            end = starts[line] - 1 if line < len(starts) else len(self.content)
            if all(
                chr(self.content[offset]).isspace()
                or any(node.start <= offset < node.end for node in nodes)
                for offset in range(start, end)
            ):
                lines.add(line)
        return frozenset(lines)

    @property
    def _scope_names(self) -> Counter[str]:
        return Counter(node.text for node in self.of_kind(NodeKind.SCOPE_NAME))


def _spanning(nodes: list[SyntaxNode], line: int) -> list[SyntaxNode]:
    return [node for node in nodes if node.spans(line)]


def _length(node: SyntaxNode) -> int:
    return node.end - node.start


def _same(node: SyntaxNode, other: SyntaxNode) -> bool:
    return (node.start, node.end) == (other.start, other.end)


def _encloses(outer: SyntaxNode, inner: SyntaxNode) -> bool:
    return outer.start <= inner.start and inner.end <= outer.end and not _same(outer, inner)
