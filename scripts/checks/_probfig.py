"""_probfig.py — shared parser for the figs files scripts/render_figures.py emits.

Rendered figures live OUTSIDE the worksheet: the .tex only says \\probfig{N}
and the TikZ body sits in a generated figs file. Left alone, that indirection
blinds both figure lints — check_prose_consistency's figure-label check would
"pass" because it never sees a label, and check_layout's valued-figure
detection would miss the macro. Both checkers therefore expand \\probfig{N}
calls back into the text (via --figs) before checking, using this parser.

Stdlib-only on purpose: the checkers run without sympy.
"""

import re

# marker line render_figures.py writes before each macro definition
_MARKER_RE = re.compile(r"^% >>> probfig (\d+)\s*$", re.M)
CALL_RE = re.compile(r"\\probfig\{(\d+)\}")


def probfig_bodies(figs_tex):
    """{problem id -> the figure's center/tikzpicture block}.

    Only the center block is extracted — the \\csname wrapper and the
    provenance comment would otherwise leak digits (macro name, given echo)
    into number scans.
    """
    bodies = {}
    parts = _MARKER_RE.split(figs_tex)
    for n, chunk in zip(parts[1::2], parts[2::2]):
        m = re.search(r"\\begin\{center\}.*?\\end\{center\}", chunk, re.S)
        if m:
            bodies[int(n)] = m.group(0)
    return bodies


def expand_probfigs(tex, bodies):
    """Replace each \\probfig{N} call with its rendered body, in place — the
    call sits exactly where the figure prints, so expansion reconstructs the
    document the student sees. Returns (expanded_tex, sorted unresolved ids)."""
    unresolved = set()

    def sub(m):
        n = int(m.group(1))
        if n in bodies:
            return bodies[n]
        unresolved.add(n)
        return m.group(0)

    return CALL_RE.sub(sub, tex), sorted(unresolved)
