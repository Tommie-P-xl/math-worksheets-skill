#!/usr/bin/env python3
"""
check_prose_consistency.py — flag numbers in worksheet prose that don't appear
as givens in the verify JSON (the word-problem analog of the figure rule).

Usage: python3 tests/check_prose_consistency.py <worksheet.tex> <verify.json>
                [--figs <figs.tex>] [--meta <meta.tex>]

Recognized shapes: \\problem{...} blocks, an enumerate/\\item list, or
examplebox/tryitbox environments (study guides — the ss path binds each box's
prose givens to its positional verify_ss entry). Blocks match verify-JSON
entries by order (block i ↔ i-th JSON id). Heuristic by design — a report for
graders and generators, not a hard gate. Exit 0 always unless files are
unreadable, the parse comes up empty, \\probfig{N} figures cannot be
resolved (pass the figs file scripts/render_figures.py emitted via --figs, or
the figure check runs blind), a problem embeds \\includegraphics (an image
this check can never bind to the JSON — see includegraphics_problems), or the
effort markers fail their binding (below).

Study-guide noise control: worked examples print INTERMEDIATE values by
design (10(0.642788)...), so a flagged prose token with >= 2 decimal places
is auto-matched when it equals a SymPy subexpression of the entry's own
approx expr at the token's printed precision. The >= 2-decimals guard keeps
integer drift (a changed given) from being masked by nearby subexpression
values. Story numbers unused by the computation remain expected flags.

Effort markers (\\probmeta{N} stars / \\probpts{N} point values) are
CONSTRUCTED by scripts/render_meta.py from the verified difficulty tags, so
the only residue to lint is placement — and that residue is hard (exit 2):
  * an unresolved call (no --meta, stale meta, or a tag gap) is an UNCHECKED
    marker, mirroring the \\probfig rule;
  * markers are all-or-nothing and index-bound: if any call appears, problem
    block i must contain exactly its own \\probmeta{i} (or \\probpts{i}),
    one mode for the whole document — swapped, duplicated, missing, or
    mixed-mode calls fail naming the blocks;
  * hand-typed literals (\\bigstar, the unicode star, "(3 pts)") are banned
    unconditionally — markers come from the verified JSON or not at all,
    the same rule hand-drawn valued figures already follow.
"""

import json
import os
import re
import sys

from _probfig import CALL_RE, expand_probfigs, probfig_bodies
from _probmeta import META_CALL_RE, PTS_CALL_RE, probmeta_ids
from _tex_segments import _item_spans, blank_comments, box_spans

NUM_RE = re.compile(r"\d+(?:\.\d+)?|\.\d+")


def item_blocks(tex):
    """Extract each top-level \\item body across every outermost enumerate.

    The shipped worksheet templates use enumerate/\\item rather than the
    \\problem{...} macro, so a generator that follows the templates produced
    ZERO parsed blocks here and the report still said "all consistent".
    Parsing both shapes is what makes this checker apply to real worksheets.

    Depth-aware via _tex_segments._item_spans: a nested part-list's content
    stays INSIDE its parent problem's block (the parts' numbers belong to
    problem i's JSON entry), where the old non-greedy regex ended the outer
    list at the first nested \\end{enumerate} — nested parts were promoted to
    top-level problems and every real problem after them was never checked.
    Comments are blanked (length-preserving) before the walk, so a
    commented-out \\item can neither split a block nor leak numbers.
    """
    btex = blank_comments(tex)
    blocks = []
    for s, e in _item_spans(btex) or []:
        body = re.sub(r"^\\item\b", "", btex[s:e]).strip()
        if body:
            blocks.append(body)
    return blocks


def problem_blocks(tex):
    """Extract the stem of each \\problem{...} / \\problem[5cm]{...} handling
    nested braces. The macro takes the workspace as an optional first argument
    (see references/latex-templates.md); matching it here — m.end() lands just
    inside the stem's brace — keeps this binder aligned with the template, or
    a sheet using the optional arg would silently parse zero blocks."""
    blocks = []
    for m in re.finditer(r"\\problem(?:\[[^\]]*\])?\{", tex):
        i, depth, buf = m.end(), 1, []
        while i < len(tex) and depth:
            c = tex[i]
            depth += (c == "{") - (c == "}")
            if depth:
                buf.append(c)
            i += 1
        blocks.append("".join(buf))
    return blocks


def examplebox_blocks(tex):
    """Study-guide shape: one block per examplebox/tryitbox body, in document
    order (positional binding, like check_answer_key). Comments are blanked
    so a commented-out box cannot become a phantom block."""
    spans = box_spans(tex)
    if spans is None:
        return []
    blanked = blank_comments(tex)
    return [blanked[a:b] for a, b, _ in spans]


def _prose_stripped(block):
    # drop TikZ coordinates (not human-visible), but keep figure LABELS —
    # see figure_label_numbers, which is checked separately (CASE-21)
    block = re.sub(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", "", block,
                   flags=re.S)
    # drop \probfig{N} calls — the braced arg is a problem INDEX, not a prose
    # value, and would otherwise be flagged as "missing from JSON" noise
    block = re.sub(r"\\probfig\{\d+\}", "", block)
    # drop \probmeta{N}/\probpts{N} the same way — their bodies print digits
    # ("(3 pts)") that are metadata, never prose values, so calls are
    # STRIPPED rather than spliced (the opposite of the figs treatment)
    block = re.sub(r"\\prob(?:meta|pts)\{\d+\}", "", block)
    # drop \answerline unit arguments — "cm$^2$" would otherwise inject a
    # phantom 2 into the scan (the unit itself is gated by check_answer_line)
    block = re.sub(r"\\answerline\{[^{}]*\}", "", block)
    # drop spacing/format macro arguments like \hspace{4.5cm}, \vspace{5cm}.
    # The STARRED forms count too: \vspace*{4.5cm} is the correct spelling
    # inside a \problem minipage (the unstarred one is discarded at a page
    # break), and without the star here every such stem leaked its dimension
    # into the prose scan — one eval sheet reported 0 of 4 givens matched
    # purely because it had used the layout-correct macro. The checker must not
    # punish the spelling the layout gate requires.
    # A SECOND braced dimension counts too: \rule{1.6cm}{0pt} leaked its 0pt
    # thickness into the scan as a phantom 0, which is how you build a table
    # cell spacer. Only the first argument was consumed.
    block = re.sub(r"\\[a-zA-Z]+\*?\{[\d.]+[a-z]{2}\}(?:\{[\d.]+[a-z]{2}\})?",
                   "", block)
    # drop the tryitbox furniture the templates mandate: \rotatebox{180}'s
    # angle argument and \\[2pt]-style line glue are markup, not prose values
    # — without this every try-it box false-flags 180 and 2, training the
    # reader to ignore the one report line that carries real drift
    # A thousands separator is punctuation inside ONE numeral. Without this,
    # "47{,}308" scanned as two numbers, 47 and 308, neither of which is a
    # given — so a grade 4-5 place-value worksheet reported 15.4% matched and
    # could not have detected a real mistyped number anywhere on the sheet. The
    # checker was blind on the whole band. check_answer_key.normalize_latex_
    # numbers has stripped both spellings all along; only this side was missing
    # them, and an author found it by rewriting the same stems without
    # separators and watching the rate go from 15.4% to 84.6%.
    # A dimension can be a FRACTION OF A LENGTH, not just "7.2cm": the
    # two-column figure-beside-questions idiom writes
    # \begin{minipage}[t]{0.50\linewidth}, and \rule{\linewidth}{0.4pt} puts
    # its thickness in the SECOND argument with a length macro in the first.
    # Both leaked on nearly every elementary sheet — one scored 42.1% until the
    # author hoisted the width into a \newlength and swapped in \hrulefill,
    # after which the identical content scored 100%.
    block = re.sub(r"\{\s*[\d.]+\s*\\[a-zA-Z]+\s*\}", "{}", block)
    block = re.sub(r"\\rule\s*(?:\[[^\]]*\])?\{[^{}]*\}\{[^{}]*\}", "", block)
    block = re.sub(r"(?<=\d)\{,\}(?=\d{3})", "", block)
    block = re.sub(r"(?<=\d),(?=\d{3})", "", block)
    block = re.sub(r"\\rotatebox\s*\{[\d.]+\}", "", block)
    # enumitem OPTION LENGTHS: \begin{itemize}[leftmargin=1.1cm, itemsep=2pt].
    # Same leak as the braced dimensions above, from a far more ordinary
    # construct — a sub-part list inside a stem. Three separate eval authors
    # reported it independently; on one sheet it alone moved the reported match
    # rate from 73.5% to 90.0%, and on another from 56.4% to 100%. A checker
    # that cries wolf on standard list formatting trains its reader to skim,
    # which costs more than the numbers it was protecting. Only key=LENGTH
    # pairs are dropped: a bare bracketed number stays visible, because
    # \item[3] prints a 3 the student reads.
    block = re.sub(r"\[[^\[\]]*=[^\[\]]*\]",
                   lambda m: "[]" if re.search(r"=\s*[-\d.]", m.group(0))
                   else m.group(0), block)
    block = re.sub(r"\\\\\[[\d.]+[a-z]{2}\]", "", block)
    # Inverse-function notation is a NAME, not a number. $f^{-1}(x)$ put a
    # phantom 1 into every stem on an inverses sheet — six of ten problems on
    # one, flagged as "missing from JSON" against a topic where the notation is
    # not optional. Only the -1 exponent is stripped: a general exponent can be
    # a printed given (the 2 in "a square of side 3 has area $3^2$"), so
    # removing all of them would hide real drift.
    block = re.sub(r"\^\s*\{\s*-\s*1\s*\}", "", block)
    return block


def prose_numbers(block):
    return {float(n) for n in NUM_RE.findall(_prose_stripped(block))}


def _approx_subexpr_values(entries):
    """Float value of every SymPy subexpression of each approx entry's expr —
    the values a worked example legitimately prints as intermediate steps
    (sin(40*pi/180) → 0.642788…). Parsed with verify.safe_parse (the
    sandboxed allowlist parser); anything unparseable or symbolic simply
    contributes nothing, so suppression degrades to 'no suppression'."""
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".."))
        import sympy
        import verify
    except ImportError:
        return []
    vals = []
    for e in entries:
        if e.get("type") != "approx" or not isinstance(e.get("expr"), str):
            continue
        try:
            parsed = verify.safe_parse(e["expr"])
        except Exception:
            continue
        for sub in sympy.preorder_traversal(parsed):
            try:
                vals.append(float(sympy.N(sub, 15)))
            except Exception:
                pass
    return vals


def suppress_intermediates(block, missing, entries):
    """Split `missing` into (still_missing, suppressed): a flagged value is
    suppressed only when its printed token has >= 2 decimal places AND equals
    a subexpression of the entry's own approx expr rounded to that printed
    precision. The decimals guard is load-bearing: a drifted integer given
    (c=12) must never be masked by a nearby subexpression value."""
    if not missing:
        return missing, []
    tokens = NUM_RE.findall(_prose_stripped(block))
    vals = None  # computed lazily: sympy costs ~1s and most blocks need none
    still, suppressed = [], []
    for p in missing:
        toks = [t for t in tokens
                if "." in t and len(t.split(".")[-1]) >= 2]
        toks = [t for t in toks if float(t) == p]
        hit = False
        for t in toks:
            d = len(t.split(".")[-1])
            if vals is None:
                vals = _approx_subexpr_values(entries)
            if any(abs(round(v, d) - float(t)) < 1e-9 for v in vals):
                hit = True
                break
        (suppressed if hit else still).append(p)
    return still, suppressed


def figure_label_numbers(block):
    """Numbers printed in figure LABELS — \\node[...]{...} text and pic "..."
    quotes. These are the human-visible figure values that must come from the
    JSON (audit 3d: previously the whole tikzpicture was stripped, so a figure
    labeled with a wrong side length was never checked). Excludes coordinates."""
    nums = set()
    # The label is the LAST braced group of the \node, not the first. The old
    # pattern stopped its option scan at the first "{", which on
    # "\node[below] at (\v,{0.32*\i}) {$7$}" is the braced COORDINATE — so the
    # coordinate arithmetic was read as the label and 0.32 was reported as a
    # printed figure value on all ten problems of one sheet. Any computed tikz
    # coordinate hits this.
    for m in re.finditer(r"\\node\b((?:[^;{]|\{[^{}]*\})*)\{"
                         r"([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", block):
        label = m.group(2)
        # A MIXED NUMBER IS ONE VALUE, and the frac rewrite below turns
        # "1\tfrac{1}{2}" into "11/2" — which NUM_RE, having no division
        # branch here, then reads as 11. Every grade-4/5 line plot with
        # half-unit ticks false-flagged a figure value of 11 that appears
        # nowhere in the document. check_answer_key has carried a _MIXED rule
        # for exactly this since the same bug bit the answer-key side; this
        # detector never got one. Handled BEFORE the frac rewrite so the whole
        # part is consumed with its fraction rather than left beside it.
        # ...and the value is offered ALONGSIDE the parts, not instead of them,
        # because the JSON may encode the same tick either way ("1 + 1/2", a
        # decimal, or the two integers). This is a soft report; a reading that
        # matches the document is worth more than one that is theoretically
        # canonical and flags a correct figure. Each match is CONSUMED so the
        # a/b rewrite below cannot reach it and glue "1" to "1/2" as "11/2".
        def _take_mixed(mm):
            whole, num, den = (int(mm.group(i)) for i in (1, 2, 3))
            if not den:
                return mm.group(0)
            nums.add(abs(whole + (-1 if whole < 0 else 1) * num / den))
            nums.update({abs(float(whole)), float(num), float(den)})
            return " "

        def _take_frac(mm):
            a, b = int(mm.group(1)), int(mm.group(2))
            if not b:
                return mm.group(0)
            nums.update({abs(a / b), abs(float(a)), abs(float(b))})
            return " "

        label = re.sub(r"(-?\d+)\s*(?:\\[,!;:>]\s*)*\\[dt]?frac\s*"
                       r"\{\s*(\d+)\s*\}\s*\{\s*(\d+)\s*\}", _take_mixed, label)
        label = re.sub(r"\\[dt]?frac\s*\{\s*(-?\d+)\s*\}\s*"
                       r"\{\s*(-?\d+)\s*\}", _take_frac, label)
        label = re.sub(r"\\[dt]?frac\s*\{?(-?\d+)\}?\s*\{?(-?\d+)\}?", r"\1/\2", label)
        # subscript indices are point NAMES, not printed quantities — the SSA
        # swing figure labels its two apexes $B_1$/$B_2$
        label = re.sub(r"_\{?\d+\}?", "", label)
        nums |= {float(n) for n in NUM_RE.findall(label)}
    # pic "$34^\circ$" quotes: mirror contract with check_layout — its
    # has_valued_figure scans pic quotes with THIS same extraction regex, so
    # the two detectors cannot disagree about whether a pic label is a figure
    # value (they once did: this branch counted pic numbers while check_layout
    # was blind to them, a false PASS on the all-or-nothing scope rule there).
    for m in re.finditer(r'"\s*\$?([^"$]*)\$?\s*"', block):
        nums |= {float(n) for n in NUM_RE.findall(m.group(1))}
    # macro-style figures (templates/figure-macros.tex): the mandatory braced
    # args ARE the printed labels, so their numbers are figure values; the
    # optional [..] arg is scale/styling and excluded — the same mirror
    # contract with check_layout.has_valued_figure's macro branch.
    for m in re.finditer(r"\\[a-zA-Z]*(?:rt|tri|fig)[a-zA-Z]*"
                         r"(?:\[[^\]]*\])?((?:\{[^{}]*\}){2,})", block):
        args = re.sub(r"\\[dt]?frac\s*\{?(-?\d+)\}?\s*\{?(-?\d+)\}?", r"\1/\2",
                      m.group(1))
        nums |= {float(n) for n in NUM_RE.findall(args)}
    return nums


def includegraphics_problems(blocks):
    """1-based indexes of problem blocks that embed \\includegraphics.

    An external image is opaque to this checker: the values it shows cannot
    be bound to the verify JSON — worse, digits in its FILENAME or options
    leak into the prose scan and can read as consistent givens, so the report
    looks healthy for a figure nobody verified. Like an unresolved \\probfig,
    an uncheckable figure must never read as a pass (exit 2). Blocks are
    comment-blanked here because problem_blocks slices raw text — a
    commented-out \\includegraphics must not trip a hard gate.
    """
    return [i for i, b in enumerate(blocks, 1)
            if re.search(r"\\includegraphics\b", blank_comments(b))]


# Fields that say where a problem SITS rather than what it says. None is ever
# printed on the sheet, so none may count as a printed given.
#
# THE RULE, because the first version of this list was written by analogy and
# got it wrong: a name that any verify TYPE declares carries mathematics and
# must NOT be here. "points" was excluded on the strength of its name — it
# sounds like an effort-marker score — and it is in fact the coordinate list for
# distance/midpoint/slope/polygon_area, the exact numbers those stems print. It
# made every coordinate-geometry problem flag its own coordinates. There is no
# "points" metadata field at all; \probpts is computed from difficulty.
#
# The only type-declared names kept here are tol and tol_reason, which are
# machinery for the comparison rather than anything a student reads.
# tests/test_pipeline_fixes.py asserts this list against verify.SCHEMAS, so a
# new type that declares a name on it fails the suite instead of quietly
# blinding the checker.
_TOLERANCE_MACHINERY = frozenset({"tol", "tol_reason"})
_BOOKKEEPING = frozenset({
    "id", "type", "difficulty", "workspace_cm", "word_problem", "bloom",
    "skill", "facet", "standard", "review_mode", "answer_unit", "subtitle",
    "note", "role",
}) | _TOLERANCE_MACHINERY


def json_numbers(entry):
    found = set()

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            # Both signs. The prose side is scanned by an UNSIGNED regex, so a
            # printed "-137" arrives here as 137.0 and a JSON value of -137
            # could never match its own printed form — every negative given
            # reported as "missing from JSON". Sign is not recoverable from the
            # prose scan either way, so the comparison is made on magnitude.
            found.add(float(v))
            found.add(abs(float(v)))
        elif isinstance(v, str):
            for n in NUM_RE.findall(v):
                found.add(float(n))
            # A JSON "1/8" and a figure tick of 1/8 are the same quantity, but
            # the two sides read it differently: the label scanner offers the
            # value AND the parts, this side offered only the parts, so 0.125
            # could never be donated and every fraction-marked figure reported
            # a value "missing from JSON". That is the whole 5.MD.B.2 line-plot
            # band. Both sides now offer both readings and therefore meet.
            for a, b in re.findall(r"(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)", v):
                try:
                    if float(b):
                        found.add(abs(float(a) / float(b)))
                except ValueError:
                    pass
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            # A read_data table's KEYS are printed givens too — the x-column of
            # a table the student reads. Walking values only made every x-value
            # look like an unexplained prose number.
            for k2 in v:
                if isinstance(k2, str) and NUM_RE.fullmatch(k2.strip()):
                    found.add(float(k2))
            # desc/note are prose ABOUT the problem at any depth (a trap's
            # "used 3 instead of 4" must not donate 3 and 4 to the given set);
            # a trap's expr/value ARE printed planted numbers and flow through.
            for k2, x in v.items():
                if k2 not in ("desc", "note"):
                    walk(x)

    # An `at` binding the expression never uses is not a verified given — it is
    # a number sitting in the JSON that nothing checks. Walking all of `at` made
    # it a one-field way to silence this gate: add "m": 6 to any entry and a 6
    # printed in the stem stops being reported, whether or not anything verifies
    # it. An author found the bypass, declined to use it, and said so. Five
    # recorded tasks carry unused keys, all of them innocent — authors listing a
    # problem's other givens to quiet the report, which is the same effect by a
    # kinder route. Filtering here rather than rejecting in verify.py keeps every
    # existing document valid; the numbers simply go back to being reported.
    ent = dict(entry)
    at = ent.get("at")
    if isinstance(at, dict):
        used = set(re.findall(r"[A-Za-z]+", str(ent.get("expr", ""))))
        ent["at"] = {k: v for k, v in at.items() if k in used}

    # Only fields that describe the MATHEMATICS may donate a given. Bookkeeping
    # fields describe the problem's place in the sheet, and letting them in is a
    # silent pass: a "difficulty": 3 tag donated 3 to the given set, so a stem
    # printing a stray 3 that nothing verifies could never be reported as drift.
    # Found because the same stem flagged a phantom value in isolation and went
    # quiet in the real run — the only difference was the difficulty tag.
    # workspace_cm, points and the ordering keys are the same shape of leak.
    walk({k: v for k, v in ent.items() if k not in _BOOKKEEPING})
    return found


def main():
    argv = sys.argv[1:]
    sources_path = None
    if "--sources" in argv:
        i = argv.index("--sources")
        sources_path = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    figs_path = None
    if "--figs" in argv:
        i = argv.index("--figs")
        figs_path = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    meta_path = None
    if "--meta" in argv:
        i = argv.index("--meta")
        meta_path = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    if len(argv) != 2 or figs_path == "" or meta_path == "":
        print("Usage: check_prose_consistency.py <worksheet.tex> <verify.json> "
              "[--figs <figs.tex>] [--meta <meta.tex>]", file=sys.stderr)
        sys.exit(2)
    tex_path, json_path = argv
    if sources_path is not None:
        from check_sources import validate
        try:
            validate(tex_path, sources_path)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            print(f"Source review failed: {exc}", file=sys.stderr)
            sys.exit(2)
    tex = open(tex_path, encoding="utf-8").read()
    data = json.load(open(json_path, encoding="utf-8"))
    # Expand \probfig{N} into the rendered figure bodies BEFORE parsing, so
    # the figure-label check (CASE-21) sees the labels the student sees. An
    # unresolved call means an UNCHECKED figure — like the zero-parse guard
    # below, that must never read as a pass.
    if figs_path:
        tex, unresolved = expand_probfigs(tex, probfig_bodies(open(figs_path, encoding="utf-8").read()))
    else:
        unresolved = sorted({int(n) for n in CALL_RE.findall(tex)})
    if unresolved:
        print(f"  ⚠ UNRESOLVED \\probfig for problem(s) {unresolved}.")
        print("    Those figures' labels live in the generated figs file, so this")
        print("    check cannot see them. Re-run with the file render_figures.py")
        print("    emitted:  --figs /tmp/figs_TOPIC_DATE.tex")
        print("    (and re-run scripts/render_figures.py if the JSON changed).")
        sys.exit(2)
    blocks = problem_blocks(tex) or item_blocks(tex) or examplebox_blocks(tex)
    flagged = includegraphics_problems(blocks)
    if flagged and sources_path is None:
        print(f"  ⚠ \\includegraphics in worksheet problem(s) {flagged}.")
        print("    An external image cannot be bound to the verify JSON, so this check")
        print("    cannot see the values it shows — like an unresolved \\probfig, an")
        print("    uncheckable figure must never read as a pass. Generate the figure")
        print("    with scripts/render_figures.py (triangle problems) or a TikZ figure")
        print("    from references/latex-templates.md so its labels are checkable.")
        sys.exit(2)

    if flagged:
        print(f"  External images in problems {flagged}: source/visual review bound; image math is not CAS-verified.")

    # ── Effort markers (construction lives in scripts/render_meta.py) ────────
    # Comment-blanked text for the literal ban: a comment MENTIONING \bigstar
    # is not a hand-typed marker.
    clean = blank_comments(tex)
    literal = []
    if re.search(r"\\bigstar\b", clean):
        literal.append("\\bigstar")
    if "\u2605" in clean:
        literal.append("a literal star glyph")
    if re.search(r"\(\s*\d+\s*pts\s*\)", clean):
        literal.append('"(N pts)"')
    if literal:
        # unconditional — even with no meta file in play, matching the
        # hand-drawn-valued-figure precedent. Prose like "scored 78 points"
        # is untouched: only the unambiguous marker patterns are banned.
        print(f"  ❌ hand-typed effort marker(s): {', '.join(literal)}.")
        print("    Effort markers must be constructed from the verify JSON — "
              "run scripts/render_meta.py")
        print("    and place \\probmeta{N} or \\probpts{N} (see SKILL.md step 3).")
        sys.exit(2)
    block_meta = [[int(n) for n in META_CALL_RE.findall(b)] for b in blocks]
    block_pts = [[int(n) for n in PTS_CALL_RE.findall(b)] for b in blocks]
    meta_flat = [n for c in block_meta for n in c]
    pts_flat = [n for c in block_pts for n in c]
    if meta_flat or pts_flat:
        have = probmeta_ids(open(meta_path, encoding="utf-8").read()) if meta_path else set()
        unresolved_meta = sorted(set(meta_flat + pts_flat) - have)
        if unresolved_meta:
            # an unresolved marker is an UNCHECKED marker — same rule as
            # \probfig above, never a silent pass
            print(f"  ⚠ UNRESOLVED \\probmeta/\\probpts for problem(s) "
                  f"{unresolved_meta}.")
            print("    Marker bodies live in the generated meta file, so this "
                  "check cannot see them.")
            print("    Re-run with the file render_meta.py emitted:  "
                  "--meta /tmp/meta_TOPIC_DATE.tex")
            print("    (and re-run scripts/render_meta.py if the JSON changed).")
            sys.exit(2)
        if meta_flat and pts_flat:
            stars_in = [i + 1 for i, c in enumerate(block_meta) if c]
            pts_in = [i + 1 for i, c in enumerate(block_pts) if c]
            print(f"  ❌ mixed marker modes: \\probmeta in block(s) {stars_in} "
                  f"but \\probpts in block(s) {pts_in} — use ONE mode for the "
                  "whole document (points for quizzes, stars for practice).")
            sys.exit(2)
        calls = block_meta if meta_flat else block_pts
        macro = "\\probmeta" if meta_flat else "\\probpts"
        bad_blocks = [i + 1 for i, c in enumerate(calls) if c != [i + 1]]
        if bad_blocks:
            print(f"  ❌ marker/problem binding failed in block(s) {bad_blocks}: "
                  f"once any marker appears, problem block i must contain "
                  f"exactly {macro}{{i}} — swapped, duplicated, or missing "
                  "markers put the wrong effort label on a problem (all "
                  "problems carry a marker or none do).")
            sys.exit(2)

    # group JSON entries by id — one worksheet problem may have several checks
    by_id = {}
    for e in data.get("problems", []):
        by_id.setdefault(int(e.get("id", 0)), []).append(e)

    total_nums = matched = 0
    report = []
    fig_flags = []
    for i, block in enumerate(blocks):
        prose = prose_numbers(block)
        given = set()
        for entry in by_id.get(i + 1, []):
            given |= json_numbers(entry)
        # 100·x style: a prose "20%" is 20 in prose but 0.2 or 20/100 in JSON
        given |= {g * 100 for g in given} | {g / 100 for g in given if g}
        missing = sorted(p for p in prose if p not in given)
        # intermediate worked-example values (subexpressions of the entry's
        # own approx expr, at printed >=2dp precision) count as matched —
        # without this, a correct study guide flags most of its examples and
        # trains the reader to ignore the one line that carries real drift
        missing, _ = suppress_intermediates(block, missing,
                                            by_id.get(i + 1, []))
        total_nums += len(prose)
        matched += len(prose) - len(missing)
        report.append((i + 1, sorted(prose), missing))
        # figure-label consistency (CASE-21): visible figure numbers must be givens
        fig = figure_label_numbers(block)
        fig_missing = sorted(f for f in fig if f not in given and f not in prose)
        if fig_missing:
            fig_flags.append((i + 1, fig_missing))

    print(f"Prose-consistency report: {tex_path}")
    if not blocks:
        print("\n  ⚠ PARSED ZERO PROBLEMS from this file.")
        print("    Nothing was checked, so this is NOT a pass. The document")
        print("    must use \\problem{...}, an enumerate/\\item list, or")
        print("    examplebox environments (study guides).")
        sys.exit(2)
    for pid, prose, missing in report:
        flag = f"  ⚠ missing from JSON: {missing}" if missing else "  ok"
        print(f"  problem {pid}: {len(prose)} prose numbers{flag}")
    rate = matched / total_nums if total_nums else 1.0
    scope = f"{len(blocks)} problem block(s)"
    print(f"\nMatch rate: {matched}/{total_nums} ({100*rate:.1f}%) across {scope}")
    if total_nums == 0:
        print("  ⚠ no numbers found in any problem — check the parse before trusting this")
    if fig_flags:
        print("Figure-label numbers not found in JSON givens (audit 3d):")
        for pid, miss in fig_flags:
            print(f"  ⚠ problem {pid}: figure shows {miss}")
    else:
        print("Figure labels: all consistent with JSON givens.")
    print("(heuristic — investigate misses; derived/rounded prose values, "
          "dates, and story numbers unused by the computation are expected "
          "false flags)")


if __name__ == "__main__":
    main()
