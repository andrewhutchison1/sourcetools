from enum import Enum, auto
from typing import Optional

from .source import Range

class AnnotationKind(Enum):
    NOTE = auto()
    HINT = auto()
    WARN = auto()
    ERROR = auto()
    FATAL = auto()

class Annotation:
    """Models an atomic piece of information of interest that is optionally attached
    to a single Range.
    """

    def __init__(self, range_: Optional[Range], message: str, kind: AnnotationKind):
        """Intitialise the Annotation with an optional Range, a mandatory descriptive
        message summarising the annotation, and an AnnotationKind representing its
        severity.
        """
        self._range = range_
        self._message = message
        self._kind = kind

    @property
    def range(self) -> Optional[Range]:
        return self._range

    @property
    def message(self) -> str:
        return self._message

    @property
    def kind(self) -> AnnotationKind:
        return self._kind

class Diagnostic:
    """Models a source code diagnostic that may be presented to the user.

    A Diagnostic models a single logical problem in a piece of source code.
    It is composed of a sequence of one or more Annotations, each of which
    provide information about the cause of the problem (which may manifest in
    other parts of a source file). In this way a Diagnostic is similar to a stack trace,
    in that the first Annotation stored in a Diagnostic models an effect (e.g. an error),
    and the subsequence Annotations stored in the Diagnostic model causes.
    """

    def __init__(self, topmost: Annotation):
        self._topmost = topmost
        self._causes = []

    def __iter__(self) -> Iterator[Annotation]:
        yield self._topmost
        yield from self._causes

    def first(self) -> Annotation:
        """Return the first Annotation of this Diagnostic."""

        return self._topmost

    def last(self) -> Annotation:
        """Return the last Annotation of this Diagnostic.

        If the Diagnostic does not have any causal Annotation, then the first diagnostic
        is returned.
        """

        return self._causes[-1] if len(self._causes) > 0 else self._topmost
