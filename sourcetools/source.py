"""Defines the Source, SourceLocation and SourceRange classes."""

from collections import namedtuple
from enum import Enum, auto
import bisect

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
    """Represents an single logical unit of source code, e.g. the contents of a source file.
    """

    def __init__(self, content, *, name=None, encoding='utf-8', line_ending=LineEnding.LF):
        """Initialise a Source object with contents and optional name, encoding and line endings.

        Args:
            content: The textual contents of the Source object. May be `str` or `bytes`.

            name (optional): The logical name of the Source object.
                Typically, this should be the filename or path of the Source file if it
                was read from a file, or something like "<stdin>" if the Source was read from
                standard input.

            encoding (optional): The encoding used to decode `content` if it has type `bytes`.
                If `encoding` has type `bytes`, then this is the encoding that will be used to
                decode it into a `str` object. The value of this parameter must be a valid
                Python encoding name. If the type of `content` is not `bytes`, then this parameter
                has no effect.

            line_ending (optional): The type of line endings that are present in `content`.
                The kind of line endings determine how the Source object interprets lines
                in the source content, and affects the line and column numbers of any
                `SourceLocation` or `SourceRange` derived therefrom.
                If the value of this parameter is `LineEnding.DETECT`, then the line endings
                of the file will be detected by examining the first newline present in the file.
                If the value of this parameter is `LineEnding.DETECT` and no newlines are present
                in the file, then a `LineEndingDetectionFailed` exception will be raised.

        Raises:
            LineEndingDetectionFailed: If the type of `content` is `bytes` and `line_ending` is
                equal to `LineEnding.DETECT` and the line ending detection algorithm fails to
                determine a line ending kind for the source content.
        """

        self._name = name
        self._content = content.decode(encoding) if isinstance(content, bytes) else content

        # Detect the content's line endings if necessary
        if line_ending == LineEnding.DETECT:
            line_ending = self._detect_line_ending()
            if line_ending is None:
                raise LineEndingDetectionFailed('Failed to detect line endings')

        # Normalise line endings
        self._content = self._normalise_line_endings(self._content, line_ending)

        self._line_ending = line_ending
        self._offset_line_col_map = _OffsetLineColMap(self)

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
            f'Source index must be int, SourceLocation, slice or SourceRange, not {name}')

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

    @property
    def range(self):
        """Returns a SourceRange consisting of the entirety of the Source content."""

        return SourceRange(self, 0, len(self))

    def _detect_line_ending(self):
        if '\r\n' in self._content:
            return LineEnding.CRLF
        elif '\n' in self._content:
            return LineEnding.LF
        else:
            return None

    def _normalise_line_endings(self, content, line_ending):
        # Normalise all line endings in `content` to LineEnding.LF and return the normalised
        # content, assuming that the current line endings are given by `line_ending`.
        # If `line_ending` is LineEnding.LF, then nothing is done.
        if line_ending == LineEnding.LF:
            return content

        return content.replace(line_ending.value, LineEnding.LF.value)

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
    def char(self):
        """Returns the character designated by this location."""

        return self._source[self._offset]

    @property
    def offset(self):
        """Returns the SourceLocation's offset within the parent Source object."""

        return self._offset

    @property
    def line_col(self):
        """Returns a LineCol object that designates the line and column number of this
        SourceLocation.
        """

        return self._source._offset_line_col_map.lookup_line_col(self._offset)

    @property
    def is_newline(self):
        """Return True if the current location refers to a newline character."""

        return self.char == LineEnding.LF.value

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

        if not 0 <= begin <= end <= len(source):
            raise RangeError(f'({begin}, {end}) is not a valid SourceRange')

        self._source = source
        self._begin = begin
        self._end = end

    def __len__(self):
        """Return the number of locations in this range."""

        return self._end - self._begin

    def __iter__(self):
        """Return an iterator that yields each location in this range."""

        for offset in range(self._begin, self._end):
            yield SourceLocation(self._source, offset)

    def lines(self):
        """Return an iterator that yields each logical line of this range as a SourceRange."""

        begin = None
        for location in self:
            if begin is None:
                begin = location.offset

            if location.is_newline:
                yield SourceRange(self._source, begin, location.offset)
                begin = None

    @property
    def chars(self):
        """Returns the string of characters designated by this range."""

        return self._source[self._begin:self._end]

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
            SourceLocation(self._source, self._end))

    @property
    def is_empty(self):
        """Return True if this range is empty."""

        return len(self) == 0

class _OffsetLineColMap:
    def __init__(self, source):
        self._source = source
        self._forward_map = self._create_forward_map()
        self._backward_list = self._create_backward_list(self._forward_map)
        self._eof_newline = self._has_eof_newline()

    def _has_eof_newline(self):
        # Return True if the parent Source object has a newline at the end of the file.

        if len(self._source.content) > 0:
            return self._source.content[-1] == LineEnding.LF.value

        return False

    def _create_forward_map(self):
        # Creates and returns a dictionary whose keys are line numbers and whose offsets
        # are the offset in which that line begins in the parent Source object.

        # The first line always begins at offset 0 (even if the source is empty)
        line_count = 1
        result = {line_count: 0}

        next_line = self._find_next_line()
        while next_line is not None:
            line_count += 1
            result[line_count] = next_line
            next_line = self._find_next_line(next_line)

        return result

    def _create_backward_list(self, forward_map):
        # Create and return a dictionary that is the inverse of the given forward map,
        # see `_create_forward_map`.

        return [(offset, line) for line,offset in forward_map.items()]

    def _find_next_line(self, start_offset=0):
        # Search, from `start_offset`, for a newline in the parent Source.
        # If a newline is found, return the offset of the first character of the line
        # that immediately follows. If a newline is not found, or the newline is at the end
        # of the parent Source object, then return None.

        begin = self._source.content.find(LineEnding.LF.value, start_offset)
        end = begin + 1

        return end if begin != -1 and end < len(self._source) else None

    def _is_valid_line_col(self, line_col):
        # Returns True if the given LineCol object is valid (refers to a valid line and column
        # in the parent Source object).

        if line_col.line not in self._forward_map:
            return False

        if line_col.line + 1 in self._forward_map:
            end_offset = self._forward_map[line_col.line + 1] - 1
        else:
            end_offset = len(self._source) - 1 if self._has_eof_newline else 0

        return 1 <= line_col.col <= end_offset - self._forward_map[line_col.line]

    def lookup_offset(self, line_col):
        # Return the offset of the character located by the `LineCol` object given
        # as `line_col` in the parent Source object.

        if not self._is_valid_line_col(line_col):
            raise ValueError(f'{line_col} is not a valid line and/or column')

        return self._forward_map[line_col.line] + line_col.col - 1

    def lookup_line_col(self, offset):
        # Return a `LineCol` object that designates the character at `offset` in the parent
        # Source object.

        if not (0 <= offset < len(self._source)):
            raise ValueError(f'{offset} is not a valid offset')

        offsets = [o for o,_ in self._backward_list]
        line_offset, line_num = self._backward_list[bisect.bisect_right(offsets, offset) - 1]
        return LineCol(line_num, offset - line_offset + 1)
