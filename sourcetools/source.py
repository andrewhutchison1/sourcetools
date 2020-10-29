"""Defines the Source, SourceLocation and SourceRange classes."""
from collections import namedtuple
from enum import Enum, auto

RangePair = namedtuple('RangePair', 'begin end')
LineCol = namedtuple('LineCol', 'line col')

class LineEnding(Enum):
    DETECT = auto()
    LF = '\n'
    CRLF = '\r\n'
    UNIX = LF
    WINDOWS = CRLF

class LineEndingDetectionFailed(Exception):
    pass

class Source:
    def __init__(self, content, *, name=None, encoding='utf-8', line_ending=LineEnding.LF):
        """Initialises the Source object with `content`, which is an iterable whose elements
        are strings, which are assumed to refer to individual characters in a source file.
        Content may be empty. The keyword only parameter `name` specifies a name for this Source
        object, which is generally the filename or something like '<stdin>'. The keyword only
        parameter `encoding` specifies the name of the text encoding that should be used to decode
        `content` if it has type `bytes`. If `content` does not have type `bytes`, then this
        parameter has no effect and the encoding is assumed to be UTF-8.
        The keyworld only parameter `line_ending` designates the
        assumed line-ending sequence (e.g. LF or CRLF). If this parameter is equal to
        `LineEnding.DETECT`, then the Source will attempt to determine the appropriate line ending
        by examining the presence of the first newline sequence. If no newlines are present and
        the `line_ending` parameter is equal to `LineEnding.DETECT`, then a
        `LineEndingDetectionFailed` exception will be raised.
        """
        self._name = name

        if isinstance(content, bytes):
            self._content = content.decode(encoding)
        else:
            self._content = content

        if line_ending == LineEnding.DETECT:
            line_ending = self._detect_line_ending()
            if line_ending is None:
                raise LineEndingDetectionFailed('Failed to detect line endings')

        self._line_ending = line_ending

    def __getitem__(self, index):
        """Performs indexing in the Source object. The exact nature of the indexing depends
        on the type of `index`.
        """
        if isinstance(index, int):
            return self._get_offset(index)
        elif isinstance(index, SourceLocation):
            return self._get_pos(index)
        elif isinstance(index, slice):
            return self._get_slice(index)
        elif isinstance(index, SourceRange):
            return self._get_range(index)

        name = type(index).__name__
        raise TypeError(
            f'Source index must be int, SourceLocation, slice or SourceRange, not {name}'
        )

    def __len__(self):
        """Returns the length of the Source's content iterable."""
        return len(self._content)

    @property
    def name(self):
        """Returns the name of this Source object."""
        return self._name

    @property
    def content(self):
        """Returns the Source's content."""
        return self._content

    @property
    def line_ending(self):
        """Returns the line endings type of this Source object."""
        return self._line_ending

    def _detect_line_ending(self):
        if '\r\n' in self._content:
            return LineEnding.CRLF
        elif '\n' in self._content:
            return LineEnding.LF
        else:
            return None

    def _get_offset(self, offset):
        return self._content[offset]

    def _get_pos(self, pos):
        return self._content[pos.offset]

    def _get_slice(self, slice_):
        if slice_.step is not None:
            raise ValueError('Source slice index may not specify a step parameter')

        return self._content[slice_]

    def _get_range(self, range_):
        begin, end = range_.offsets
        return self._content[begin:end]

class SourceLocation:
    def __init__(self, source, offset):
        """Initialises the SourceLocation object with a Source object and an integer offset from the
        beginning (0) of the Source's content that uniquely identifies a single source
        character.
        """
        if not 0 <= offset <= len(source):
            raise RangeError(f'Offset {offset} out of range')

        self._source = source
        self._offset = offset

    @property
    def offset(self):
        """Returns the SourceLocation's offset within the parent Source object."""
        return self._offset

    @property
    def line_col(self):
        """Returns a LineCol object that designates the line and column number of this
        SourceLocation.
        """
        pass

    @property
    def is_end(self):
        """Returns True if this SourceLocation refers to the end of parent Source object."""
        return self._offset == len(self._source)

class SourceRange:
    def __init__(self, source, begin, end):
        """Initialises the SourceRange object with a Source object and `begin` and `end`
        integer offsets which designate, respectively, the range of source characters
        [begin, end) in the Source object.
        """
        if not 0 <= begin < end <= len(source):
            raise RangeError(f'({begin}, {end}) is not a valid SourceRange')

        self._source = source
        self._begin = begin
        self._end = end

    def __len__(self):
        return self._end - self._begin

    @property
    def offsets(self):
        """Returns RangePair containing the begin and end offsets of this SourceRange within the
        parent Source object.
        """
        return RangePair(self._begin, self._end)

    @property
    def locations(self):
        """Returns a RangePair containing the begin and end locations of the SourceRange within the
        parent Source object, returning them as SourceLocation objects.
        """
        return RangePair(
            SourceLocation(self._source, self._begin),
            SourceLocation(self._source, self._end)
        )
