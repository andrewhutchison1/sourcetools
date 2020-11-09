from enum import Enum, auto

from .source import Range

class AnnotationKind(Enum):
    NOTE = auto()
    WARN = auto()
    ERROR = auto()
    FATAL = auto()

class Annotation:
    def __init__(self, range_: Range, msg: str, kind: AnnotationKind):
        self._range = range_
        self._msg = msg
        self._kind = kind
        self._full_lines = range_.full_lines()

    @property
    def range(self):
        return self._range

    @property
    def message(self):
        return self._msg

    @property
    def kind(self):
        return self._kind

    @property
    def full_lines(self):
        return self._full_lines
