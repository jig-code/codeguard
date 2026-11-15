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

    def judged_lines(
        self, points: frozenset[int], replaced: frozenset[int] = frozenset()
    ) -> frozenset[int]:
        scopes = self._standing(NodeKind.SCOPE, replaced)
        members = self._standing(NodeKind.MEMBER_LIST, replaced)
        statements = _Statements(
            self.of_kind(NodeKind.STATEMENT),
            self.of_kind(NodeKind.HANDLER),
            self.of_kind(NodeKind.GUARDED_BLOCK),
            self.of_kind(NodeKind.BLOCK),
            replaced,
        )
        return frozenset(
            line
            for point in points
            for line in (
                {point}
                if point in self._prose_only_lines
                else _context_lines(scopes, members, statements, point)
            )
        )

    def kind_lines(
        self, points: frozenset[int], replaced: frozenset[int] = frozenset()
    ) -> dict[str, frozenset[int]]:
        spans: dict[str, set[int]] = {}
        for node in self.nodes:
            if (
                not isinstance(node.kind, NodeKind)
                and any(self._touches(node, point) for point in points)
                and not _wholly_replaced(node, replaced)
            ):
                spans.setdefault(node.kind, set()).update(node.lines)
        return {kind: frozenset(lines) for kind, lines in spans.items()}

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

    def _standing(self, kind: NodeKind, replaced: frozenset[int]) -> list[SyntaxNode]:
        return [node for node in self.of_kind(kind) if not _wholly_replaced(node, replaced)]

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


@dataclass(frozen=True)
class _Statements:
    nodes: list[SyntaxNode]
    handlers: list[SyntaxNode]
    guarded: list[SyntaxNode]
    blocks: list[SyntaxNode]
    replaced: frozenset[int]

    def lines_around(self, point: int, scope: SyntaxNode | None) -> set[int]:
        around = [
            node
            for node in self.nodes
            if node.spans(point) and (scope is None or _within(node, scope))
        ]
        statement = min(around, key=_length) if around else None
        if statement is None:
            return {point}
        if _wholly_replaced(statement, self.replaced):
            gone = max(
                (node for node in around if _wholly_replaced(node, self.replaced)), key=_length
            )
            return self._kept_around(gone, point, scope)
        return {*statement.lines, *self._handler_try_and_guarded_block(statement)}

    def _kept_around(self, gone: SyntaxNode, point: int, scope: SyntaxNode | None) -> set[int]:
        if guarded := self._handler_try_and_guarded_block(gone):
            return set(guarded)
        return self._owner_header(gone, point, scope)

    def _owner_header(self, gone: SyntaxNode, point: int, scope: SyntaxNode | None) -> set[int]:
        owners = [
            node
            for node in self.nodes
            if _encloses(node, gone)
            and not _wholly_replaced(node, self.replaced)
            and (scope is None or _within(node, scope))
        ]
        if not owners:
            return {point}
        owner = min(owners, key=_length)
        blocks = [
            block
            for block in self.blocks
            if _encloses(owner, block)
            and block.spans(point)
            and not _wholly_replaced(block, self.replaced)
        ]
        body = min(blocks, key=_length).start_line if blocks else owner.start_line
        return set(_header_lines(owner, body))

    def _handler_try_and_guarded_block(self, statement: SyntaxNode) -> range:
        if not any(_same(statement, handler) for handler in self.handlers):
            return range(0)
        owners = [node for node in self.nodes if _encloses(node, statement)]
        if not owners:
            return range(0)
        owner = min(owners, key=_length)
        blocks = [
            block
            for block in self.guarded
            if _encloses(owner, block) and not _wholly_replaced(block, self.replaced)
        ]
        if not blocks:
            return range(0)
        return range(owner.start_line, min(blocks, key=lambda block: block.start).end_line + 1)


def _context_lines(
    scopes: list[SyntaxNode], members: list[SyntaxNode], statements: _Statements, point: int
) -> set[int]:
    enclosing = [scope for scope in scopes if scope.spans(point)]
    innermost = min(enclosing, key=_size) if enclosing else None
    if innermost is None:
        return statements.lines_around(point, None)
    body = next(
        (node for node in members if node.spans(point) and _is_own_member_list(innermost, node)),
        None,
    )
    if body is None:
        return set(innermost.lines)
    return {*_header_lines(innermost, body.start_line), *statements.lines_around(point, body)}


def _header_lines(node: SyntaxNode, body_start: int) -> range:
    return range(node.start_line, max(body_start, node.start_line + 1))


def _size(node: SyntaxNode) -> int:
    return node.end_line - node.start_line


def _length(node: SyntaxNode) -> int:
    return node.end - node.start


def _same(node: SyntaxNode, other: SyntaxNode) -> bool:
    return (node.start, node.end) == (other.start, other.end)


def _encloses(outer: SyntaxNode, inner: SyntaxNode) -> bool:
    return outer.start <= inner.start and inner.end <= outer.end and not _same(outer, inner)


def _within(node: SyntaxNode, scope: SyntaxNode) -> bool:
    return scope.start_line <= node.start_line and node.end_line <= scope.end_line


def _is_own_member_list(scope: SyntaxNode, members: SyntaxNode) -> bool:
    return _within(members, scope) and not _within(scope, members)


def _wholly_replaced(node: SyntaxNode, replaced: frozenset[int]) -> bool:
    return bool(replaced) and replaced.issuperset(node.lines)
