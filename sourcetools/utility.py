"""Utility functions and classes."""

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
    elif '\n' in content:
        return LineEnding.LF
    else:
        return None

def normalise_line_endings(content, current, new=LineEnding.LF):
    if current == new:
        return content

    if current == LineEnding.DETECT:
        current = detect_line_endings(content)

    return content.replace(current.value, new.value) if current is not None else None
