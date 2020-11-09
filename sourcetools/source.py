"""Defines the Source, Location and Range classes."""

from dataclasses import dataclass
from typing import Union, Generic, TypeVar, Iterator, Tuple, List

from .utility import LineEnding, normalise_line_endings, lower_bound_index

_T = TypeVar('T', int, 'Location')
@dataclass
class RangePair(Generic[_T]):
    begin: _T
    end: _T

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

    def __init__(self, content, *, name='<none>', encoding='utf-8', line_ending=LineEnding.LF):
        """Initialise a Source object with contents and optional name, encoding and line endings.

        Args:
            content: The textual contents of the Source object. May be `str` or `bytes`.

            name (optional, default "<none>"): The logical name of the Source object.
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
                `Location` or `Range` derived therefrom.
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

        self._metrics = Metrics(self)

    def __hash__(self) -> int:
        """Return the hash of this Source object."""

        return hash((self._name, self._content))

    def __len__(self) -> int:
        """Returns the length of the Source's content iterable."""

        return len(self._content)

    @property
    def name(self) -> str:
        """Returns the name of this Source object."""

        return self._name

    @property
    def content(self) -> str:
        """Returns the Source's content."""

        return self._content

    @property
    def metrics(self) -> 'Metrics':
        """Returns the Source's metrics object."""

        return self._metrics

    @property
    def line_ending(self) -> LineEnding:
        """Returns the line endings type of this Source object."""

        return self._line_ending

    def range(self) -> 'Range':
        """Returns a Range consisting of the entirety of the Source content."""

        return Range(self, 0, len(self))

class Location:
    def __init__(self, source: Source, offset: int):
        """Initialises the Location object with a Source object and an integer offset from the
        beginning (0) of the Source's content that uniquely identifies a single source
        character.
        """

        if not source.metrics.valid_offset(offset):
            raise ValueError(f'Offset {offset} out of range')

        self._source = source
        self._offset = offset
        self._linecol = self.source.metrics.get_linecol(offset)

    def __hash__(self) -> int:
        """Return the hash of this Location."""

        return hash((self._source, self._offset))

    def __eq__(self, rhs: 'Location') -> bool:
        """Compare this Location with another for equality. Two Location objects
        are equal if they refer to the same Source object (by identity), and store the same
        offset within that Source.
        """

        if isinstance(rhs, Location) and self._source is rhs._source:
            return self._offset == rhs._offset

        return NotImplemented

    def __ne__(self, rhs: 'Location') -> bool:
        """Compare this Location with another for inequality."""

        return not self == rhs

    def __lt__(self, rhs: 'Location') -> bool:
        """Return True if this Location object is ordered before the Location `rhs`.
        Ordering is performed against the offsets of each Location.
        """

        if isinstance(rhs, Location) and self._source is rhs._source:
            return self._offset < rhs._offset

        return NotImplemented

    def __gt__(self, rhs: 'Location') -> bool:
        """Return True if this Location object is ordered after the Location `rhs`.
        Ordering is performed against the offsets of each Location.
        """

        return self != rhs and not self < rhs

    def __le__(self, rhs: 'Location') -> bool:
        return not self > rhs

    def __ge__(self, rhs: 'Location') -> bool:
        return not self < rhs

    def __str__(self) -> str:
        return f'{self.source.name} {self.linecol.line}:{self.linecol.col}'

    @property
    def source(self) -> Source:
        """Return the Source object to which this location refers."""

        return self._source

    @property
    def char(self) -> str:
        """Returns the character designated by this location."""

        return self._source.content[self._offset]

    @property
    def offset(self) -> int:
        """Returns the Location's offset within the parent Source object."""

        return self._offset

    @property
    def linecol(self) -> LineCol:
        """Returns a LineCol object that designates the line and column number of this
        Location.
        """

        return self._linecol

    @property
    def line(self) -> int:
        """Return the line number of this location."""

        return self.linecol.line

    @property
    def col(self) -> int:
        """Return the column number of this location."""

        return self.linecol.col

    @property
    def is_newline(self) -> bool:
        """Return True if the current location refers to a newline character."""

        return self.char == LineEnding.LF.value

    @property
    def is_end(self) -> bool:
        """Returns True if this Location refers to the end of parent Source object."""

        return self._offset == len(self._source)

class Range:
    def __init__(self, source: Source, begin: int, end: int):
        """Initialises the Range object with a Source object and `begin` and `end`
        integer offsets which designate, respectively, the range of source characters
        [begin, end) in the Source object.
        """

        if not all((
                source.metrics.valid_offset(begin),
                source.metrics.valid_offset(end),
                begin <= end)):
            raise ValueError(f'({begin}, {end}) is not a valid Range')

        self._source = source
        self._begin = begin
        self._end = end

    def __hash__(self) -> int:
        """Return the hash of this Range."""

        return hash((self._source, self._begin, self._end))

    def __len__(self) -> int:
        """Return the number of locations in this range."""

        return self._end - self._begin

    def __eq__(self, rhs: 'Range') -> bool:
        return hash(rhs) == hash(self)

    def __ne__(self, rhs: 'Range') -> bool:
        return not self == rhs

    def __lt__(self, rhs: 'Range') -> bool:
        includes_begin = all((
                rhs._begin <= self._begin < rhs._end,
                self._end < rhs._end))

        includes_end = all((
                rhs._begin < self._begin < rhs._end,
                self._end <= rhs._end))

        return includes_begin != includes_end

    def __gt__(self, rhs: 'Range') -> bool:
        return rhs < self and rhs != self

    def __le__(self, rhs: 'Range') -> bool:
        return not self > rhs

    def __ge__(self, rhs: 'Range') -> bool:
        return not self < rhs

    def __iter__(self) -> Iterator[Location]:
        """Iterate through each location in this range.

        Yields:
            The next location in this range.
        """

        for offset in range(self._begin, self._end):
            yield Location(self._source, offset)

    def __and__(self, rhs: 'Range') -> 'Range':
        if not any(location in self for location in rhs):
            return None

        return Range(
                self.source,
                max((self.offsets.begin, rhs.offsets.begin)),
                min((self.offsets.end, rhs.offsets.end)))

    def __contains__(self, location: Location) -> bool:
        """Return True if the given Location is contained in this range."""

        return self._begin <= location.offset < self._end

    def __getitem__(self, index: Union[int, slice]) -> Union[Location, 'Range']:
        if isinstance(index, int):
            if 0 <= index < len(self):
                return Location(self.source, self._begin + index)

            raise IndexError(f'Index {index} out of range')

        if isinstance(index, slice):
            if 0 <= index.start < len(self) and index.start <= index.stop < len(self):
                if index.step is not None:
                    raise ValueError('Slice step must be None')

                begin = self._begin + index.start
                end = self._begin + index.stop
                return Range(self.source, begin, end)

            raise ValueError('Invalid slice')

        raise TypeError('Index must be int or slice')

    def __str__(self) -> str:
        begin = f'{self.locations.begin.linecol.line}:{self.locations.begin.linecol.col}'
        end = f'{self.locations.end.linecol.line}:{self.locations.end.linecol.col}'
        return f'{self.source.name} {begin}-{end}'

    def full_lines(self) -> 'Range':
        """Return a Range that is a (not necessarily strict) superset of this Range that
        contains only complete logical source lines.
        """

        return Range(
                self.source,
                self.source.metrics.get_line_start_offset(self.locations.begin.line),
                self.source.metrics.get_line_end_offset(self.locations.end.line))

    def each_line(self) -> Iterator['Line']:
        """Return an iterator that yields each logical source line of this Range.

        Yields:
            Each logical source line of this Range. The first and last lines yielded
            may not be complete source lines if this Range does not include them completely.
        """

        begin = None
        for location in self:
            if begin is None:
                begin = location.offset

            if location.is_newline:
                yield Line(self.source, begin, location.offset)
                begin = None

        if begin is not None:
            yield Line(self.source, begin, self.offsets.end)

    @property
    def source(self) -> Source:
        """Return the parent Source object of this range."""

        return self._source

    @property
    def chars(self) -> str:
        """Returns the string of characters designated by this range."""

        return self._source.content[self._begin:self._end]

    @property
    def offsets(self) -> RangePair[int]:
        """Returns RangePair containing the begin and end offsets of this Range within the
        parent Source object.
        """

        return RangePair(self._begin, self._end)

    @property
    def locations(self) -> RangePair[Location]:
        """Returns a RangePair containing the begin and end locations of the Range within the
        parent Source object, returning them as Location objects.
        """

        return RangePair(
            Location(self._source, self._begin),
            Location(self._source, self._end))

    @property
    def is_empty(self) -> bool:
        """Return True if this range is empty."""

        return len(self) == 0

    @property
    def line_numbers(self) -> List[int]:
        """Return a list consisting of the line numbers each (possibly partial) logical
        source line in this range.
        """

        return list(range(self.locations.begin.line, self.locations.end.line + 1))

class Line(Range):
    @property
    def line_number(self):
        return self.locations.begin.line

def count_linecols(source: Source, offset: int = 0, linecol: LineCol = LineCol(1,1)) \
        -> Iterator[Tuple[int, LineCol]]:
    """Generate line and column information for each character in `source`.

    Return an object that yields a 2-tuple containing an offset and LineCol object
    representing the line and column position of each character in `source`.

    Args:
        source: The Source whose content will be counted.
        offset (optional): The offset to start counting from.
        linecol (optional): A LineCol object to start counting from.

    Yields:
        A 2-tuple whose first element is the offset of the yielded character and whose second
        element is the LineCol.
    """

    line,col = linecol
    for i,char in enumerate(source.content[offset:], start=offset):
        yield i,LineCol(line, col)

        if char == LineEnding.LF.value:
            line += 1
            col = 1
        else:
            col += 1

class Metrics:
    def __init__(self, source: Source, max_search: int = 128):
        self._source = source
        self._linecol_map = _LineColMap(source, max_search)
        self._linecol_counts = self._make_linecol_counts()

    @property
    def source(self) -> Source:
        return self._source

    def get_offset(self, linecol: LineCol) -> int:
        if not self.valid_linecol(linecol):
            raise ValueError(f'Invalid LineCol {linecol}')

        return self._linecol_map.get_offset(linecol)

    def get_linecol(self, offset: int) -> LineCol:
        if not self.valid_offset(offset):
            raise ValueError(f'Invalid offset {offset}')

        if offset == len(self.source):
            return LineCol(*list(self._linecol_counts.items())[-1])

        return self._linecol_map.get_linecol(offset)

    def get_lines(self, begin: int, end: int) -> Tuple[int, int]:
        """Return a Tuple that denotes begin, end offsets of the lines denoted by `lines`."""
        
        if not self.valid_line(begin) or not self.valid_line(end) or not begin < end:
            raise ValueError('Not a valid line number')

        begin_offset = self.get_offset(LineCol(begin, 1))
        end_offset = self.get_offset(LineCol(end - 1, self._linecol_counts[end - 1]))
        return (begin_offset, end_offset)

    def get_line_start_offset(self, line: int) -> int:
        """Return the offset of the character at the start of the logical source line `line`."""

        if not self.valid_line(line):
            raise ValueError('Not a valid line number')

        return self.get_offset(LineCol(line, 1))

    def get_line_end_offset(self, line: int) -> int:
        """Return the offset of the character at the end of the logical source line `line`."""

        if not self.valid_line(line):
            raise ValueError('Not a valid line number')

        return self.get_offset(LineCol(line, self._linecol_counts[line]))

    def valid_linecol(self, linecol: LineCol) -> bool:
        """Return True if `linecol` represents a valid LineCol object in the parent Source."""

        line,col = linecol
        return line in self._linecol_counts and 0 < col <= self._linecol_counts[line]

    def valid_offset(self, offset: int) -> bool:
        """Return True if `offset` is a valid character offset in the parent Source."""

        return 0 <= offset <= len(self.source)

    def valid_line(self, line: int) -> bool:
        """Return True if the line number `line` is valid."""

        return 1 <= line <= self.line_count

    def col_count(self, line: int) -> int:
        """Return the number of columns of the given line number `line` in the parent Source."""

        return self._linecol_counts[line]

    @property
    def line_count(self) -> int:
        """Return the number of lines in the parent Source."""

        return len(self._linecol_counts)

    def _make_linecol_counts(self):
        result = {}

        for offset,linecol in count_linecols(self.source):
            if self.source.content[offset] == LineEnding.LF.value:
                result[linecol.line] = linecol.col

        return result

class _LineColMap:
    def __init__(self, source: Source, max_search: int):
        self._source = source
        self._offsets, self._linecols = self._make_map(max_search)

    @property
    def source(self) -> Source:
        return self._source

    def get_offset(self, linecol: LineCol) -> int:
        if linecol in self._linecols:
            return self._offsets[self._linecols.index(linecol)]

        index = lower_bound_index(self._linecols, linecol)
        lb_offset, lb_linecol = self._get(index)

        for s_offset,s_linecol in count_linecols(self.source, lb_offset, lb_linecol):
            if s_linecol == linecol:
                return s_offset

        return None

    def get_linecol(self, offset: int) -> LineCol:
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
