#!/usr/bin/env python3
r"""_units.py — shared unit lexicon + LaTeX token matching for the unit gates.

One module used by BOTH unit checkers (check_answer_key.py's key-side gate and
check_answer_line.py's sheet-side gate), for the same reason _tex_segments.py
exists: two hand-rolled matchers would drift apart and disagree about what
counts as a printed unit.

Matching is token-SEQUENCE containment, never substring: "undefined" is one
token and can never satisfy "in" the inch, and \text{ or } contains no lexicon
token at all — so the connective in \boxed{x = 2 \text{ or } x = 3} is clean
by construction, not by special-casing.

The lexicon is CLOSED on purpose. Flagging every \text{} would false-fail
legitimate prose inside boxes; a unit gate should only fire on something that
is unambiguously a unit.

Documented limitation: PREFIX currency symbols ($5, \$) are out of scope —
the dollar sign doubles as the math delimiter and cannot be token-matched
safely. Write "in dollars" in the problem stem instead of declaring a
currency answer_unit.
"""
import re

UNIT_LEXICON = [
    "ft", "feet", "m", "meters", "metres", "cm", "mm", "km", "in", "inches",
    "mi", "miles", "yd", "yards", "s", "sec", "seconds", "min", "minutes",
    "hr", "hours", "mph", "km/h", "m/s", "ft/s", "units", "square units",
    "cubic units", "cm^2", "m^2", "km^2", "ft^2", "in^2", "mi^2",
    "cm^3", "m^3", "ft^3", "L", "mL", "g", "kg", "lb", "lbs", "oz",
    "degrees", "deg",
]

_TOKEN_RE = re.compile(r"\\[a-zA-Z]+|[A-Za-z]+|\^|\d+|\S")
# Wrapper/formatting tokens dropped before sequence matching, so \text{ft},
# {\,ft}, cm$^2$ and \mathrm{ft} all reduce to the same core sequence.
# ("\\" + ",") is the tokenized form of the thin space \, .
_WRAPPERS = {"\\text", "\\mathrm", "{", "}", "$", "\\", ","}
# Longest real unit label in the lexicon is two words ("sq ft", "cubic cm").
_MAX_UNIT_WORDS = 2


def tokenize(s):
    return _TOKEN_RE.findall(s)


def _core(tokens):
    return [t for t in tokens if t not in _WRAPPERS]


def _contains(hay, needle):
    n = len(needle)
    return n > 0 and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def unit_in(text, unit):
    r"""Does `text` print `unit`? Core-token-sequence containment, plus the
    angle alias: a declared deg/degrees is also satisfied by ^\circ."""
    hay = _core(tokenize(text))
    if _contains(hay, _core(tokenize(unit))):
        return True
    if unit in ("deg", "degrees"):
        return _contains(hay, ["^", "\\circ"])
    return False


def same_unit(a, b):
    """Unit-name equivalence for declared-vs-printed filtering (deg alias)."""
    return a == b or {a, b} <= {"deg", "degrees"}


# lexicon entries by descending token length, so the longest match wins:
# "square units" is found as ONE unit, never as a bare trailing "units"
_LEX_SEQS = sorted(((_core(tokenize(u)), u) for u in UNIT_LEXICON),
                   key=lambda t: -len(t[0]))


def undeclared_units(text, expected_strings, declared=()):
    r"""Lexicon units printed in \text{}/\mathrm{} inside `text` that are
    neither declared as an answer_unit nor part of a JSON expected string.

    The declared filter is token-aware in both directions: \text{cm}^2 against
    a declared "cm^2" finds only "cm" inside the \text, and "cm" being a
    contiguous sub-sequence of the declared unit's tokens makes it declared,
    not decoration. The expected-string filter keeps \ans{\text{undefined}}
    clean when expected is "undefined".
    """
    found = set()
    for m in re.finditer(r"\\(?:text|mathrm)\{([^{}]*)\}", text):
        body = m.group(1)
        # \text{} carrying a SENTENCE is prose, not a unit declaration. An
        # answer reading "2 \text{ marbles in the last box}" was failed for an
        # undeclared inch, because "in" is a lexicon token. A unit label is one
        # or two words ("cm", "sq ft"); anything longer is the author writing
        # English, and scanning it produces false failures on exactly the
        # plain-language answers elementary sheets are made of.
        if len(body.split()) > _MAX_UNIT_WORDS:
            continue
        toks = _core(tokenize(body))
        i = 0
        while i < len(toks):
            hit = None
            for seq, unit in _LEX_SEQS:
                if toks[i:i + len(seq)] == seq:
                    hit = (unit, len(seq))
                    break
            if hit:
                found.add(hit[0])
                i += hit[1]
            else:
                i += 1
    return sorted(
        u for u in found
        if not any(same_unit(u, d)
                   or _contains(_core(tokenize(d)), _core(tokenize(u)))
                   for d in declared)
        and not any(u in s for s in expected_strings))
