"""Implements console/terminal printing for diagnostics.
"""

from dataclasses import dataclass
from math import log10
from typing import Dict, Optional, Union

from .diagnostics import Annotation, AnnotationKind, Diagnostic
from .source import Range, Line

class StringBuilder:
    def __init__(self, join_with=''):
        self._join_with = join_with
        self._parts = []

    def __iadd__(self, what: str) -> 'StringBuilder':
        self._parts.append(what)
        return self

    def __str__(self) -> str:
        return self._join_with.join(self._parts)

    def reset(self) -> 'StringBuilder':
        self._parts.clear()
        return self

@dataclass
class PrintOpts:
    source_indent_left: int                     = 4
    source_show_line_nums: bool                 = True
    source_show_gutter: bool                    = True
    source_gutter_char: str                     = '|'
    source_margin: int                          = 1
    source_show_indicator: bool                 = True
    source_indicate_leading_whitespace: bool    = False
    source_indicate_char: str                   = '^'
    show_header: bool                           = True
    show_source: bool                           = True
    newline_after_header: bool                  = True

class Printer:
    def __init__(self, options: Optional[Dict[AnnotationKind, PrintOpts]] = None):
        self._opts = {kind: PrintOpts() for kind in AnnotationKind}
        self._opts.update(options if options is not None else {})

    def print_diagnostic(self, diagnostic: Diagnostic) -> str:
        s = StringBuilder('\n\n')

        for annotation in diagnostic:
            s += self.print_annotation(annotation)

        return str(s)

    def print_annotation(self, annotation: Annotation) -> str:
        builder = StringBuilder('\n')
        opts = self._opts[annotation.kind]

        if opts.show_header:
            builder += self.print_header(annotation)

        if opts.newline_after_header:
            builder += ''

        if opts.show_source:
            builder += self.print_source(annotation)

        return str(builder)

    def print_header(self, annotation: Annotation) -> str:
        builder = StringBuilder(' ')
        builder += annotation.kind.name
        builder += f'({annotation.range}):'
        builder += annotation.message
        return str(builder)

    def print_source(self, annotation: Annotation) -> str:
        builder = StringBuilder('\n')
        line_nums_width = int(log10(max(annotation.range.line_numbers))) + 1

        for line in annotation.range.full_lines().each_line():
            builder += self.print_source_line(line, annotation.kind, line_nums_width)
        
            indicate = line & annotation.range
            if indicate is not None:
                builder += self.print_indicator_line(
                        indicate,
                        line,
                        annotation.kind,
                        line_nums_width)

        return str(builder)

    def print_source_line(self, line: Line, kind: AnnotationKind, line_nums_width: int) -> str:
        builder = StringBuilder()
        opts = self._opts[kind]

        # Left indent
        builder += ' ' * opts.source_indent_left

        # Line numbers
        if opts.source_show_line_nums:
            builder += str(line.line_number).rjust(line_nums_width)

        # Gutter
        if opts.source_show_gutter:
            builder += ' '
            builder += opts.source_gutter_char

        # Margin (between gutter and first source character)
        builder += ' ' * opts.source_margin

        # Now for the actual source
        builder += line.chars

        return str(builder)

    def print_indicator_line(
            self,
            indicate: Range,
            line: Line,
            kind: AnnotationKind,
            line_nums_width: int) -> str:
        
        builder = StringBuilder()
        opts = self._opts[kind]

        # Left indent
        builder += ' ' * opts.source_indent_left

        # Line number spaces (we don't display line numbers on indicator lines, just a gap)
        if opts.source_show_line_nums:
            builder += ''.rjust(line_nums_width)

        # Gutter
        if opts.source_show_gutter:
            builder += ' '
            builder += opts.source_gutter_char

        # Margin
        builder += ' ' * opts.source_margin

        # Now for the actual indicator line
        # Skip leading whitespace
        skip_count = 0
        if not self._opts[kind].source_indicate_leading_whitespace:
            for i,ch in enumerate(indicate.chars):
                if not ch.isspace():
                    skip_count = i
                    break

        builder += ' ' * skip_count
        builder += opts.source_indicate_char * (len(indicate) - skip_count)

        return str(builder)
