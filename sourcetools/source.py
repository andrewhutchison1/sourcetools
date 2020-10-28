"""Defines the Source, SourcePos and SourceRange classes."""

class Source:
    def __init__(self, content):
        """Initialises the Source object with `content`, which is an iterable whose elements
        are strings, which are assumed to refer to individual characters in a source file.
        """
        self._content = content

class SourcePos:
    def __init__(self, source, offset):
        """Initialises the SourcePos object with a Source object and an integer offset from the
        beginning (0) of the Source's content that uniquely identifies a single source
        character.
        """
        self._source = source
        self._offset = offset

class SourceRange:
    def __init__(self, source, begin, end):
        """Initialises the SourceRange object with a Source object and `begin` and `end`
        integer offsets which designate, respectively, the range of source characters
        [begin, end) in the Source object.
        """
        self._source = source
        self._begin = begin
        self._end = end
