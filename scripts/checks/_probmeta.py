"""_probmeta.py — shared parser for the meta files scripts/render_meta.py emits.

The effort markers live OUTSIDE the worksheet: the .tex only says
\\probmeta{N} or \\probpts{N} and the rendered bodies sit in a generated meta
file, exactly like \\probfig and its figs file. This parser gives
check_prose_consistency.py sight of which problem ids actually have bodies
(--meta), so an unresolved or stale call is a loud failure, never a silent
pass. Stdlib-only on purpose: the checkers run without sympy.

Unlike _probfig, bodies are never spliced back into the text — a marker
prints digits ("(3 pts)") that must stay OUT of the prose-number scan, so
callers strip the calls instead.
"""

import re

# marker line render_meta.py writes before each body pair
_MARKER_RE = re.compile(r"^% >>> probmeta (\d+)\s*$", re.M)
META_CALL_RE = re.compile(r"\\probmeta\{(\d+)\}")
PTS_CALL_RE = re.compile(r"\\probpts\{(\d+)\}")


def probmeta_ids(meta_tex):
    """The set of problem ids the meta file defines bodies for."""
    return {int(n) for n in _MARKER_RE.findall(meta_tex)}
