"""Defines the Source, SourceLocation and SourceRange classes."""

from dataclasses import dataclass
from collections import namedtuple

from .utility import LineEnding, normalise_line_endings, lower_bound_index

RangePair = namedtuple('RangePair', 'begin end')

@dataclass(order=True)
class LineCol:
    line: int
    col: int

    def __iter__(self):
        yield self.line
        yield self.col

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
        self._content = normalise_line_endings(self._content, line_ending)
        self._line_ending = line_ending

        if self._content is None:
            raise LineEndingDetectionFailed()

        self._metrics = SourceMetrics(self)

    def __hash__(self):
        """Return the hash of this Source object."""

        return hash((self._name, self._content))

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
    def metrics(self):
        """Returns the Source's metrics object."""

        return self._metrics

    @property
    def line_ending(self):
        """Returns the line endings type of this Source object."""

        return self._line_ending

    def range(self):
        """Returns a SourceRange consisting of the entirety of the Source content."""

        return SourceRange(self, 0, len(self))

class SourceLocation:
    def __init__(self, source, offset):
        """Initialises the SourceLocation object with a Source object and an integer offset from the
        beginning (0) of the Source's content that uniquely identifies a single source
        character.
        """

        if not 0 <= offset <= len(source):
            raise ValueError(f'Offset {offset} out of range')

        self._source = source
        self._offset = offset
        self._linecol = self.source.metrics.get_linecol(offset)

    def __hash__(self):
        """Return the hash of this SourceLocation."""

        return hash((self._source, self._offset))

    def __eq__(self, rhs):
        """Compare this SourceLocation with another for equality. Two SourceLocation objects
        are equal if they refer to the same Source object (by identity), and store the same
        offset within that Source.
        """

        if isinstance(rhs, SourceLocation) and self._source is rhs._source:
            return self._offset == rhs._offset

        return NotImplemented

    def __ne__(self, rhs):
        """Compare this SourceLocation with another for inequality."""

        return not self == rhs

    def __lt__(self, rhs):
        """Return True if this SourceLocation object is ordered before the SourceLocation `rhs`.
        Ordering is performed against the offsets of each SourceLocation.
        """

        if isinstance(rhs, SourceLocation) and self._source is rhs._source:
            return self._offset < rhs._offset

        return NotImplemented

    def __gt__(self, rhs):
        """Return True if this SourceLocation object is ordered after the SourceLocation `rhs`.
        Ordering is performed against the offsets of each SourceLocation.
        """

        return self != rhs and not self < rhs

    def __le__(self, rhs):
        return not self > rhs

    def __ge__(self, rhs):
        return not self < rhs

    @property
    def source(self):
        """Return the Source object to which this location refers."""

        return self._source

    @property
    def char(self):
        """Returns the character designated by this location."""

        return self._source.content[self._offset]

    @property
    def offset(self):
        """Returns the SourceLocation's offset within the parent Source object."""

        return self._offset

    @property
    def linecol(self):
        """Returns a LineCol object that designates the line and column number of this
        SourceLocation.
        """

        return self._linecol

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
            raise ValueError(f'({begin}, {end}) is not a valid SourceRange')

        self._source = source
        self._begin = begin
        self._end = end

    def __hash__(self):
        """Return the hash of this SourceRange."""

        return hash((self._source, self._begin, self._end))

    def __len__(self):
        """Return the number of locations in this range."""

        return self._end - self._begin

    def __iter__(self):
        """Return an iterator that yields each location in this range."""

        for offset in range(self._begin, self._end):
            yield SourceLocation(self._source, offset)

    def __contains__(self, location):
        """Return True if the given SourceLocation is contained in this range."""

        if not isinstance(location, SourceLocation):
            raise TypeError(f'expected type SourceLocation, got {type(location).__name__}')

        return self._begin <= location.offset < self._end

    def __getitem__(self, index):
        if isinstance(index, int):
            if 0 <= index < len(self):
                return self._source.content[self._begin + index]

            raise IndexError(f'Index {index} out of range')

        if isinstance(index, slice):
            if 0 <= index.start < len(self) and index.start <= index.stop < len(self):
                if index.step is not None:
                    raise ValueError('Slice step must be None')

                return self._source.content[index.start:index.stop]

            raise ValueError('Invalid slice')

        raise TypeError('Index must be int or slice')

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

        return self._source.content[self._begin:self._end]

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

def count_linecols(source, offset=0, linecol=LineCol(1,1)):
    """Generate line and column information for each character in `source`.

    Return an object that yields a 2-tuple containing an offset and LineCol object
    representing the line and column position of each character in `source`.

    Args:
        source (Source): The Source whose content will be counted.
        offset (int, optional): The offset to start counting from.
        linecol (LineCol, optional): A LineCol object to start counting from.

    Yields:
        (int, LineCol): A 2-tuple whose first element is the offset of the yielded
            character and whose second element is the LineCol.
    """

    line,col = linecol
    for i,char in enumerate(source.content[offset:], start=offset):
        yield i,LineCol(line, col)

        if char == LineEnding.LF.value:
            line += 1
            col = 1
        else:
            col += 1

class SourceMetrics:
    def __init__(self, source: Source, max_search=128):
        self._source = source
        self._linecol_map = _LineColMap(source, max_search)
        self._linecol_counts = self._make_linecol_counts()

    @property
    def source(self):
        return self._source

    def get_offset(self, linecol: LineCol) -> int:
        if not self.valid_linecol(linecol):
            raise ValueError(f'Invalid LineCol {linecol}')

        return self._linecol_map.get_offset(linecol)

    def get_linecol(self, offset: int) -> LineCol:
        if not self.valid_offset(offset):
            raise ValueError(f'Invalid offset {offset}')

        return self._linecol_map.get_linecol(offset)

    def valid_linecol(self, linecol: LineCol) -> bool:
        line,col = linecol
        return line in self._linecol_counts and 0 < col <= self._linecol_counts[line]

    def valid_offset(self, offset: int) -> bool:
        return 0 <= offset < len(self.source)

    def _make_linecol_counts(self):
        result = {}

        for offset,linecol in count_linecols(self.source):
            if self.source.content[offset] == LineEnding.LF.value:
                result[linecol.line] = linecol.col

        return result

class _LineColMap:
    def __init__(self, source, max_search: int):
        self._source = source
        self._offsets, self._linecols = self._make_map(max_search)

    @property
    def source(self):
        return self._source

    def get_offset(self, linecol: LineCol):
        if linecol in self._linecols:
            return self._offsets[self._linecols.index(linecol)]

        index = lower_bound_index(self._linecols, linecol)
        lb_offset, lb_linecol = self._get(index)

        for s_offset,s_linecol in count_linecols(self.source, lb_offset, lb_linecol):
            if s_linecol == linecol:
                return s_offset

        return None

    def get_linecol(self, offset: int):
        if offset in self._offsets:
            return self._linecols[self._offsets.index(offset)]

        index = lower_bound_index(self._offsets, offset)
        lb_offset, lb_linecol = self._get(index)

        for s_offset,s_linecol in count_linecols(self.source, lb_offset, lb_linecol):
            if s_offset == offset:
                return s_linecol

        return None

    def _make_map(self, max_search: int):
        offsets = list(range(0, len(self.source), max_search))
        linecols = []

        for offset,linecol in count_linecols(self.source):
            if offset in offsets:
                linecols.append(linecol)

        return offsets,linecols

    def _get(self, index: int):
        return self._offsets[index], self._linecols[index]
