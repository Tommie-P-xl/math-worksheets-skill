#!/usr/bin/env python3
r"""render_quick_answers.py — construct the answer key's compact "Quick
Answers" bank FROM the verify JSON, so the at-a-glance grading column can
never disagree with the verified values.

Usage: render_quick_answers.py <verify_<stem>.json> <ak_<stem>.tex> [out.tex]
       [--ws=<ws_<stem>.tex>]
Default output: qa_<stem>.tex next to the JSON (verify_ prefix -> qa_,
mirroring figs_/meta_ naming). build.sh re-runs this EVERY build — the
render-figures pattern — so the gated path cannot go stale and no staleness
lint is needed (a value-comparison checker would just duplicate this
generator).

The bank is one multicols block of "N. value" entries, one per problem id
1..problem_count (verify.py guarantees full id coverage). Entries are PLAIN
TEXT, never \ans/\boxed: check_answer_key.py binds only boxed answers inside
problem segments and never resolves \input, so the bank cannot degrade the
strict per-problem gate (fixture-locked invariant).

Rendering rules (nothing raw is ever injected into LaTeX):
  * numeric expected — verbatim as written in the JSON (Decimal parse keeps
    a verified 6.30 printing as 6.30, not 6.3); a negative number is set in
    math mode so its minus sign is a real minus, not a text hyphen;
  * string expected — validated by verify.py's safe_parse (ONE allowlist for
    the whole system, so a Python builtin like "open" can never reach the
    printer), then re-parsed with evaluate=False and printed in the AUTHOR's
    form: 9/12 stays 9/12, "2 + 3/4" stays a mixed number, and a completely
    factored 3*(x-3)*(x+3) is not silently redistributed;
  * a string that is NOT a mathematical expression under that allowlist
    (a relation "<", a bin label "20-29", "no solution") prints as ITSELF,
    TeX-escaped — never evaluated arithmetically and never hidden;
  * lists comma-joined; an inequality's interval spec prints as an interval,
    a midpoint's pair prints bracketed; dicts as var = value pairs;
  * a VERIFIED empty solution set prints the empty-set symbol, never "---";
  * "---" is RESERVED for "no machine check exists": a manual-only id prints
    it alone, and an id that mixes machine checks with a manual entry prints
    it after the verified values, so a grader can always tell a verified
    answer from an unchecked one;
  * multi-entry ids join all expected values, each labelled by its own
    "slot" (which side, which intercept) when the JSON declares one, so a
    two-slot answer can never read in the wrong order. FOLLOW-UP: "slot" is
    an optional per-entry label this generator reads but verify.py's strict
    schema does not yet accept — add it to _UNIVERSAL_FIELDS there (a label,
    like "note", never touched by any check) before authors can declare it;
    until then a multi-slot id renders as it always did, unlabelled;
  * a declared answer_unit is printed with the value;
  * with --ws, a problem printing MORE responses than the verification covers
    is marked \unchecked, and a "What is verified" note names those problems
    and the manual ones. Without --ws the bank cannot know this and stays
    silent about it — the marks appear only when coverage was actually
    measured, never as decoration.
Column count adapts to the widest rendered entry (4 / 3 / 2) so factored and
interval answers don't wreck the layout.

PREFLIGHT: the ak_ source must \input{worksheet-preamble} (a hand-rolled
preamble is the transcription-drift class that produced the one-answer-per-
paragraph key this tool exists to fix, and the shipped preamble is what
guarantees multicol and the compact \ans) and must \input the bank file —
a generated bank the key never shows is the real silent failure. Both are
hard errors with teaching messages, fixture-tested.

Exit 0: bank written. Exit 1: preflight failure or invalid input.
"""

import json
import os
import re
import sys
from decimal import Decimal

import sympy
from sympy.parsing.sympy_parser import parse_expr

# ONE parser for the whole system. verify.py validates every expression against
# a token allowlist before it reaches sympy; reusing that function here (rather
# than a second, laxer sympify) means the bank can only ever print something the
# verifier would also accept. The bare sympify this replaced typeset PYTHON
# BUILTINS: sympify("open") SUCCEEDS and returns <built-in function open>, and
# an inequality's [-oo, -3, "open"] shipped that repr into a delivered key.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify  # noqa: E402
from verify import safe_parse, split_equation, VerifyInputError  # noqa: E402

# safe_parse is the GATE; these locals only pin name -> sympy object for the
# second, printing parse. If verify ever renames the table, the printer keeps
# working on sympy's own defaults (identical LaTeX for every allowlisted name) —
# a renamed table must not be able to take the answer key down.
_LOCALS = getattr(verify, "_SYMPY_LOCALS", {})

# "---" is RESERVED: it means "no machine check exists here, read the worked
# solution". It used to double as the fallback for anything sympify could not
# swallow, which made a VERIFIED relation ("<") and an unchecked proof print the
# SAME glyph — the one distinction the bank exists to draw.
# The hand-judged mark. Was "---": an em dash reads as "nothing here" and
# lives one glyph away from a minus sign, exactly the neighbourhood a maths
# answer key crowds. A card suit appears nowhere else in these documents, so
# it can carry ONE meaning — this answer is yours to judge — and the legend
# on the summary page says so. amssymb (always loaded) supplies the glyph.
MANUAL = r"$\spadesuit$"

# An answer nobody checked must not look like an answer somebody checked. The
# bank had exactly two states — a value, or "---" — so a printed response with
# no verify entry at all simply did not appear, and the row looked complete. A
# grader reading "3. 27" cannot tell whether the sheet also asked for a second
# thing that nothing verified. 172 of 300 reviewed cases shipped such an answer.
# The gate (tests/check_answer_slots.py) now blocks the cases it can prove, but
# it cannot read a stem that asks for two things behind one blank, and
# \scratchblank is an author's claim rather than a proof — so the key says so
# wherever coverage is not established.
UNCHECKED = r"\unchecked"
# A verified empty solution set is a RESULT, not a missing check.
EMPTY_SET = r"$\emptyset$"

# Relations are answers on compare/order sheets, and none of them survives a
# parser: "<" is not an expression. Typeset as the relation it is.
_RELATIONS = {"<": "$<$", ">": "$>$", "=": "$=$", "==": "$=$",
              "<=": r"$\le$", ">=": r"$\ge$", "!=": r"$\neq$",
              "≤": r"$\le$", "≥": r"$\ge$", "≠": r"$\neq$"}

# A plain decimal numeral is printed EXACTLY as the author wrote it, for the
# same reason JSON floats are parsed as Decimal: sympy turns "12.50" into 12.5
# and drops the cents off a money answer.
_NUMERAL_RE = re.compile(r"-?(?:\d+\.\d+|\d+|\.\d+)\Z")
# A bin/interval LABEL ("20-29", "90-100") is data, not arithmetic. It passes
# the allowlist — every character is legal — so no parser guard can catch it;
# only the shape can. Requiring no spaces around the hyphen and a non-decreasing
# pair keeps real subtraction (which authors write as "20 - 29", and which is
# an odd thing to bank as an ANSWER anyway) on the mathematical path.
_RANGE_LABEL_RE = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\Z")

# Types whose "expected" is a POINT rather than a list of independent answers.
_POINT_TYPES = {"midpoint"}


def _is_range_label(s):
    m = _RANGE_LABEL_RE.match(s)
    return bool(m) and float(m.group(1)) <= float(m.group(2))


def _drop_unit_factors(expr):
    r"""Remove redundant literal-1 factors left by evaluate=False parsing.

    `parse_expr("1/4", evaluate=False)` builds Mul(1, Pow(4, -1)) — the 1 is an
    artifact of not evaluating, not something the author wrote — and
    sympy.latex faithfully prints "$1 \cdot \frac{1}{4}$". Every numerator-1
    fraction was affected and nothing else: 3/8 and 7/12 print correctly. This
    shipped as visibly malformed probabilities (1/4, 1/2, 1/10) in delivered
    answer keys, and no spelling avoided it — "(1)/(4)" and "1 / 4" parse the
    same way. Dropping the unit factor restores the author's form rather than
    overriding it, which is the whole point of parsing with evaluate=False.

    Top level and one level into an Add's terms: that covers the observed shape
    ("2 + 1/4") without walking the whole tree and risking a rewrite of the
    form this function exists to protect.
    """
    ONE, NEG = sympy.Integer(1), sympy.Integer(-1)

    def strip(e):
        # Recurse through Mul/Add only. Pow, functions and everything else are
        # returned untouched: the artifact lives in the product structure, and
        # walking further would risk rewriting the form this exists to protect.
        # "-x**2/2" parses as Mul(Mul(-1, x**2), 1/2) — the -1 sits one level
        # below the top, which a single-level pass misses.
        if isinstance(e, (sympy.Mul, sympy.Add)):
            args = [strip(a) for a in e.args]
            if isinstance(e, sympy.Add):
                return (sympy.Add(*args, evaluate=False)
                        if any(n is not o for n, o in zip(args, e.args)) else e)
            kept = [a for a in args if a != ONE]
            neg = NEG in kept
            if neg:
                kept = [a for a in kept if a != NEG]
            if not kept:
                return NEG if neg else ONE
            inner = (kept[0] if len(kept) == 1
                     else sympy.Mul(*kept, evaluate=False))
            # evaluate=True on the negation gives sympy's own unary minus
            # ("- \frac{x^{2}}{2}") instead of a literal (-1) factor, without
            # reordering or distributing anything.
            return sympy.Mul(NEG, inner) if neg else inner
        return e

    return strip(expr)


# An expected string the author wrote as scientific notation: a numeric
# mantissa times a power of ten. Matched on the ^→** normalized string.
_SCI_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*\*\s*10\s*\*\*\s*\(?\s*([+-]?\d+)\s*\)?\s*$")


def _math(s):
    """Typeset an expression string the author's way, or raise VerifyInputError.

    safe_parse is the gate (allowlist + rejection message); the second parse is
    the PRINTER, with evaluate=False so sympy cannot rewrite the author's form.
    Canonicalisation is not cosmetic here: it turned a completely factored
    3*(x-3)*(x+3) into (x+3)(3x-9) on a sheet whose directions say "Factor
    completely", and shipped a wrong answer.

    Scientific notation gets its own printer for the same reason: even with
    evaluate=False, parse_expr rewrites "6.2*10**(-4)" into 6.2/10**4 and the
    bank printed \\frac{6.2}{10000} — correct, and not the form the sheet
    teaches. A string that IS the authored form m*10**n prints as m ⋅ 10^n
    directly from the matched literals (locale-aware via \\dec/\\mtimes), so
    the value identity with what the verifier accepted holds by construction.
    """
    # An `equiv` answer may be written as the equation the student writes
    # ("(x-3)**2 + (y+5)**2 = 25"); verify.py compares lhs - rhs, and the bank
    # prints the equation, because a grader scanning this column for a
    # centre-radius answer should see one. Each side is typeset by the same
    # form-preserving path, so the guarantee below holds on both.
    sides = split_equation(s)
    if sides is not None:
        lhs, rhs = (_math(side).strip("$") for side in sides)
        return f"${lhs} = {rhs}$"
    safe_parse(s)                      # validate — raises VerifyInputError
    normalized = s.replace("^", "**")
    sci = _SCI_RE.match(normalized)
    if sci:
        mant, exp = (g.lstrip("+") for g in sci.groups())
        return rf"$\dec{{{mant}}} \mtimes 10^{{{exp}}}$"
    try:
        expr = parse_expr(normalized, local_dict=_LOCALS, evaluate=False)
    except Exception:                  # printer-only fallback; already validated
        expr = safe_parse(s)
    expr = _drop_unit_factors(expr)
    # order='none' keeps the author's term order, so "2 + 3/4" prints as the
    # mixed number it is instead of being reordered to 3/4 + 2.
    tex = sympy.latex(expr, order="none")
    # evaluate=False can leave a literal (-1) coefficient nested inside a
    # product — "-x**2/2" prints \frac{\left(-1\right) x^{2}}{2}. Rewriting
    # the TREE risks the form preservation this function exists for (a deeper
    # pass reorders or distributes), so the sign is normalised at the render
    # level, where it can only touch a coefficient sympy itself calls -1.
    tex = re.sub(r"\\left\(-1\\right\)\s*", "- ", tex)
    # sympy has one natural logarithm and prints it \log. An author who wrote
    # ln means ln — on the sheets where both appear, printing \log for ln is
    # a different function to the student.
    if re.search(r"\bln\s*\(", s) and not re.search(r"\blog\s*\(", s):
        tex = tex.replace(r"\log", r"\ln")
    return "$" + tex + "$"


def _interval(spec):
    """An inequality's [lo, hi, openness] spec -> interval notation.

    Same vocabulary as verify.py's parse_interval_spec, so what the verifier
    proved is what the bank prints. Unwrapped single intervals and unions both
    arrive here.
    """
    if spec and not isinstance(spec[0], list):
        spec = [spec]
    parts = []
    for iv in spec:
        if not (isinstance(iv, list) and len(iv) == 3):
            return None
        lo, hi, openness = iv
        lopen = openness in ("open", "loopen") or lo in ("-oo", "oo")
        hopen = openness in ("open", "hiopen") or hi in ("-oo", "oo")
        parts.append("$" + ("(" if lopen else "[") + _bare(lo) + ", "
                     + _bare(hi) + (")" if hopen else "]") + "$")
    return r" $\cup$ ".join(parts) if parts else None


def _bare(v):
    """An interval endpoint, printed without its own math delimiters."""
    t = _fmt(v)
    return t[1:-1] if t.startswith("$") and t.endswith("$") else t


def _fmt(v, ptype=None):
    """One expected value -> bank text (never raw string injection)."""
    if isinstance(v, bool):
        return MANUAL
    if isinstance(v, (int, Decimal)):
        return _signed(str(v))
    if isinstance(v, float):
        return _signed(repr(v))
    if isinstance(v, str):
        if not v.strip():   # nothing declared is not an answer
            return MANUAL
        if v.strip() in _RELATIONS:
            return _RELATIONS[v.strip()]
        if _NUMERAL_RE.match(v.strip()):
            return _signed(v.strip())
        if _is_range_label(v.strip()):
            return _texsafe(v.strip())
        try:
            return _math(v)
        except Exception:   # VerifyInputError is the expected one
            # Not mathematics under the allowlist — so it is a LABEL, a word,
            # or a relation the author wrote out. It prints as itself, escaped:
            # never "---" (which would claim nobody checked it) and never run
            # through arithmetic. The catch is deliberately total: this is a
            # PRINTER, and no parser surprise may take the answer key down when
            # the honest, escaped literal is always available.
            return _texsafe(v)
    if isinstance(v, list):
        if not v:                      # a verified "no solution"
            return EMPTY_SET
        if ptype == "inequality":
            iv = _interval(v)
            if iv:
                return iv
        if ptype in _POINT_TYPES and len(v) == 2:
            return f"({_fmt(v[0])}, {_fmt(v[1])})"
        return ", ".join(_fmt(x, ptype) for x in v)
    if isinstance(v, dict):
        return ", ".join(f"${k} = $ {_fmt(x)}" for k, x in sorted(v.items()))
    return MANUAL


def _signed(text):
    """A negative number is math: sympy's minus sign next to a text hyphen in
    the same column is two different glyphs for one operation."""
    return f"${text}$" if text.startswith("-") else text


def _fmt_unit(unit):
    """A declared answer_unit, printed with the value it belongs to.

    The unit is half the answer on a measurement sheet — "6.30" and "6.30 ft"
    are not the same thing to grade — and the JSON already declares it for the
    unit gates. Exponents go to math mode so cm^2 is not a literal caret.
    """
    parts = str(unit).split("^")
    out = _texsafe(parts[0])
    for p in parts[1:]:
        out += "$^{" + _texsafe(p) + "}$"
    return out


def _render_expected(entry):
    """One JSON entry -> its text, with its declared slot label and unit.

    A manual entry has no `expected`; it renders as the MANUAL marker under its
    own slot label, so an id with three unscored parts shows three of them.
    """
    if "expected" not in entry:
        text = MANUAL
    else:
        text = _fmt(entry["expected"], entry.get("type"))
        unit = entry.get("answer_unit")
        if isinstance(unit, str) and unit.strip():
            text = f"{text} {_fmt_unit(unit.strip())}"
    slot = entry.get("slot")
    if isinstance(slot, str) and slot.strip():
        # Which value is which. Unlabelled, a two-entry id printed in verify.json
        # ARRAY order: "2. 2.83, 8.49" for a problem asking "AC and BD", with BD
        # first. The label has to come from the JSON, because declaration order
        # is not an answer.
        text = f"{_texsafe(slot.strip())} = {text}"
    return text


def render_entry(entries, uncovered=0):
    """All of one problem id's entries -> its single bank line text.

    `uncovered` is how many printed responses this problem has that NO entry
    covers. It cannot be derived from the JSON — the JSON is exactly the thing
    that is missing an entry — so it comes from counting the worksheet's own
    answer slots (see slot_gap).
    """
    # ONE rendering pass in DECLARATION ORDER, machine values and manual
    # markers alike. Manual entries used to be reduced to a single trailing
    # bool, so an id with three unscored parts printed one "---" and dropped
    # all three slot labels: 30 ids across 21 sheets, one of them a
    # three-part always/sometimes/never item whose row read "---". A grader
    # cannot see how many judgements are owed, or which. Rendering each in
    # place also puts the parts in the order the sheet asks them, which is
    # what makes the labels usable at a glance.
    vals = [_render_expected(e) for e in entries if isinstance(e, dict)]
    text = ", ".join(v for v in vals if v)
    if not text:
        text = MANUAL if (entries or not uncovered) else ""
    if uncovered:
        mark = UNCHECKED if not text else f"{text}~{UNCHECKED}"
        return mark
    return text


def slot_gap(ws_tex, n, by_id):
    """{problem id: printed responses no verify entry covers}.

    Calls the GATE'S OWN decision function (check_answer_slots.shortfall), not
    just its primitives. Sharing the primitives was not enough: this once
    recomputed the comparison itself, and when the gate's rules were refined it
    dropped to 66 flagged cases while the key went on marking 86. A key that
    disagrees with the gate about what is verified is worse than one that says
    nothing, so there is exactly one definition and both callers use it.
    """
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "checks"))
        from check_answer_slots import (blank_comments, segment_spans,
                                        shortfall)
    except ImportError:
        return {}
    tex = blank_comments(ws_tex)
    spans = segment_spans(tex)
    if spans is None:
        return {}
    out = {}
    for i, (a, b) in enumerate(spans[:n], 1):
        out[i], _ = shortfall(tex[a:b], by_id.get(i, []))
    return out


def _idlist(ids):
    return ", ".join(str(i) for i in ids)


def coverage_note(n, unchecked_ids, manual_ids, scratch=0, machine=0, total=0):
    r"""The instructor's one-line answer to "what can I trust here?".

    The bank shows values; it never said what stands behind them. An instructor
    reading a complete-looking column has no way to tell a SymPy-proved answer
    from one the author typed and nothing checked. This states the split
    explicitly and names the problems, so acting on it takes no archaeology:
    mark the verified ones fast, read the flagged ones properly.

    COUNTED IN ANSWERS, NOT PROBLEMS. It counted problems where EVERY response
    was machine-checked, which on a find-and-fix sheet — a correction plus a
    written diagnosis on each item — is always zero. One shipped key read
    "0 of 8 problems fully machine-checked" with eleven passing SymPy checks
    behind it. That is the original defect inverted: it understates the
    verification instead of overstating it, and a parent reading it concludes
    nothing was checked. Answers are also simply the truthful unit — the whole
    reason the slot gate exists is that a problem is not an answer.

    Silent when every response is machine-verified — a legend explaining marks
    that do not appear is noise, and noise is what makes real warnings invisible.
    """
    if not unchecked_ids and not manual_ids and not scratch:
        return []
    out = ["\\medskip\\noindent{\\small\\textbf{What is verified}}"
           "\\par\\nopagebreak",
           "\\vspace{2pt}\\noindent\\rule{\\linewidth}{0.4pt}\\par\\nopagebreak"]
    if total:
        out.append(
            f"\\noindent{{\\small {machine} of {total} answer"
            f"{'s' if total != 1 else ''} machine-checked against SymPy, "
            f"across {n} problem{'s' if n != 1 else ''}.}}\\par")
    else:                                    # pre-count callers
        verified = n - len(unchecked_ids) - len(manual_ids)
        out.append(
            f"\\noindent{{\\small {verified} of {n} problem"
            f"{'s' if n != 1 else ''} fully machine-checked against SymPy.}}"
            "\\par")
    if manual_ids:
        out.append(
            f"\\noindent{{\\small {MANUAL} marks an answer only you can "
            f"judge --- problem{'s' if len(manual_ids) > 1 else ''} "
            f"{_idlist(manual_ids)}. The worked solution states what a correct "
            "response must contain.}\\par")
    if unchecked_ids:
        out.append(
            f"\\noindent{{\\small \\unchecked\\ marks a problem that "
            f"prints more responses than the verification covers --- "
            f"problem{'s' if len(unchecked_ids) > 1 else ''} "
            f"{_idlist(unchecked_ids)}. At least one printed answer there "
            f"carries NO machine guarantee; check "
            f"{'those' if len(unchecked_ids) > 1 else 'it'} yourself before "
            "handing the sheet back.}\\par")
    if scratch:
        # \scratchblank is the author's CLAIM that a blank holds working
        # space, not an answer. The claim is cheap to make and quiets the
        # slot gate, so the one reader it affects gets told it was made.
        out.append(
            f"\\noindent{{\\small The author marked {scratch} blank"
            f"{'s' if scratch != 1 else ''} as working space "
            f"(\\emph{{not}} answers --- nothing checks what lands there).}}"
            "\\par")
    out += ["\\noindent\\rule{\\linewidth}{0.4pt}\\medskip", ""]
    return out


def column_count(entries_text):
    """Deterministic adaptive columns: 4 for short entries, 3, then 2."""
    width = max((len(t) for t in entries_text), default=0)
    if width <= 12:
        return 4
    if width <= 20:
        return 3
    return 2


AKTITLE_RE = re.compile(r"\\aktitleblock\{[^{}]*\}\{([^{}]*)\}")


def curriculum_block(by_id, n, level):
    """A "Curriculum" section for the ANSWER KEY: level, codes, difficulty.

    The grade level is deliberately absent from the worksheet and the study
    guide — a child working a grade below or above reads the label before the
    mathematics, and it tells the student nothing they need. It is the adult's
    information, so it belongs on the adult's document, next to the standards
    codes that answer the question a parent or teacher actually has: what does
    this sheet cover, and where does it sit in the curriculum.

    Built from the verify JSON and the key's own \aktitleblock, never typed, so
    it cannot disagree with the tags the verifier reported.
    """
    codes, diffs = {}, []
    for i in range(1, n + 1):
        for e in by_id.get(i, []):
            std = e.get("standard")
            if std:
                codes.setdefault(str(std), []).append(i)
            d = e.get("difficulty")
            if isinstance(d, int):
                diffs.append(d)
    if not level and not codes:
        return []
    out = ["\\medskip\\noindent{\\small\\textbf{Curriculum}}\\par\\nopagebreak",
           "\\vspace{2pt}\\noindent\\rule{\\linewidth}{0.4pt}\\par\\nopagebreak"]
    if level:
        # VERBATIM, not escaped. This string is lifted out of the key's own
        # \aktitleblock, two inches higher on the same page, where LaTeX has
        # already expanded it — so reprinting it here adds no capability that
        # the document did not already have, and escaping it does real damage:
        # a level of "High School Geometry \quad Definitions and Proof Logic"
        # came out with a literal "\quad" sitting in the middle of it.
        out.append(f"\\noindent{{\\small\\textbf{{Level:}}~{level}}}\\par")
    for code in sorted(codes):
        seen, nums = set(), []
        for i in codes[code]:
            if i not in seen:
                seen.add(i)
                nums.append(str(i))
        out.append(f"\\noindent{{\\small {_texsafe(code)} "
                   f"\\textit{{-- problem{'s' if len(nums) > 1 else ''} "
                   f"{', '.join(nums)}}}}}\\par")
    if diffs:
        out.append(f"\\noindent{{\\small\\textit{{Difficulty {min(diffs)}--"
                   f"{max(diffs)} of 5 across {len(diffs)} tagged "
                   f"check{'s' if len(diffs) > 1 else ''}.}}}}\\par")
    out += ["\\noindent\\rule{\\linewidth}{0.4pt}\\medskip", ""]
    return out


def render(data, level="", ws_tex=""):
    by_id = {}
    for p in data.get("problems", []):
        if isinstance(p, dict) and isinstance(p.get("id"), int):
            by_id.setdefault(p["id"], []).append(p)
    pc = data.get("problem_count")
    n = pc if isinstance(pc, int) and pc > 0 else (max(by_id) if by_id else 0)
    if n == 0:
        raise ValueError("no problems in the verify JSON — nothing to bank")
    # shortfall() already nets entries against what the problem prints, so the
    # value here IS the number of uncovered responses — do not subtract again.
    gap = slot_gap(ws_tex, n, by_id) if ws_tex else {}
    entries, unchecked_ids, manual_ids = [], [], []
    for i in range(1, n + 1):
        ents = by_id.get(i, [])
        short = gap.get(i, 0)
        entries.append(render_entry(ents, short))
        if short:
            unchecked_ids.append(i)
        elif any(isinstance(e, dict) and "expected" not in e for e in ents):
            manual_ids.append(i)
    # A bank of identical answers is a useless bank. Verifying "find the
    # inverse" by equiv on the composition passes every gate and makes every
    # expected value literally "x", so the grader's quick-reference reads
    # "x, x, x, x, ...". No gate catches it — the JSON is correct, the binding
    # is correct, and the printed artifact is worthless. Found by an eval agent
    # who noticed it and re-encoded as solve-for-y to get the real formulas.
    real = [e for e in entries if e != MANUAL]
    if len(real) >= 4 and len(set(real)) == 1:
        print(f"render_quick_answers: WARNING — all {len(real)} banked answers "
              f"are {real[0]!r}. The bank is meant to let a grader scan the "
              f"answers; identical entries mean the verification is proving a "
              f"tautology (e.g. equiv on a composition) rather than the answer "
              f"the student writes. Re-encode so 'expected' holds the real "
              f"result.", file=sys.stderr)
    cols = column_count(entries)
    lines = [
        "% GENERATED every build by scripts/render_quick_answers.py from the",
        "% verify JSON -- edit the JSON, not this file. Entries are plain",
        "% text, never \\ans/\\boxed, so check_answer_key.py's per-problem",
        "% binding stays STRICT (the checker never resolves \\input, and only",
        "% boxed answers inside problem segments count).",
        "\\medskip\\noindent{\\small\\textbf{Quick Answers}}\\par\\nopagebreak",
        "\\vspace{2pt}\\noindent\\rule{\\linewidth}{0.4pt}\\par\\nopagebreak",
        # \raggedright + \sloppy: a bank row is \\-terminated inside multicols,
        # so a long symbolic answer beside a descriptive "slot" label has NO
        # break point and overfulls the column — compile-ak then fails on a
        # sheet whose mathematics and verification are both correct. The two
        # levers that left an author are both bad: shorten the label (against
        # the guidance that labels be descriptive) or change the mathematics.
        # One eval author shortened "(a) fully factored form" to "(a)" to get a
        # green build. Let the row wrap instead; the bank is a reference column,
        # not justified prose, so ragged edges cost nothing.
        f"\\begin{{multicols}}{{{cols}}}\\small\\raggedcolumns"
        "\\raggedright\\sloppy\\noindent",
    ]
    for i, t in enumerate(entries, 1):
        sep = " \\\\[2pt]" if i < len(entries) else ""
        lines.append(f"{i}.~{t}{sep}")
    lines += [
        "\\end{multicols}",
        "\\noindent\\rule{\\linewidth}{0.4pt}\\medskip",
        "",
    ]
    scratch = 0
    if ws_tex:
        try:
            from check_answer_slots import SCRATCH_RE, blank_comments as _bc
            scratch = len(SCRATCH_RE.findall(_bc(ws_tex)))
        except ImportError:
            pass
    machine = sum(1 for e in data.get("problems", [])
                  if isinstance(e, dict) and e.get("type") != "manual")
    total = machine + sum(1 for e in data.get("problems", [])
                          if isinstance(e, dict) and e.get("type") == "manual")
    total += sum(gap.values())          # printed responses nothing covers
    # The verification and curriculum summaries are the ADULT's metadata, and
    # printed between the bank and the worked solutions they pushed the actual
    # answers a page down on busy sheets. They now claim the LAST page for
    # themselves, via \AtEndDocument so the ak_ author changes nothing and the
    # single-\input contract preflight enforces stays exactly as it was. The
    # common-wrong-answers block travels with them: it is a reference table,
    # and the worked solution is where a grader already lands when a student's
    # answer is off. Blank lines cannot appear inside the hook's argument
    # (\AtEndDocument's token list ends a paragraph at a stray \par from a
    # blank line mid-brace), so the sections are joined with explicit \par.
    summary = (coverage_note(n, unchecked_ids, manual_ids, scratch, machine,
                             total)
               + curriculum_block(by_id, n, level)
               + common_errors(by_id, n))
    # The blocks separate themselves with blank lines, and inline those blank
    # lines ARE the \par between a closing rule and the next block's heading.
    # Dropping them fused rule and heading onto one line — "Curriculum"
    # overfull by exactly its own width. Inside the hook a blank line is the
    # hazard and \par is the same token, so swap rather than filter.
    summary = [ln if ln.strip() else r"\par" for ln in summary]
    while summary and summary[-1] == r"\par":
        summary.pop()
    if summary:
        lines += [
            r"\AtEndDocument{\clearpage",
            r"\noindent{\large\textbf{Verification \& Curriculum "
            r"Summary}}\par\nopagebreak",
            r"\vspace{2pt}\noindent\rule{\linewidth}{1pt}\par\nopagebreak",
            r"\vspace{4pt plus 2pt}",
        ] + summary + ["}"]
    return "\n".join(lines)


# A trap description is prose written by whoever authored the JSON, and it lands
# verbatim in LaTeX text mode. A desc reading "wrote (x - 6)^2 for a shift LEFT"
# produced "Missing $ inserted" and killed compile-ak — the JSON was correct and
# machine-checked, and the document still would not build. Escaping here rather
# than forbidding the characters keeps the failure impossible instead of merely
# documented.
#
# "<" and ">" are here for the bank rather than for prose: a literal answer can
# now be a written-out relation ("x < 3 or x > 5"), and in text mode those two
# characters are font-encoding-dependent (they come out as inverted marks under
# OT1). \textless/\textgreater print the glyph the author meant under any
# encoding.
_TEX_ESCAPES = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                "^": r"\textasciicircum{}", "~": r"\textasciitilde{}",
                "<": r"\textless{}", ">": r"\textgreater{}"}


def _texsafe(text):
    """Escape prose for LaTeX text mode, backslash first so it is not re-escaped."""
    out = str(text).replace("\\", "\x00")
    for ch, rep in _TEX_ESCAPES.items():
        if ch != "\\":
            out = out.replace(ch, rep)
    return out.replace("\x00", _TEX_ESCAPES["\\"])


def common_errors(by_id, n):
    """A "Common wrong answers" block built from the declared traps.

    The key proves the right answer but says nothing about how to grade a wrong
    one. Every declared trap already carries the misconception, the expression a
    student following it would evaluate, and the value that produces — and
    verify.py machine-checks that the trap value really is what the wrong method
    yields. Printing it turns grading into teaching: seeing 7.37 tells the
    grader the student used cos where tan was needed, which is a different
    conversation from "wrong, minus two".

    Emitted through \\commonerror, never \\ans/\\boxed, so
    check_answer_key.py's per-problem binding of CORRECT answers stays strict
    and a wrong value can never be mistaken for a verified one.
    """
    rows = []
    for i in range(1, n + 1):
        for entry in by_id.get(i, []):
            for trap in (entry.get("traps") or []):
                desc, val = trap.get("desc"), trap.get("value")
                if desc is None or val is None:
                    continue
                rows.append((i, _fmt(val), desc))
    if not rows:
        return []
    out = [
        "\\medskip\\noindent{\\small\\textbf{Common wrong answers}}"
        "\\par\\nopagebreak",
        "\\vspace{2pt}\\noindent\\rule{\\linewidth}{0.4pt}\\par\\nopagebreak",
    ]
    for i, val, desc in rows:
        out.append(f"\\commonerror{{{i}}}{{{val}}}{{{_texsafe(desc)}}}")
    out += ["\\noindent\\rule{\\linewidth}{0.4pt}\\medskip", ""]
    return out


def preflight(ak_tex, out_base):
    """Teaching-message errors for the two silent-failure classes."""
    faults = []
    if not re.search(r"\\input\{[^}]*worksheet-preamble(?:\.tex)?\}", ak_tex):
        faults.append(
            "the answer key does not \\input{worksheet-preamble} — hand-rolled "
            "preambles are the transcription-drift class that produced the "
            "one-answer-per-paragraph key, and the shipped preamble is what "
            "provides multicol and the compact \\ans. Start the key with the "
            "template preamble (see templates/worksheet-preamble.tex).")
    token = re.escape(out_base[:-len(".tex")] if out_base.endswith(".tex")
                      else out_base)
    if not re.search(r"\\input\{[^}]*" + token + r"(?:\.tex)?\}", ak_tex):
        faults.append(
            f"the quick-answer bank was generated but the key never shows it — "
            f"add \\input{{{token}}} directly under \\aktitleblock.")
    return faults


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--ws=")]
    ws_path = next((a[len("--ws="):] for a in argv[1:]
                    if a.startswith("--ws=")), None)
    if len(args) not in (2, 3):
        print("Usage: render_quick_answers.py <verify_TOPIC_DATE.json> "
              "<ak_TOPIC_DATE.tex> [out.tex] [--ws=ws_TOPIC_DATE.tex]",
              file=sys.stderr)
        return 1
    json_path, ak_path = args[0], args[1]
    base = os.path.basename(json_path)
    stem = base[len("verify_"):] if base.startswith("verify_") else base
    stem = stem[:-len(".json")] if stem.endswith(".json") else stem
    out_path = args[2] if len(args) == 3 else \
        os.path.join(os.path.dirname(os.path.abspath(json_path)),
                     f"qa_{stem}.tex")
    try:
        # Decimal float parsing keeps the JSON's written precision: a verified
        # 6.30 must print 6.30 in the bank, not 6.3
        data = json.load(open(json_path), parse_float=Decimal)
        ak_tex = open(ak_path).read()
        # Optional: without it the bank still renders, it just cannot report
        # which printed responses nothing covers.
        ws_tex = open(ws_path).read() if ws_path else ""
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        return 1
    m = AKTITLE_RE.search(ak_tex)
    level = m.group(1).strip() if m else ""
    faults = preflight(ak_tex, os.path.basename(out_path))
    if faults:
        for f in faults:
            print(f"render_quick_answers.py: {f}", file=sys.stderr)
        return 1
    try:
        text = render(data, level, ws_tex)
    except ValueError as e:
        print(f"render_quick_answers.py: {e}", file=sys.stderr)
        return 1
    with open(out_path, "w") as f:
        f.write(text)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
