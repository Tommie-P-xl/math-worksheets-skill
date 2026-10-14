#!/usr/bin/env python3
r"""check_overprint.py — find text printing on top of other text, on the page.

Usage:
  check_overprint.py FILE.pdf [FILE.pdf ...]
  check_overprint.py --overlap 0.45 FILE.pdf     # tune the threshold
  check_overprint.py --quiet FILE.pdf            # only report faults

WHY THIS EXISTS
Everything else in this repository checks the SOURCE or the engine's LOG. Both
are blind to a whole class of fault, because TeX is perfectly happy to set two
things in the same place and says nothing: it has not overrun a line, it has not
run out of room, it has simply drawn one thing over another.

Three of those shipped in one eval run with completely clean logs — a running
head printing through the Name/Date blanks, three figure captions overprinting
after `xshift` was scaled along with its `tikzpicture`, and a grid drawn too
small to write on. Each was found by a person looking at a rendered page. This
finds the first two mechanically, by reading where the words actually landed.

WHAT IT DOES
`pdftotext -bbox` reports a box for every word on every page. Two boxes that
overlap substantially are two things drawn on top of each other. Words that sit
outside the page are text that ran off the paper.

WHAT IT DELIBERATELY DOES NOT DO
It cannot see a figure's GEOMETRY — a collision between two TikZ paths, or a
label lying across a drawn line, or a grid too small to use, leaves no word box
to overlap. It reads text only, so a clean report means "no text is
overprinted", not "the page is good". The remaining classes still need eyes.

WHAT IT DOES COVER INSIDE A FIGURE, stated precisely because the repository
has been telling authors otherwise. Every LABEL is text, so label-over-label
IS in scope wherever it happens — including at the swing apex of an
ambiguous-SSA triangle, which evals/AUTHORING.md lists as an ungated defect
bounded by "prefer A >= 30 degrees". Both halves of that are wrong, and both
were re-measured by rendering (see tests/test_overprint.py, SSA_MEASURED):

  A = 44 deg, a = 310, b = 400   the "?" arc label at B_2 lands on the "0" of
                                 the swing side's "a = 310" label. This gate
                                 reports it: '?' and '310' overlap by 54% of
                                 the smaller box — over the 0.45 prose
                                 threshold, so the ordinary rule catches it,
                                 not the narrow figure-label rule.

So the threshold does not bound the defect: 44 is comfortably above 30 and
collides anyway. What IS bounded is the OTHER geometry — at A = 15 and A = 25
(the cases AUTHORING.md confirmed by eye) the swing label lands on the BASE
LINE, a TikZ path, and this gate is correctly silent because there is no second
word box. Those two failures look identical on the page and are opposite here:
one is gated, one is invisible. Rendering a page and looking at it remains the
only cover for the second.

CALIBRATION
The threshold is overlap area as a fraction of the SMALLER box, so a subscript
brushing its base does not count while a title lying across a blank does. It was
calibrated against 450 PDFs this repository had already produced and gated, and
then confirmed against a document with a deliberate collision.

That single threshold is calibrated for TEXT OVER TEXT IN PROSE, where the
smaller box is a word and covering half of it is unmistakable. It is the wrong
number for a FIGURE LABEL, which is one or two characters: a `?` dropped on top
of a length digit hides the digit completely while covering only a fifth of the
box area, because most of a word box is the font's ascent and descent, not ink.
So there is a second, narrower rule for exactly that geometry — see
`stacked_label`. It is not a lower global threshold; a lower global threshold
would flag every subscript and radical in the corpus.

Exit 0 clean · 1 overprinting found · 2 harness error (no pdftotext, bad file).
"""
import argparse
import collections
import os
import re
import subprocess
import sys

WORD_RE = re.compile(
    r'<word xMin="([\d.eE+-]+)" yMin="([\d.eE+-]+)" '
    r'xMax="([\d.eE+-]+)" yMax="([\d.eE+-]+)">(.*?)</word>')
PAGE_RE = re.compile(r'<page width="([\d.eE+-]+)" height="([\d.eE+-]+)">')

# Overlap area as a fraction of the smaller box. Calibrated on 450 gated PDFs:
# ordinary mathematical typesetting (subscripts, accents, radicals over their
# argument, stacked fraction parts) produces overlaps well under this, while a
# title lying across an answer blank covers most of the smaller box.
OVERLAP = 0.45
# Boxes below this area are punctuation and single marks, where a few points of
# kerning is a large fraction of a small box and means nothing.
MIN_AREA = 4.0
# A word may extend this far past the page edge before it counts as running off
# — poppler occasionally reports a hair of overhang on a glyph's side bearing.
BLEED = 1.0
# Glyphs whose box is SUPPOSED to cover other text. A radical's box spans its
# whole vinculum, so it legitimately sits over everything under the bar; the
# same goes for an overline or a long-division tie. Comparing them against what
# they cover is asking whether a roof overlaps its house. Calibration: these
# were 293 of the 297 hits at a 0.45 threshold across 450 gated PDFs — noise
# that would have buried the four real faults underneath it.
OVERLAY_GLYPHS = {"\u221a", "\u203e", "\u0304", "\u00af", "\u2500", "\u2015"}
# Punctuation-only words: a dot leader or an ellipsis kerns into its neighbour,
# and a couple of points is a large fraction of a box that small.
PUNCT_ONLY = re.compile(r"^[.,;:\u00b7\u2026\-\u2013\u2014_]+$")

# ---------------------------------------------------------------- figure labels
# A second rule, for the one geometry the area threshold above cannot see: a
# short label printed on top of another short label inside a figure.
#
# Why the area threshold misses it. `pdftotext` reports a word's box as the
# font's full ascent-to-descent span, not its ink. A `?` and a `9` set at the
# same size, one dropped far enough onto the other that the `?`'s dot lands
# inside the digit, still share only ~30% of the smaller box \u2014 the rest of each
# box is empty leading. In prose that number means a graze; between two
# single-character labels it means the digit is unreadable.
#
# Why the answer is not a lower global threshold. Measured across the 900 PDFs
# in evals/runs, dropping the global number to 0.19 buries the page in
# subscripts, radical indices and fraction parts. The four conditions below
# separate the two populations instead, and each one is doing work:
#
#   LABEL_RE     Both words are short label tokens. Figure labels are a length,
#                an angle, a variable or a `?`. Requiring both sides to be one
#                is what keeps `\underbrace{..}_{lower bound}` out (poppler
#                reads the brace as a word and its label sits right under it).
#   STACK_HFRAC  They occupy the same column. This is the subscript test: a
#                subscript, a superscript and a degree mark sit BESIDE their
#                base and score ~0 here, because poppler starts the small
#                glyph's box exactly where the base's box ends.
#   STACK_VFRAC  Their boxes interpenetrate vertically by more than TeX's own
#                stacking ever produces. \frac and \dfrac place numerator and
#                denominator at fixed offsets from the maths axis, so the box
#                overlap they leave is a constant 0.22 of the box height at
#                every size in the corpus; the deepest innocent stack measured
#                anywhere in the 900 PDFs is 0.26. Real collisions measured
#                0.34 and 0.45. The threshold sits in the gap.
#   STACK_SIZE   Both boxes are the same height, i.e. the same font size. Every
#                mark TeX legitimately stacks over another is set SMALLER: the
#                index of a cube root, an accent, a script. This is the
#                condition that rejects the poppler radical artifact, where the
#                surd is mis-decoded as a word and its index overlaps it by
#                0.38 \u2014 the index is at script size, so the ratio is 0.69.
LABEL_RE = re.compile(r"^[A-Za-z0-9?]{1,3}$")
STACK_HFRAC = 0.55
STACK_VFRAC = 0.30
STACK_SIZE = 0.90


def words_by_page(pdf):
    """[(page_w, page_h, [(x0, y0, x1, y1, text), ...]), ...] via pdftotext."""
    try:
        r = subprocess.run(["pdftotext", "-bbox", pdf, "-"],
                           capture_output=True, text=True)
    except OSError as exc:
        raise RuntimeError(f"pdftotext unavailable: {exc}") from exc
    if r.returncode != 0:
        # Not our question. Whether a file is a readable PDF is owned by the
        # compile gates and check_log; the driver's own tests deliberately run
        # a stub engine that emits a placeholder, and failing here would make
        # this gate report a compile problem it is not equipped to diagnose.
        return None
    pages, cur = [], None
    for line in r.stdout.splitlines():
        pm = PAGE_RE.search(line)
        if pm:
            cur = (float(pm.group(1)), float(pm.group(2)), [])
            pages.append(cur)
            continue
        wm = WORD_RE.search(line)
        if wm and cur is not None:
            x0, y0, x1, y1 = (float(wm.group(i)) for i in range(1, 5))
            cur[2].append((x0, y0, x1, y1, wm.group(5)))
    return pages


def area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def overlap_fraction(a, b):
    """Intersection area as a fraction of the smaller box (0 when disjoint)."""
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    smaller = min(area(a), area(b))
    return (ix * iy) / smaller if smaller > 0 else 0.0


def is_overlay(text):
    """True when the word is a glyph designed to sit over other text."""
    return (not text.strip()
            or any(ch in OVERLAY_GLYPHS for ch in text)
            or bool(PUNCT_ONLY.match(text.strip())))


def composed_glyph(a, b):
    """Two single symbols stacked to build one character, not a collision.

    TeX composes several relations by piling one symbol on another — congruence
    is a tilde set over an equals sign, and poppler reports the two pieces as
    two words at the same place. They ARE at the same place; that is the glyph.
    The signature is two single non-alphanumeric marks sharing an x-extent, and
    no real collision looks like that: text-over-text always involves words.
    """
    ta, tb = a[4].strip(), b[4].strip()
    if len(ta) != 1 or len(tb) != 1 or ta.isalnum() or tb.isalnum():
        return False
    wa, wb = a[2] - a[0], b[2] - b[0]
    if min(wa, wb) <= 0:
        return False
    # same horizontal run, within a quarter of the narrower mark's width
    return (abs(a[0] - b[0]) < 0.25 * min(wa, wb)
            and abs(a[2] - b[2]) < 0.25 * min(wa, wb))


def _axis_fraction(lo_a, hi_a, lo_b, hi_b):
    """Overlap along one axis as a fraction of the shorter extent."""
    inter = min(hi_a, hi_b) - max(lo_a, lo_b)
    shorter = min(hi_a - lo_a, hi_b - lo_b)
    if inter <= 0 or shorter <= 0:
        return 0.0
    return inter / shorter


def stacked_label(a, b):
    """True when two short labels are printed one on top of the other.

    The figure-label rule described at the top of this file. It is deliberately
    narrow: same-size, short, both-alphanumeric-or-`?`, sharing a column, and
    interpenetrating deeper than TeX's own stacking. It answers a different
    question from `overlap_fraction` and is checked in addition to it, never
    instead of it.
    """
    ta, tb = a[4].strip(), b[4].strip()
    if not LABEL_RE.match(ta) or not LABEL_RE.match(tb):
        return False
    ha, hb = a[3] - a[1], b[3] - b[1]
    if ha <= 0 or hb <= 0 or min(ha, hb) / max(ha, hb) < STACK_SIZE:
        return False
    if _axis_fraction(a[0], a[2], b[0], b[2]) < STACK_HFRAC:
        return False
    return _axis_fraction(a[1], a[3], b[1], b[3]) >= STACK_VFRAC


def page_faults(page_w, page_h, words, threshold):
    """Overprinting pairs and off-page words on one page."""
    faults = []
    for x0, y0, x1, y1, text in words:
        if x0 < -BLEED or y0 < -BLEED or x1 > page_w + BLEED or y1 > page_h + BLEED:
            faults.append(("off-page", f"{text!r} at ({x0:.0f},{y0:.0f})-"
                                       f"({x1:.0f},{y1:.0f}) leaves the "
                                       f"{page_w:.0f}x{page_h:.0f} page"))
    # Sweep in reading order and only compare words that could share a line:
    # once a later word starts below this one's bottom, nothing after it can
    # overlap either, so the scan stays near-linear on ordinary pages.
    ordered = sorted(words, key=lambda w: (w[1], w[0]))
    for i, a in enumerate(ordered):
        if area(a[:4]) < MIN_AREA or is_overlay(a[4]):
            continue
        for b in ordered[i + 1:]:
            if b[1] >= a[3]:
                break
            if area(b[:4]) < MIN_AREA or is_overlay(b[4]):
                continue
            if composed_glyph(a, b):
                continue
            f = overlap_fraction(a[:4], b[:4])
            if f >= threshold:
                faults.append(("overprint",
                               f"{a[4]!r} and {b[4]!r} overlap by "
                               f"{f * 100:.0f}% of the smaller, at "
                               f"({a[0]:.0f},{a[1]:.0f})"))
            elif stacked_label(a, b):
                faults.append(("overprint",
                               f"{a[4]!r} is printed on top of {b[4]!r} — two "
                               f"labels of the same size stacked in one column, "
                               f"{f * 100:.0f}% of the smaller box, at "
                               f"({a[0]:.0f},{a[1]:.0f})"))
    return faults


def check(pdf, threshold, quiet):
    pages = words_by_page(pdf)
    if pages is None:
        if not quiet:
            print(f"  ·  {os.path.basename(pdf)}: not a readable PDF — skipped "
                  f"(the compile gates own that)")
        return 0
    total = 0
    for n, (w, h, words) in enumerate(pages, 1):
        faults = page_faults(w, h, words, threshold)
        total += len(faults)
        for kind, msg in faults:
            print(f"  ❌ {os.path.basename(pdf)} p{n} [{kind}] {msg}")
    if not total and not quiet:
        print(f"  ✅ {os.path.basename(pdf)}: {len(pages)} page(s), no text "
              f"printed over other text")
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--overlap", type=float, default=OVERLAP)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    faults = 0
    try:
        for pdf in a.pdfs:
            if not os.path.isfile(pdf):
                print(f"error: no such file: {pdf}", file=sys.stderr)
                return 2
            faults += check(pdf, a.overlap, a.quiet)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if faults:
        print(f"\n❌ {faults} overprinting/off-page fault(s). TeX reports none of "
              f"this:\n   drawing one thing over another is not an error to the "
              f"engine, only to a reader.")
        return 1
    if not a.quiet:
        print(f"\n✅ no overprinting in {len(a.pdfs)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
