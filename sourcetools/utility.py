"""Utility functions and classes."""

from bisect import bisect_left
from enum import Enum, auto

class LineEnding(Enum):
    DETECT = auto()
    LF = '\n'
    CRLF = '\r\n'
    UNIX = LF
    WINDOWS = CRLF

def detect_line_endings(content):
    if '\r\n' in content:
        return LineEnding.CRLF

    if '\n' in content:
        return LineEnding.LF

    return None

def normalise_line_endings(content, current, new=LineEnding.LF):
    if current == new:
        return content

    if current == LineEnding.DETECT:
        current = detect_line_endings(content)

    return content.replace(current.value, new.value) if current is not None else None

def lower_bound_index(sequence, value):
    """Return the index of the greatest lower bound of `value` in the sorted iterable `sequence`.

    `sequence` is binary-searched for the greatest element that is less-than `value`.
    If `sequence` is not sorted, then the result will be undefined.
    """
    index = bisect_left(sequence, value)
    return index - 1 if index != 0 else 0
