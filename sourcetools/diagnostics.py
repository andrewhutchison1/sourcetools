from enum import Enum, auto
from typing import Iterator

from .source import Range

class AnnotationKind(Enum):
    NOTE = auto()
    WARN = auto()
    ERROR = auto()
    FATAL = auto()

class Annotation:
    """An Annotation is a source.Range that is annotated with a string message, and has an
    AnnotationKind attached to it. This class models what could be called an error message,
    compiler error or compiler warning.
    """

    def __init__(self, range_: Range, msg: str, kind: AnnotationKind):
        self._range = range_
        self._msg = msg
        self._kind = kind
        self._full_lines = range_.full_lines()

    @property
    def range(self) -> Range:
        return self._range

    @property
    def message(self) -> str:
        return self._msg

    @property
    def kind(self) -> AnnotationKind:
        return self._kind

    @property
    def full_lines(self) -> Range:
        return self._full_lines

class Diagnostic:
    """A Diagnostic models a single logical 'problem' in source code that consists of a list of
    one or more causally-related Annotations.

    A Diagnostic consists of a top-level annotation that represents a symptomatic problem in
    source code. The diagnostic can optionally contain one or more annotations that reflect
    a causal chain of problems, with the deepest such annotation representing a root cause,
    similar to a stack trace.
    """

    def __init__(self, top: Annotation):
        """Initialise the Diagnostic with a top-level Annotation.

        The top-level annotation represents the problem in source code that occurred at the top
        level. The diagnostic also has an AnnotationKind, which is taken from the `kind`
        property of the top-level annotation.
        """

        self._top = top
        self._rest = []

    def __len__(self) -> int:
        """Return the total number of annotations represented in this Diagnostic, including
        the top-level annotation.
        """

        return 1 + len(self._rest)

    def __iter__(self) -> Iterator[Annotation]:
        """Yields each annotation represented in this diagnostic, in the order of effect to
        cause.
        """

        yield self._top
        yield from self._rest

    def add_cause(self, cause: Annotation) -> 'Diagnostic':
        """Add a causal Annotation to this Diagnostic and return self for chaining."""

        self._rest.append(cause)
        return self

    @property
    def top(self) -> Annotation:
        return self._top

    @property
    def root_cause(self) -> Annotation:
        """Return the Annotation that ultimately caused this problem this diagnostic represents.

        If there are no causal annotations, then the top-level annotation is returned.
        """

        return self._rest[-1] if len(self._rest) > 0 else self.top

    @property
    def kind(self) -> AnnotationKind:
        return self._top.kind
