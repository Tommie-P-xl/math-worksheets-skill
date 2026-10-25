#!/usr/bin/env python3
"""
render_figures.py — construct TikZ figures FROM the verify JSON, so a figure
can never disagree with the answer it illustrates.

Why this exists: charts already follow this rule (read_data's "the SAME data
feeds the pgfplots chart") but geometry figures were hand-drawn — the agent
solved the triangle by hand and retyped coordinates into TikZ. The shipped SSA
"swing" reference figure carried wrong hand-computed constants (9.24/3.05 for
the true 9.220/3.037), which is exactly the transcription drift verify.py
exists to kill. This script closes the gap by CONSTRUCTION: the same `given`
dict solve_triangle verifies is what places every vertex, so drawing and check
share one source of truth. Lints stay as belt-and-braces; construction is the
guarantee.

Usage: render_figures.py <verify_TOPIC_DATE.json> [out.tex]
Default output: figs_TOPIC_DATE.tex next to the input (verify_ prefix -> figs_,
matching the ws_/ak_/ss_ naming convention).

What renders:
  * every `type: "triangle"` problem — automatically, from its own `given`
    dict (opt-in marker `"figure": {"kind": "triangle"}` is allowed but adds
    nothing; values inside it are rejected by verify.py so the givens can
    never be duplicated). Ambiguous SSA emits the two-triangle swing figure
    with BOTH computed apexes.
  * problems carrying `"figure": {"kind": "right_triangle", "given":
    {two of a/b/c/A/B}, "solve_for": ..., "unknown": "x"}` — the right angle
    is at C. The renderer draws the figure object regardless of the problem's
    verification type (verify.py gates WHICH types may carry one — approx and
    eval); every figure value must appear as a literal in the problem's
    `expr` or among its `at` values (eval's write-the-ratio shape), which
    binds the drawing to the arithmetic the verifier checked.

Emitted file: one `% >>> probfig N` marker + macro per figured problem and a
single dispatcher `\\probfig{N}`. The worksheet `\\input`s the file and places
`\\probfig{N}` inside problem N's minipage. The markers are what lets
tests/check_prose_consistency.py and tests/check_layout.py splice the figure
bodies back in (--figs) so their figure rules stay sighted.

Figures are to scale: longest drawn side is normalized to ~4.5cm. Labels show
ONLY given values, plus "?" (or the declared unknown name) on solve_for —
never a computed answer. Output is ASCII-only so the pdflatex fallback
compiles it identically to tectonic.

Exit 0: figs file written. Exit 1: invalid input or an impossible figure —
no file is written, because a wrong figure is worse than no figure.
"""

import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import sympy
    from verify import (VerifyInputError, figure_bindable_numbers, parse_value,
                        solve_triangle, _OPP, _SIDE_OF)
except ModuleNotFoundError:
    # Same dependency story as run_verify.sh: the renderer deliberately reuses
    # verify.py's solver (one solver, one truth), which needs sympy.
    print("Error: sympy is not installed. render_figures.py shares verify.py's\n"
          "triangle solver so the figure and the check can never disagree —\n"
          "install it with:  pip3 install sympy", file=sys.stderr)
    sys.exit(1)


class FigureError(Exception):
    """A figure that must not render (impossible geometry, bad figure spec)."""


TARGET_CM = 4.5                    # longest drawn side after normalization
THIN_ANGLE = math.radians(25.0)    # thin-triangle rule, latex-templates.md
THIN_SIDE_CM = 2.0                 # (any angle < 25 deg or drawn side < 2cm)
# Two vertex labels closer than this share a footprint: a \small "$B_2$" box is
# about 0.5cm wide, so 1.0cm apart still touches once both carry a subscript.
# Measured, not guessed — below it the A/B_2 pair overprints, above it does not.
CROWDED_VERTEX_CM = 1.0
# How far a vertex letter stands off from its own vertex, along the outward
# angle bisector. Small on purpose: the label must still read as belonging to
# that vertex. 3pt is a hair over 1mm.
VERTEX_STANDOFF_PT = 3.0
RIGHT_TOL = math.radians(0.1)      # |angle - 90 deg| <= 0.1 deg -> square mark

# ── Label metrics, CALIBRATED from TeX rather than estimated ────────────────
# Placement decisions are made here, in Python, before LaTeX ever runs, so the
# widths cannot be asked for at typeset time. The previous attempt guessed them
# from a character count and was measured 44% under on a single letter, which
# made a box model useless: it computed clear paper exactly where the page had
# none. These numbers come from \settowidth on the shipped preamble at \small,
# the size every one of these labels is set at:
#
#     \settowidth{\l}{\small$C$}        ->  8.6094pt
#     \settowidth{\l}{\small$b = 26$}   -> 30.2493pt
#     \settowidth{\l}{\small$50^\circ$} -> 15.7001pt
#
# The structure is exactly linear — a digit is 5.475pt whether it stands alone
# or sits in "1234" — so the shapes this renderer emits ($X$, $X_n$, $x = N$,
# $N^\circ$, $?$) are reproduced to better than a tenth of a point. Checked
# against the rendered page: this model puts "b = 26" at 1.0632cm and
# pdftotext -bbox measures 1.063cm.
# tests/test_ssa_figure_labels.py re-derives them from a compile, so a preamble
# font change fails loudly instead of silently degrading the placement.
PT_CM = 0.0351459804                      # one TeX point in centimetres
_W_DIGIT = 5.475                          # any digit, at \small
_W_EQUALS = 14.6                          # " = " including both thick spaces
_W_DEGREE = 4.75                          # the ^\circ suffix
_W_SUBSCRIPT = 4.2                        # a subscript digit
_W_POINT = 3.04                           # a decimal point
_W_QUERY = 5.17                           # "?"
_W_LETTER = {"A": 8.21, "B": 8.86, "C": 8.61, "a": 5.79, "b": 4.70, "c": 4.74}
_W_LETTER_DEFAULT = 6.8                   # any other italic letter
_H_LINE = 7.6                             # cap height of every one of these


def label_extent_cm(text):
    """(half-width, half-height) in cm for a figure label, from TeX metrics.

    `text` is the node body as emitted, e.g. "$b = 26$" or "$B_2$".
    """
    body = text.strip("$")
    w = 0.0
    i = 0
    while i < len(body):
        ch = body[i]
        if body.startswith("^\\circ", i):
            w += _W_DEGREE
            i += 6
        elif body.startswith(" = ", i):
            w += _W_EQUALS
            i += 3
        elif ch == "_":
            w += _W_SUBSCRIPT
            i += 2                        # the subscript digit goes with it
        elif ch.isdigit():
            w += _W_DIGIT
            i += 1
        elif ch == ".":
            w += _W_POINT
            i += 1
        elif ch == "?":
            w += _W_QUERY
            i += 1
        elif ch.isalpha():
            w += _W_LETTER.get(ch, _W_LETTER_DEFAULT)
            i += 1
        else:
            i += 1                        # braces, backslashes, stray spaces
    return (w * PT_CM / 2.0, _H_LINE * PT_CM / 2.0)


def label_box(pos, text, out_dir):
    """Box centre and half-extents for a label anchored `out_dir` from pos.

    A TikZ node placed "above" sits with its lower edge on the point, so the
    centre is one half-extent along the outward direction.
    """
    hw, hh = label_extent_cm(text)
    ux, uy = out_dir if out_dir else (0.0, 0.0)
    return (pos[0] + ux * hw, pos[1] + uy * hh, hw, hh)


def box_gap(a, b):
    """Clear distance between two label boxes; negative when they overlap."""
    dx = abs(a[0] - b[0]) - (a[2] + b[2])
    dy = abs(a[1] - b[1]) - (a[3] + b[3])
    if dx < 0 and dy < 0:
        return max(dx, dy)
    return math.hypot(max(0.0, dx), max(0.0, dy))

# THE right-triangle labelling convention, shared with the shipped \rtfig and
# \refrt macros (templates/figure-macros.tex): the right angle sits at vertex
# C, so side c (= AB, opposite C) is the hypotenuse. A worksheet places the
# value-free \refrt reference figure beside renderer-built \probfig figures,
# so a disagreement here teaches students two contradictory labelings on one
# page. tests/test_figure_convention.py parses this assignment and the macros'
# "% right angle mark" lines and fails if they ever diverge — keep the
# constant, and route any convention change through both files at once.
RIGHT_ANGLE_VERTEX = "C"

# side x connects the two vertices whose angles are NOT _OPP[x]
_EDGES = {"a": ("B", "C"), "b": ("A", "C"), "c": ("A", "B")}

_ANCHOR_NAMES = ["right", "above right", "above", "above left",
                 "left", "below left", "below", "below right"]


# ── small numeric/TikZ helpers ────────────────────────────────────────────────

def _f(v):
    """JSON given -> float through verify.py's own parser (accepts "pi/3")."""
    return float(sympy.N(parse_value(v)))


def _fmt(x):
    # 4 decimals: coarser rounding (2-3dp) can shift a de-normalized side by
    # more than the 1e-3 the property test allows on long sides.
    return f"{x:.4f}"


def _pt(p):
    return f"({_fmt(p[0])},{_fmt(p[1])})"


def _unitv(x, y):
    n = math.hypot(x, y)
    return (x / n, y / n) if n else (0.0, 0.0)


def _anchor(x, y):
    """Map an outward direction to the nearest of the 8 TikZ anchors."""
    ang = math.degrees(math.atan2(y, x)) % 360.0
    return _ANCHOR_NAMES[int(((ang + 22.5) // 45) % 8)]


def _node(anchor, pos, text, thin, shift_dir=None, shift_pt=0.0):
    opts = [anchor, "fill=none"]
    if shift_dir is not None and shift_pt:
        # explicit xshift/yshift instead of positioning-library `below left=2pt`
        # syntax — the templates only load calc/angles/quotes
        opts.append(f"xshift={shift_dir[0] * shift_pt:.1f}pt")
        opts.append(f"yshift={shift_dir[1] * shift_pt:.1f}pt")
    if thin:
        opts.append("font=\\small")
    return "\\node[" + ", ".join(opts) + "] at " + _pt(pos) + " {" + text + "};"


def _pic(first, vertex, second, label, thin):
    opts = "draw, angle radius=7mm, angle eccentricity=1.6"
    if thin:
        opts += ", font=\\small"
    return ("\\pic [" + opts + ", \"" + label + "\"] {angle = "
            + first + "--" + vertex + "--" + second + "};")


def _arc_order(vpos, ray1, ray2):
    """Order two rays so the CCW sweep from first to second is the INTERIOR
    angle (TikZ `pic {angle=X--V--Y}` measures counterclockwise from V--X)."""
    (n1, p1), (n2, p2) = ray1, ray2
    a1 = math.atan2(p1[1] - vpos[1], p1[0] - vpos[0])
    a2 = math.atan2(p2[1] - vpos[1], p2[0] - vpos[0])
    if (a2 - a1) % (2 * math.pi) <= math.pi:
        return n1, n2
    return n2, n1


def _pic_at(vname, vpos, ray1, ray2, label, thin):
    first, second = _arc_order(vpos, ray1, ray2)
    return _pic(first, vname, second, label, thin)


def _right_mark(vpos, p1, p2, size=0.28):
    """Small square at a right-angle vertex, oriented along the two edges."""
    u1 = _unitv(p1[0] - vpos[0], p1[1] - vpos[1])
    u2 = _unitv(p2[0] - vpos[0], p2[1] - vpos[1])
    q1 = (vpos[0] + u1[0] * size, vpos[1] + u1[1] * size)
    q2 = (vpos[0] + (u1[0] + u2[0]) * size, vpos[1] + (u1[1] + u2[1]) * size)
    q3 = (vpos[0] + u2[0] * size, vpos[1] + u2[1] * size)
    return "\\draw " + _pt(q1) + " -- " + _pt(q2) + " -- " + _pt(q3) + ";"


def _disp(v):
    """Display a given exactly as the JSON wrote it (7, 6.5, "pi/3")."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _angle_label(v, unit):
    if unit == "deg":
        return "$" + _disp(v) + "^\\circ$"
    return "$" + str(v).replace("pi", "\\pi") + "$"


def _split_given(given, unit):
    to_rad = math.radians if unit == "deg" else float
    sides = {k: _f(given[k]) for k in "abc" if k in given}
    angles = {k: to_rad(_f(given[k])) for k in "ABC" if k in given}
    return sides, angles


# ── single-triangle emission ─────────────────────────────────────────────────
# Canonical placement (same as the SAS template): A at the origin, B on the
# x-axis at distance c, C = (b cos A, b sin A). All angles are in (0, 180) so
# C is always above the axis and A->B->C is counterclockwise.

def _single_lines(sol, side_labels, angle_marks):
    a, b, c = sol["a"], sol["b"], sol["c"]
    s = TARGET_CM / max(a, b, c)
    pts = {"A": (0.0, 0.0),
           "B": (c * s, 0.0),
           "C": (b * math.cos(sol["A"]) * s, b * math.sin(sol["A"]) * s)}
    thin = (min(sol["A"], sol["B"], sol["C"]) < THIN_ANGLE
            or min(a, b, c) * s < THIN_SIDE_CM)
    lines = [f"\\coordinate ({v}) at {_pt(pts[v])};" for v in "ABC"]
    lines.append("\\draw[thick] (A) -- (B) -- (C) -- cycle;")
    for v, mark in angle_marks.items():
        if mark and mark[0] == "right":
            o1, o2 = [o for o in "ABC" if o != v]
            lines.append(_right_mark(pts[v], pts[o1], pts[o2]))
    # vertex labels: anchored away from the centroid so they clear both edges
    cx = sum(p[0] for p in pts.values()) / 3.0
    cy = sum(p[1] for p in pts.values()) / 3.0
    for v in "ABC":
        d = _unitv(pts[v][0] - cx, pts[v][1] - cy)
        lines.append(_node(_anchor(*d), pts[v], "$" + v + "$", thin))
    # side labels: outward normal at the edge midpoint (templates' anchor rule);
    # thin triangles get an explicit 2pt outward shift
    for side, (v1, v2) in _EDGES.items():
        text = side_labels.get(side)
        if not text:
            continue
        mid = ((pts[v1][0] + pts[v2][0]) / 2.0, (pts[v1][1] + pts[v2][1]) / 2.0)
        ex, ey = pts[v2][0] - pts[v1][0], pts[v2][1] - pts[v1][1]
        nx, ny = -ey, ex
        third = pts[_OPP[side]]                     # interior lies toward it
        if nx * (mid[0] - third[0]) + ny * (mid[1] - third[1]) < 0:
            nx, ny = -nx, -ny
        nu = _unitv(nx, ny)
        lines.append(_node(_anchor(*nu), mid, text, thin,
                           shift_dir=nu, shift_pt=2.0 if thin else 0.0))
    for v, mark in angle_marks.items():
        if mark and mark[0] == "arc":
            o1, o2 = [o for o in "ABC" if o != v]
            first, second = _arc_order(pts[v], (o1, pts[o1]), (o2, pts[o2]))
            lines.append(_pic(first, v, second, mark[1], thin))
    return lines


# ── ambiguous-SSA swing emission ─────────────────────────────────────────────
# Shared parts of both triangles: the given angle's vertex P0, the given
# "other" side P0--F, and the swinging given side F--W. Only W moves: the base
# P0--W (the missing side) has two lengths. solve_triangle returns the acute
# second angle first, which always has the LONGER base — so W1 (solid) is the
# far apex and W2 (dashed) the near one, matching the reference figure.

def _swing_lines(sols, ang_name, opp, other, raw, unit, solve_fors):
    sol1, sol2 = sols
    w_ang = _OPP[other]                              # swing vertex's angle
    f_ang = ({"A", "B", "C"} - {ang_name, w_ang}).pop()
    base = _SIDE_OF[f_ang]                           # side with two lengths
    c1, c2 = sol1[base], sol2[base]
    other_len, opp_len, ang_v = sol1[other], sol1[opp], sol1[ang_name]
    s = TARGET_CM / max(c1, other_len, opp_len)
    p0 = (0.0, 0.0)
    w1 = (c1 * s, 0.0)
    w2 = (c2 * s, 0.0)
    fp = (other_len * math.cos(ang_v) * s, other_len * math.sin(ang_v) * s)
    n_p0, n_w1, n_w2, n_f = ang_name, w_ang + "1", w_ang + "2", f_ang
    drawn = [c1 * s, c2 * s, other_len * s, opp_len * s]
    all_angles = [sol[k] for sol in sols for k in "ABC"]
    thin = min(all_angles) < THIN_ANGLE or min(drawn) < THIN_SIDE_CM
    lines = [f"\\coordinate ({n_p0}) at {_pt(p0)};",
             f"\\coordinate ({n_w1}) at {_pt(w1)};",
             f"\\coordinate ({n_w2}) at {_pt(w2)};",
             f"\\coordinate ({n_f}) at {_pt(fp)};",
             f"\\draw[thick] ({n_p0}) -- ({n_w1}) -- ({n_f}) -- cycle;",
             f"\\draw[thick, dashed] ({n_f}) -- ({n_w2});"]
    # vertex labels (subscripts _1/_2 are point NAMES, not printed values)
    cx = (p0[0] + w1[0] + fp[0]) / 3.0
    cy = (p0[1] + w1[1] + fp[1]) / 3.0
    # A vertex label goes along the OUTWARD ANGLE BISECTOR of its own two
    # edges, which is the standard TikZ idiom for polygon labelling and is
    # strictly better than the direction-from-centroid this used to use.
    #
    # Centroid direction fails exactly where this figure lives. On a flat
    # triangle the centroid sits almost ON the base, so vertex A's outward
    # direction comes out nearly horizontal — pointing straight along the base
    # at B_2, the neighbour it most needs to avoid. The bisector cannot do
    # that: it points away from BOTH edges meeting at the vertex, so at a
    # spike it runs out along the spike's axis, away from everything.
    for name, text, pos, e1, e2 in ((n_p0, "$" + ang_name + "$", p0, w1, fp),
                                    (n_w1, "$" + w_ang + "_1$", w1, p0, fp),
                                    (n_f, "$" + f_ang + "$", fp, p0, w1)):
        u1 = _unitv(e1[0] - pos[0], e1[1] - pos[1])
        u2 = _unitv(e2[0] - pos[0], e2[1] - pos[1])
        d = _unitv(-(u1[0] + u2[0]), -(u1[1] + u2[1]))
        if d == (0.0, 0.0):          # degenerate: edges exactly opposed
            d = _unitv(pos[0] - cx, pos[1] - cy)
        # ...and stood off ALONG it, TikZ's `label distance`. The bisector is
        # what makes a stand-off safe: it is the one direction guaranteed to
        # lead away from both edges, so pushing along it cannot walk the label
        # into the figure. This is what actually separates "C" from the "b = N"
        # sharing the apex — the two were landing 0.6pt apart, which reads as
        # "b = 26C" and is far too small an overlap for the 45% gate to see.
        lines.append(_node(_anchor(*d), pos, text, thin,
                           shift_dir=d, shift_pt=VERTEX_STANDOFF_PT))
    # W2 sits ON the base inside the solid triangle — push its label clear.
    #
    # Clear of the BASE was the whole rule, and it is not enough: W2 slides
    # toward P0 as the triangle thins, and the direction-from-centroid anchor
    # then points its label down-LEFT, straight onto P0's own label. Swept over
    # 33 ambiguous-SSA geometries, "A and B overlap" fired in 10 of the 12
    # collisions — the single most common fault in the figure, and one no
    # amount of moving the SIDE labels can reach.
    #
    # So W2's label is pushed away from P0 along the base once the two vertices
    # are within a label's width of each other. Above that gap nothing changes,
    # which keeps every already-clean figure identical.
    gap = math.hypot(w2[0] - p0[0], w2[1] - p0[1])
    if gap < CROWDED_VERTEX_CM:
        away = 1.0 if w2[0] >= p0[0] else -1.0
        lines.append(_node(_anchor(away, -1.0), w2, "$" + w_ang + "_2$", thin,
                           shift_dir=(away, -1.0), shift_pt=6.0))
    else:
        d = _unitv(w2[0] - cx, w2[1] - cy)
        lines.append(_node(_anchor(*d), w2, "$" + w_ang + "_2$", thin,
                           shift_dir=(0.0, -1.0), shift_pt=2.0))

    def _side_node(p_from, p_to, frac, away_from, text, extra_shift=0.0):
        pos = (p_from[0] + frac * (p_to[0] - p_from[0]),
               p_from[1] + frac * (p_to[1] - p_from[1]))
        ex, ey = p_to[0] - p_from[0], p_to[1] - p_from[1]
        nx, ny = -ey, ex
        if nx * (pos[0] - away_from[0]) + ny * (pos[1] - away_from[1]) < 0:
            nx, ny = -nx, -ny
        nu = _unitv(nx, ny)
        shift = extra_shift if extra_shift else (7.0 if thin else 0.0)
        return _node(_anchor(*nu), pos, text, thin, shift_dir=nu, shift_pt=shift)

    # THE FIXED SIDE'S LABEL POSITION IS COMPUTED, NOT CHOSEN.
    #
    # It used to sit at a flat 0.55, picked because it cleared the arc labels
    # in the reference figure. It does not clear them in every valid triangle:
    # where W2 lands on the base, and where 0.55 of P0->F lands, both move with
    # the givens, and for some of them the "?" arc at W2 prints on top of
    # "b = N". An author probing ten SSA triangles found one collision, caught
    # only by check_overprint — the LaTeX log says nothing about two things
    # drawn in the same place. Their only lever was to change the givens, on a
    # topic whose entire point is this figure.
    #
    # A pic label's position is not a mystery: `angle radius=7mm,
    # angle eccentricity=1.6` puts it 1.12cm from the vertex along the
    # bisector of the two rays. So the arc labels can be located and the side
    # label placed where there is actually room.
    def _arc_label_pos(vertex, ray_a, ray_b, radius_cm=0.7 * 1.6):
        ua = _unitv(ray_a[0] - vertex[0], ray_a[1] - vertex[1])
        ub = _unitv(ray_b[0] - vertex[0], ray_b[1] - vertex[1])
        bis = _unitv(ua[0] + ub[0], ua[1] + ub[1])
        return (vertex[0] + bis[0] * radius_cm, vertex[1] + bis[1] * radius_cm)

    # (position, TEXT) — the text is what gives an obstacle its WIDTH, and the
    # angle value is the widest thing in the middle of the figure. Two of the
    # five collisions that survived the point-based pass were the angle label
    # against a side label, which a model without widths cannot even see.
    ang_text = _angle_label(raw[ang_name], unit)
    crowd = [(_arc_label_pos(p0, w1, fp), ang_text)]   # given angle, always drawn
    if w_ang in solve_fors:
        crowd.append((_arc_label_pos(w1, fp, p0), "$?$"))
        crowd.append((_arc_label_pos(w2, fp, p0), "$?$"))
    if f_ang in solve_fors:
        crowd.append((_arc_label_pos(fp, p0, w1), "$?$"))
    # THE VERTEX LABELS ARE IN THE CROWD TOO. They were not, and they are the
    # dominant collision: swept across 33 ambiguous-SSA geometries, 12 collide
    # and the causes are "C" on the fixed side's own label (A = 15, 20 — 63%
    # and 51% overlap), the two vertex labels A and B_2 on each other, and only
    # then the arc-on-swing-label case the docs describe. A label placed to
    # clear the arcs while ignoring the vertex letters is choosing between two
    # obstacles with one eye shut, which is the likeliest reason three previous
    # attempts at this moved the swing labels and made the count worse.
    crowd += [(p0, "$" + ang_name + "$"), (w1, "$" + w_ang + "_1$"),
              (w2, "$" + w_ang + "_2$"), (fp, "$" + f_ang + "$")]
    # Each obstacle as a BOX, offset outward the way its own node is anchored.
    crowd_boxes = [label_box(pos, text, _unitv(pos[0] - cx, pos[1] - cy))
                   for pos, text in crowd]

    def _outward(p_from, p_to, frac, away_from):
        """The position and normal _side_node will use — same maths, reused so
        the search scores exactly what the renderer is about to emit."""
        pos = (p_from[0] + frac * (p_to[0] - p_from[0]),
               p_from[1] + frac * (p_to[1] - p_from[1]))
        ex, ey = p_to[0] - p_from[0], p_to[1] - p_from[1]
        nx, ny = -ey, ex
        if nx * (pos[0] - away_from[0]) + ny * (pos[1] - away_from[1]) < 0:
            nx, ny = -nx, -ny
        return pos, _unitv(nx, ny)

    def _clear(p_from, p_to, frac, away_from, text, obstacles):
        pos, nu = _outward(p_from, p_to, frac, away_from)
        box = label_box(pos, text, nu)
        return min(box_gap(box, o) for o in obstacles)

    # 0.55 stays FIRST so every figure that was already clean is unchanged —
    # this only moves the label on the geometries where it was landing on
    # something. Candidates walk outward from there along the same side.
    CANDS = (0.55, 0.65, 0.45, 0.72, 0.38, 0.80, 0.30)
    ROOMY = 0.10                       # cm of clear paper: reads as two things
    fixed_text = "$" + other + " = " + _disp(raw[other]) + "$"
    fixed_frac = max(CANDS, key=lambda f: (
        _clear(p0, fp, f, w1, fixed_text, crowd_boxes) >= ROOMY,
        _clear(p0, fp, f, w1, fixed_text, crowd_boxes)))
    lines.append(_side_node(p0, fp, fixed_frac, w1, fixed_text))

    # Each label placed becomes an obstacle for the next. The swing labels sat
    # at flat fractions with nothing checked at all; they now search the same
    # candidates against everything already on the page, including the
    # fixed-side label and each other. Their default stays FIRST in the
    # candidate list, so a figure that was already clean does not move —
    # every previous attempt to place these regressed the count by moving them
    # unconditionally.
    pos, nu = _outward(p0, fp, fixed_frac, w1)
    placed = crowd_boxes + [label_box(pos, fixed_text, nu)]
    swing_text = "$" + opp + " = " + _disp(raw[opp]) + "$"
    for p_from, frac0, shift0 in ((w1, 0.45, 0.0), (w2, 0.30, 3.0)):
        frac = max((frac0,) + CANDS, key=lambda f: (
            _clear(p_from, fp, f, p0, swing_text, placed) >= ROOMY,
            _clear(p_from, fp, f, p0, swing_text, placed)))
        spos, snu = _outward(p_from, fp, frac, p0)
        shift = shift0 if shift0 else (7.0 if thin else 0.0)
        # SLIDING ALONG THE SIDE IS NOT ALWAYS AVAILABLE. On a flat triangle the
        # W2 side passes straight through the given angle's arc-label region, so
        # every candidate fraction overlaps it and the search above returns the
        # least-bad one — which still collides. Then the only free direction is
        # OFF the side, along the normal the label is already offset on. Escalate
        # that offset until the box clears, up to a bound past which the label
        # stops reading as belonging to its own side.
        while shift < 22.0:
            box = (spos[0] + snu[0] * shift * PT_CM,
                   spos[1] + snu[1] * shift * PT_CM)
            if min(box_gap(label_box(box, swing_text, snu), o)
                   for o in placed) >= ROOMY:
                break
            shift += 2.0
        lines.append(_side_node(p_from, fp, frac, p0, swing_text,
                                extra_shift=shift))
        placed.append(label_box((spos[0] + snu[0] * shift * PT_CM,
                                 spos[1] + snu[1] * shift * PT_CM),
                                swing_text, snu))
    if base in solve_fors:
        lines.append(_side_node(p0, w1, 0.5, fp, "$" + base + " = ?$"))
    lines.append(_pic_at(n_p0, p0, (n_w1, w1), (n_f, fp),
                         _angle_label(raw[ang_name], unit), thin))
    if w_ang in solve_fors:   # both candidate angles get the "?" arc
        lines.append(_pic_at(n_w1, w1, (n_f, fp), (n_p0, p0), "$?$", thin))
        lines.append(_pic_at(n_w2, w2, (n_f, fp), (n_p0, p0), "$?$", thin))
    if f_ang in solve_fors:   # only the solid triangle's apex angle
        lines.append(_pic_at(n_f, fp, (n_p0, p0), (n_w1, w1), "$?$", thin))
    return lines


# ── per-problem figure builders ──────────────────────────────────────────────

def _render_triangle_problem(pid, given, unit, solve_fors):
    sides, angles = _split_given(given, unit)
    sols = solve_triangle(sides, angles)
    if not sols:
        raise FigureError(
            f"problem {pid}: given {given} does not form a valid triangle "
            "(each side must be shorter than the other two combined, angles "
            "must leave room for a third). run_verify.sh fails this problem "
            "for the same reason — fix the JSON givens, then re-render.")
    side_labels, angle_marks = {}, {}
    for k in "abc":
        if k in given:
            side_labels[k] = "$" + k + " = " + _disp(given[k]) + "$"
        elif k in solve_fors:
            side_labels[k] = "$" + k + " = ?$"
    for k in "ABC":
        if k in given:
            # a square mark IS the printed value "90", so it replaces the arc
            angle_marks[k] = (("right",) if abs(angles[k] - math.pi / 2) <= RIGHT_TOL
                              else ("arc", _angle_label(given[k], unit)))
        elif k in solve_fors:
            angle_marks[k] = ("arc", "$?$")
    if len(sols) == 2:
        (ang_name,) = angles.keys()
        opp = _SIDE_OF[ang_name]
        other = (set(sides) - {opp}).pop()
        return _swing_lines(sols, ang_name, opp, other, given, unit, solve_fors)
    return _single_lines(sols[0], side_labels, angle_marks)


_RT_KEYS = {"kind", "given", "solve_for", "unknown"}


def _render_right_triangle_figure(pid, p):
    fig = p["figure"]
    extra = set(fig) - _RT_KEYS
    if extra:
        raise FigureError(
            f"problem {pid}: figure has unknown field(s) {sorted(extra)} — "
            f"allowed: {sorted(_RT_KEYS)}")
    given = fig.get("given")
    if (not isinstance(given, dict) or len(given) != 2
            or set(given) - {"a", "b", "c", "A", "B"}):
        raise FigureError(
            f"problem {pid}: right_triangle 'given' must be an object with "
            "exactly two of a/b/c/A/B (the right angle C is implied), e.g. "
            '{"b": 9, "A": 35}')
    for k, v in given.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise FigureError(
                f"problem {pid}: figure given {k!r} must be a number "
                "(it must also appear literally in 'expr')")
    solve_for = fig.get("solve_for")
    if solve_for not in {"a", "b", "c", "A", "B"} or solve_for in given:
        raise FigureError(
            f"problem {pid}: figure 'solve_for' must be one of a/b/c/A/B "
            "and not already given")
    unknown = fig.get("unknown", "?")
    if not isinstance(unknown, str) or not re.fullmatch(r"[A-Za-z?]{1,3}", unknown):
        raise FigureError(
            f"problem {pid}: figure 'unknown' must be a short letter name "
            'like "x" (it is typeset in math mode)')
    expr = p.get("expr")
    if not isinstance(expr, str):
        raise FigureError(
            f"problem {pid}: a right_triangle figure needs the problem's "
            "'expr' (approx/eval types) to bind the drawing to the checked "
            "arithmetic")
    # the figure <-> check binding: construction makes the drawing internally
    # consistent, but only a match against the numbers the check used ('expr'
    # literals plus 'at' values — verify.figure_bindable_numbers, one source
    # for gate and renderer) ties it to what verify.py verified
    checked_nums = figure_bindable_numbers(p)
    for k, v in given.items():
        if float(v) not in checked_nums:
            raise FigureError(
                f"problem {pid}: figure value {k}={_disp(v)} does not appear "
                f"in expr {expr!r} or its 'at' values — the figure would show "
                "a number the verifier never checked. Use the same numbers "
                "in both.")
    sides = {k: float(given[k]) for k in "abc" if k in given}
    angles = {k: math.radians(float(given[k])) for k in "AB" if k in given}
    angles[RIGHT_ANGLE_VERTEX] = math.pi / 2
    sols = solve_triangle(sides, angles)
    if not sols:
        raise FigureError(
            f"problem {pid}: figure givens {given} do not form a right "
            "triangle (a leg cannot exceed the hypotenuse; A + B must be "
            "90 degrees). Fix the figure givens.")
    side_labels, angle_marks = {}, {RIGHT_ANGLE_VERTEX: ("right",)}
    for k in "abc":
        if k in given:
            side_labels[k] = "$" + _disp(given[k]) + "$"
        elif k == solve_for:
            side_labels[k] = "$" + unknown + "$"
    for k in "AB":
        if k in given:
            angle_marks[k] = ("arc", _angle_label(given[k], "deg"))
        elif k == solve_for:
            angle_marks[k] = ("arc", "$" + unknown + "$")
    return _single_lines(sols[0], side_labels, angle_marks)


# ── assembly ─────────────────────────────────────────────────────────────────

def build_figures(problems):
    """Returns (figures, errors): figures = [(pid, comment, lines)]."""
    errors = []
    tri = {}       # pid -> {"given", "unit", "solve_fors"}
    rt = {}        # pid -> problem dict
    for p in problems:
        if not isinstance(p, dict):
            continue
        pid = p.get("id")
        if p.get("type") == "triangle":
            entry = tri.get(pid)
            if entry is None:
                tri[pid] = {"given": p.get("given"), "unit": p.get("unit", "deg"),
                            "solve_fors": {p.get("solve_for")}}
            elif (entry["given"] != p.get("given")
                  or entry["unit"] != p.get("unit", "deg")):
                # one \probfig{N} per problem; two different triangles under
                # one id cannot share a figure
                errors.append(
                    f"problem {pid}: two triangle checks with DIFFERENT givens "
                    "share this id — one figure cannot show both. Split them "
                    "into separate problem ids.")
            else:
                entry["solve_fors"].add(p.get("solve_for"))
        elif isinstance(p.get("figure"), dict):
            kind = p["figure"].get("kind")
            if kind == "triangle":
                continue     # opt-in marker on a triangle problem; no-op here
            if kind != "right_triangle":
                errors.append(
                    f"problem {pid}: unknown figure kind {kind!r} — this renderer supports "
                    "'triangle' (automatic) and 'right_triangle'. Other shapes "
                    "keep using the hand-built templates in "
                    "references/latex-templates.md.")
                continue
            if pid in rt or pid in tri:
                errors.append(f"problem {pid}: more than one figure for this id")
                continue
            rt[pid] = p
    figures = []
    for pid, entry in tri.items():
        if pid in rt:
            errors.append(f"problem {pid}: more than one figure for this id")
            continue
        try:
            lines = _render_triangle_problem(pid, entry["given"], entry["unit"],
                                             entry["solve_fors"])
            comment = (f"triangle from verify JSON given {entry['given']} "
                       f"(unit {entry['unit']}) -- solve_for "
                       f"{sorted(str(x) for x in entry['solve_fors'])}")
            figures.append((pid, comment, lines))
        except (FigureError, VerifyInputError) as e:
            errors.append(str(e) if isinstance(e, FigureError)
                          else f"problem {pid}: {e} — run_verify.sh rejects "
                               "this problem too; fix the JSON first.")
    for pid, p in rt.items():
        try:
            lines = _render_right_triangle_figure(pid, p)
            comment = (f"right_triangle figure {p['figure'].get('given')} -- "
                       f"solve_for {p['figure'].get('solve_for')}, values "
                       "literal-checked against expr")
            figures.append((pid, comment, lines))
        except (FigureError, VerifyInputError) as e:
            errors.append(str(e) if isinstance(e, FigureError)
                          else f"problem {pid}: {e}")
    figures.sort(key=lambda f: (f[0] is None, f[0]))
    return figures, errors


def _wrap(pid, comment, lines):
    body = "\n".join("  " + ln for ln in lines)
    return (f"% >>> probfig {pid}\n"
            f"% {comment}\n"
            f"\\expandafter\\newcommand\\csname probfig{pid}\\endcsname{{%\n"
            "\\begin{center}\n\\begin{tikzpicture}\n"
            + body +
            "\n\\end{tikzpicture}\n\\end{center}%\n}\n")


def default_out_path(json_path):
    base = os.path.basename(json_path)
    stem = base[:-5] if base.endswith(".json") else base
    if stem.startswith("verify_"):
        stem = stem[len("verify_"):]
    return os.path.join(os.path.dirname(json_path) or ".", f"figs_{stem}.tex")


def main(argv):
    if len(argv) not in (1, 2) or argv[0] in ("-h", "--help"):
        print("Usage: render_figures.py <verify_TOPIC_DATE.json> [out.tex]\n"
              "Renders \\probfig{N} TikZ macros from the SAME givens verify.py "
              "checks.", file=sys.stderr)
        return 1
    json_path = argv[0]
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"❌ Could not read {json_path}: {e}", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not isinstance(data.get("problems"), list):
        print("❌ Not a verify file: expected an object with a 'problems' "
              "list (the same JSON run_verify.sh takes).", file=sys.stderr)
        return 1
    out_path = argv[1] if len(argv) == 2 else default_out_path(json_path)
    figures, errors = build_figures(data["problems"])
    if errors:
        for e in errors:
            print(f"❌ {e}", file=sys.stderr)
        print("\nNo figs file was written — a wrong figure is worse than no "
              "figure.", file=sys.stderr)
        return 1
    src = os.path.basename(json_path)
    # The figs file itself stays ASCII-only (latex-templates.md's engine rule:
    # pdflatex, the fallback, cannot typeset literal Unicode).
    header = (
        "% Generated by scripts/render_figures.py -- DO NOT EDIT BY HAND.\n"
        f"% Source of truth: {src}. Every coordinate and label below is\n"
        "% computed from the SAME 'given' values verify.py checks, so the\n"
        "% drawing cannot disagree with the answer key. Regenerate after ANY\n"
        f"% change to the JSON:  python3 scripts/render_figures.py {src}\n"
        "% Worksheet usage: \\input this file after \\begin{document}, then\n"
        "% put \\probfig{N} inside problem N's minipage.\n"
        "\\newcommand{\\probfig}[1]{\\csname probfig#1\\endcsname}\n")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)
        for pid, comment, lines in figures:
            f.write(_wrap(pid, comment, lines))
    if figures:
        ids = ", ".join(str(pid) for pid, _, _ in figures)
        print(f"✅ {len(figures)} figure(s) → {out_path} (problems: {ids})")
    else:
        print(f"✅ no triangle/right_triangle figures in {src} — wrote an "
              f"empty figs shell to {out_path} (safe to \\input)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
