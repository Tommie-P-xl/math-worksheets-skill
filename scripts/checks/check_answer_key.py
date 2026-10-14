#!/usr/bin/env python3
"""
check_answer_key.py — bind the printed answer key to the verified JSON,
problem by problem.

verify.py proves the JSON's `expected` values are correct, but the student
reads the PDF. Nothing otherwise guarantees the answer key's printed answers
match the verified values (audit A1/3a). This checker splits the key into
per-problem segments and requires each problem's verified values to appear in
THAT problem's \\boxed{}/\\ans{} answer.

Usage: python3 tests/check_answer_key.py <ak_*.tex or ss_*.tex> <verify.json>

Why per problem, per box (audit B1/B2/B3): a whole-document number match let
a key with shuffled answers pass, let a wrong \\boxed value pass whenever the
correct number survived in the worked steps beside it, and a flat 0.011
tolerance let \\boxed{4.52} satisfy a verified 4.51. The box is what the
student trusts, so the hard gate reads only the boxes, problem by problem,
at the precision each answer is printed with.

Not every answer is a value. An `equiv` entry's `expected` is a whole
EXPRESSION written as lhs - rhs, so its literals are pieces of one answer
rather than answers of their own: a miss there is reported once, naming the
type and the rule ("box the whole rewritten form"), not once per literal as
"the boxed value is wrong". And whether an answer is SYMBOLIC is decided by
walking `expected`, not by its JSON shape — ["18 - 3*x/2"] is the same
mathematics as "18 - 3*x/2" and `--schema` prints the list form for `solve`.

Units bind the same way (tests/_units.py): a problem that declares
"answer_unit" must print that unit inside its own box, and a box printing a
lexicon unit the JSON never declared hard-fails — otherwise a key could
answer a metres problem in feet and pass every numeric gate.

Exit 0 = every verified value is boxed in its own problem (soft alignment
notes may still print when binding is degraded). Exit 1 = drift: a wrong or
missing boxed value, a swapped key, a unit mismatch, a segment/problem count
mismatch, or a key with no recognizable problem structure.
"""
import json
import re
import sys
import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _tex_segments import segment_spans, blank_comments, box_spans  # noqa: E402
from _units import unit_in, undeclared_units  # noqa: E402

NUM = re.compile(r"-?\d+(?:\.\d+)?(?:/\d+)?")
# Both groups must be FULLY braced and contain nothing but a number (leading
# spacing macros allowed). The old pattern made the braces optional, which let
# it match a PREFIX and rewrite what it did not understand:
#   \tfrac{11\pi}{6}  -> "1/1\pi}{6}"   the 11 destroyed, reported as a swapped key
#   \dfrac{-16x}{4}   -> "-1/6x}{4}"    -16 became -0.1667
#   \dfrac{3}{1+9x^2} -> "3/1+9x^2}"    the 1 swallowed
#   \dfrac{\,16}{5}   -> unmatched      3.2 invisible in its own box
# Three eval agents hit these as "verified value is not in the boxed answer",
# a message that points at the author instead of at this regex. When the braces
# hold anything else, leave the text alone: the plain number scanner then finds
# 11 and 6 on their own, which is worse than a fraction and far better than a lie.
_FRAC = re.compile(
    r"\\[dt]?frac\s*"
    r"\{\s*(?:\\[,!;:>]\s*)*(-?\d+(?:\.\d+)?)\s*\}\s*"
    r"\{\s*(?:\\[,!;:>]\s*)*(-?\d+(?:\.\d+)?)\s*\}")


_MIXED = re.compile(
    r"(-?\d+)\s*(?:\\[,!;:>]\s*)*\\[dt]?frac\s*"
    r"\{\s*(?:\\[,!;:>]\s*)*(\d+)\s*\}\s*"
    r"\{\s*(?:\\[,!;:>]\s*)*(\d+)\s*\}")


# The SAME mixed number, written the way a verify JSON has to write it: sympy
# has no mixed-number syntax, so "2 3/4" is spelled "2 + 3/4" and sympifies to
# 11/4. This checker read it as two answers, 2 and 0.75, and got away with it
# only while the printed side ALSO split "2\tfrac{3}{4}" into 2 and 3/4. Fixing
# the printed side broke the pair: the key boxed 2.75 and the JSON demanded a
# bare 2 and a bare 0.75 that no correct key would print. Both sides now agree
# it is one number, which is what verify.py checked in the first place.
#
# Unlike the LaTeX form, this one means plain addition — "-2 + 3/4" is -1.25,
# not -2.75 — because that is what sympy evaluates. The lookbehind keeps it off
# exponents and operands: "x**2 + 1/2" must stay 2 and 0.5, not become 2.5.
_MIXED_SUM = re.compile(r"(?<![\w.*^/}])(-?\d+)\s*\+\s*(\d+)/(\d+)(?!\d)")


# \pm PRINTS BOTH SIGNS, so a box holding it offers both values.
#
# A solution set stored as ["7*I", "-7*I"] is correctly and idiomatically boxed
# as \ans{x = \pm 7i}, but the number scanner saw one token, +7, and the -7 was
# reported as "boxed as 7 without its sign" — a sign complaint against a key
# that prints the sign, in the one notation that prints BOTH. The same holds for
# a real solution set [7, -7] against \ans{x = \pm 7}, where strict sign applies
# and the false failure is unavoidable without reading \pm.
#
# So \pm N (and \mp N) expands to the two values it means. It only ADDS the
# opposite-signed reading of a token that is already there; nothing that used to
# bind stops binding. Only a digit directly after the macro is expanded —
# \pm\sqrt{7} keeps its single 7, because the value the box offers is not 7.
_PM = re.compile(r"\\(?:pm|mp)\s*(?:\\[,!;:>]\s*)*(\d+(?:\.\d+)?(?:/\d+)?)")


def _pm_pair(m):
    return f"{m.group(1)} -{m.group(1)}"


def _mixed_sum_value(m):
    whole, num, den = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if den == 0:
        return m.group(0)
    return repr(whole + num / den)


def _mixed_value(m):
    """2\tfrac{3}{4} -> 2.75, keeping the sign of the whole part."""
    whole, num, den = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if den == 0:
        return m.group(0)
    sign = -1 if whole < 0 else 1
    return repr(whole + sign * num / den)


def normalize_latex_numbers(text):
    """Rewrite text so the number regex sees actual values.

    - \\frac{a}{b} becomes a/b (stays contiguous for the fraction branch)
    - thousands separators drop, both plain 1,234 and LaTeX 1{,}234
    - a '-' after a letter, digit, ')' or '}' is binary subtraction, not a
      sign: '(x-3)' must yield 3, not -3, or a correct factored key
      false-fails against expected '(x - 3)*(x - 4)' (audit ak_factor).
      A leading sign ('= -4', '{-4}') is preserved.
    """
    # A mixed number is one value, not two. "2\tfrac{3}{4}" used to concatenate
    # into "23/4" = 5.75, so a verified 2.75 could never bind to the answer a
    # reader plainly sees. Handled before _FRAC so the digit is consumed with
    # its fraction rather than left stranded beside it.
    text = _MIXED.sub(_mixed_value, text)
    text = _FRAC.sub(r"\1/\2", text)
    # After _FRAC, so "2 + \tfrac{3}{4}" has become "2 + 3/4" and a key that
    # writes the mixed number as a sum binds to the same value as one that
    # writes it as a mixed numeral.
    text = _MIXED_SUM.sub(_mixed_sum_value, text)
    # After the fraction rules, so "\pm\dfrac{7}{2}" has already become
    # "\pm 7/2" and expands to both readings of the same fraction.
    text = _PM.sub(_pm_pair, text)
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    text = re.sub(r"(?<=\d)\{,\}(?=\d{3})", "", text)
    text = re.sub(r"(?<=[A-Za-z0-9)\}])-", " ", text)
    return text


def boxed_answers(tex):
    """Each \\boxed{...}/\\ans{...}: (start offset, content), nesting-aware,
    in order. Offsets let the caller test whether a box lies inside a
    problem segment — the per-problem gate only applies when they all do."""
    out = []
    for m in re.finditer(r"\\(?:boxed|ans)\{", tex):
        i, depth, buf = m.end(), 1, []
        while i < len(tex) and depth:
            c = tex[i]
            depth += (c == "{") - (c == "}")
            if depth:
                buf.append(c)
            i += 1
        out.append((m.start(), "".join(buf)))
    return out


# A box's body is typeset in MATH MODE, where spaces do not print. \akheader
# renews \ans to wrap its argument in \ensuremath, so \ans{no solution} prints
# "nosolution" — compiles clean, passes every gate, and is visible only by
# reading the PDF. Found by an author who read theirs.
#
# The signature is exact: two runs of two-or-more LETTERS separated by a space,
# outside any text-mode wrapper. One-letter runs are variable juxtaposition
# ("x = 2", "sin x") and are left alone; anything already inside \text, \mbox,
# \mathrm, \textrm or \operatorname prints its spaces and is stripped first.
_TEXT_WRAPPED = re.compile(
    r"\\(?:text|mbox|textrm|mathrm|operatorname)\s*\{[^{}]*\}")
_LOST_SPACE = re.compile(r"(?<![A-Za-z\\])[A-Za-z]{2,}\s+[A-Za-z]{2,}")


def lost_spaces(box):
    """The words a math-mode box will run together, or []."""
    body = _TEXT_WRAPPED.sub(" ", box)
    body = re.sub(r"\\[a-zA-Z]+", " ", body)      # macros are not printed words
    return [m.group(0) for m in _LOST_SPACE.finditer(body)]


def num_tokens(text):
    """(value, raw_token) pairs for every number printed in `text`.

    The raw token is kept because matching is precision-aware: the written
    form decides how close a verified value must be (audit B3). The old
    set-of-round(x, 4) discarded exactly that information.
    """
    out = []
    src = normalize_latex_numbers(text)
    for m in NUM.finditer(src):
        tok = m.group(0)
        # An exponent followed by a division is not a fraction. "pi*h**2/9" read
        # as 2/9 = 0.2222 and demanded that value in the printed box, which no
        # correct answer key would ever contain — a guaranteed false failure on
        # every cone volume, every x**2/4. Split it back into its two numbers.
        if "/" in tok and src[max(0, m.start() - 2):m.start()] in ("**", "^ ") \
                or ("/" in tok and src[max(0, m.start() - 1):m.start()] == "^"):
            a, b = tok.split("/")
            for part in (a, b):
                try:
                    out.append((float(part), part))
                except ValueError:
                    pass
            continue
        try:
            if "/" in tok:
                a, b = tok.split("/")
                out.append((float(a) / float(b), tok))
            else:
                out.append((float(tok), tok))
        except (ValueError, ZeroDivisionError):
            pass
    return out


def value_matches(v, val, tok):
    """Does verified value v match printed token tok (parsed value val)?

    Mirrors verify.py's rounds_to semantics without importing it (this
    checker stays dependency-free): a printed decimal matches only if v
    rounds half-up (the school convention) to it at its own written
    precision — so \\boxed{4.52} can never satisfy a verified 4.51, while
    5, 5.0 and 5.00 all mean the same answer. Integer tokens accept
    anything that rounds to them (within 0.5). Fraction tokens are exact
    up to half an ulp at 4 decimals, so a key printing 2/3 for a JSON
    value stored as 0.6667 still binds; anything coarser is drift.
    """
    if "/" in tok:
        return abs(v - val) <= 5.1e-5
    if "." in tok:
        decimals = len(tok.split(".")[-1])
        try:
            q = Decimal(1).scaleb(-decimals)
            return Decimal(repr(float(v))).quantize(q, rounding=ROUND_HALF_UP) \
                == Decimal(tok)
        except InvalidOperation:
            return abs(v - val) <= 0.5 * 10 ** (-decimals)
    return abs(v - val) <= 0.5


def any_match(v, tokens):
    return any(value_matches(v, val, tok) for val, tok in tokens)


# `compare` with "order": "relation" has an answer of "<", ">" or "=" — no
# numeric token at all, so the numeric binding below found nothing to check and
# `continue`d past the problem. A key printing \ans{>} against a verified "<"
# passed as "every verified answer is boxed". Found in an eval run, on a sheet
# this repository had itself produced.
RELATIONS = {"<", ">", "=", "<=", ">=", "\\le", "\\ge", "\\leq", "\\geq"}
RELATION_ALIASES = {"<=": ("<=", "\\le", "\\leq"), ">=": (">=", "\\ge", "\\geq"),
                    "<": ("<",), ">": (">",), "=": ("=",)}


def json_expected_relation(entry):
    """The relation an entry's answer IS, when its answer is a relation."""
    exp = entry.get("expected")
    if entry.get("type") == "compare" and isinstance(exp, str) and exp.strip() in RELATIONS:
        return exp.strip()
    return None


def boxed_relations(text):
    """Relation symbols appearing in boxed content, longest form first."""
    found = set()
    for token in ("\\leq", "\\geq", "\\le", "\\ge", "<=", ">=", "<", ">", "="):
        if token in text:
            found.add(token)
    return found


def json_expected_nums(entry):
    found = set()

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            found.add(float(v))
        elif isinstance(v, str):
            # same normalization as the printed side, so '(x - 3)*(x - 4)'
            # and '(x-3)(x-4)' extract the same values
            found.update(val for val, _ in num_tokens(v))
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    # only the ANSWER matters here: expected + solve_for target, not givens
    for key in ("expected",):
        if key in entry:
            walk(entry[key])
    return found


# ── Study-guide (box-segmented) structure rules ──────────────────────────────
# These fire ONLY when the document segments by examplebox/tryitbox — never on
# \problem or enumerate shapes — so answer keys are untouched.

def box_pairing_errors(tex, kinds):
    """Faded-scaffolding pairing (SKILL.md step 3): every examplebox is
    immediately followed by its tryitbox in the SAME skill section, and every
    tryitbox re-parameterizes the examplebox directly before it. A guide with
    worked examples and no try-its fails here — the student's first retrieval
    attempt must come before worksheet problem 1."""
    errs = []
    headings = [m.start() for m in re.finditer(r"\\skillheading", tex)]
    for idx, (a, b, kind) in enumerate(kinds):
        if kind == "examplebox":
            nxt = kinds[idx + 1] if idx + 1 < len(kinds) else None
            if nxt is None or nxt[2] != "tryitbox" \
                    or any(b <= h < nxt[0] for h in headings):
                errs.append(
                    f"box {idx + 1} (examplebox) has no try-it: study guides "
                    "pair every worked example with a try-it the student "
                    "attempts before the worksheet — add a tryitbox per "
                    "examplebox, in the same skill section (SKILL.md step 3).")
        else:  # tryitbox
            if idx == 0 or kinds[idx - 1][2] != "examplebox":
                errs.append(
                    f"box {idx + 1} (tryitbox) does not follow a worked "
                    "example — a try-it re-parameterizes the examplebox "
                    "directly before it (SKILL.md step 3).")
    return errs


def role_agreement_errors(kinds, by_id):
    """Positional role check: the k-th box is a tryitbox iff the JSON entry
    bound to position k carries \"role\": \"tryit\". A swapped tag would bind
    a try-it's answer against a worked example's value (or vice versa), so a
    mismatch is drift, not style."""
    errs = []
    for i in sorted(by_id):
        if i - 1 >= len(kinds):
            continue
        kind = kinds[i - 1][2]
        roles = {e.get("role") for e in by_id[i]}
        is_tryit = "tryit" in roles
        if is_tryit and kind != "tryitbox":
            errs.append(
                f"JSON entry {i} is tagged \"role\": \"tryit\" but box {i} "
                f"is a {kind} — reorder the entries to document order "
                "(example, try-it, example, try-it) or fix the tag.")
        elif not is_tryit and kind == "tryitbox":
            errs.append(
                f"box {i} is a tryitbox but JSON entry {i} carries no "
                "\"role\": \"tryit\" tag — tag the try-it's entry so its "
                "answer binds to the right box.")
    return errs

def expected_strings(entry):
    """String leaves of `expected` — the undeclared-unit gate must not flag a
    word the verified answer itself contains (\\text{undefined})."""
    out = []

    def walk(v):
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    walk(entry.get("expected"))
    return out


_ALPHA = re.compile(r"[A-Za-z]")

# String leaves that are BOOKKEEPING, not algebra. An interval's endpoint
# markers and infinities are the shape verify.py's `inequality`/`interval`
# types store their answer in ("expected": ["-oo", 18, "loopen"]), and every
# one of them contains a letter. Reading them as "this answer is an
# expression" would switch a boundary value to magnitude matching, and an
# inequality's boundary sign IS its answer: x > 7 and x > -7 are different
# answers, so nothing about them should be sign-blind. Measured — with these
# counted as symbolic, a sweep that flipped one boxed sign per key lost 14
# detections across the 600 recorded keys and 600 study guides, every one of
# them an inequality.
_NOT_EXPRESSIONS = {"oo", "-oo", "+oo", "open", "closed", "loopen", "hiopen",
                    "ropen", "true", "false", "none", "nan"}


def expected_is_symbolic(entry):
    """Does this entry's ANSWER contain algebra, wherever it is stored?

    This used to read the top level only:

        isinstance(e.get("expected"), str) and re.search("[A-Za-z]", ...)

    so "18 - 3*x/2" was symbolic and ["18 - 3*x/2"] — the SAME mathematics, and
    the shape `--schema` prints for `solve` — was not. verify.py accepts both
    forms identically, so the JSON shape alone decided whether the magnitude
    branch below ran. When it did not, a correct key boxing y = -3/2 x + 18
    tokenised to {-1.5, 18} against JSON numbers {18, 3, 2} and produced eight
    binding failures on one sheet, every one of them reading "the boxed value is
    wrong" and pointing at an answer key that was right. Unwrapping the list in
    the JSON cleared all eight without touching the key — i.e. the gate was
    asking the author to edit verified data to suit the checker.

    The same asymmetry kept sign matching strict on ["7*I", "-7*I"], so
    \\ans{x = \\pm 7i} failed as "boxed as 7 without its sign".

    So walk the structure, exactly the way json_expected_nums already walks it
    for the values themselves — the two must agree about what an answer IS.
    A list of purely numeric strings (["5", "-2"]) stays non-symbolic and keeps
    strict sign, which is where a sign error still IS the wrong answer.
    Interval bookkeeping (_NOT_EXPRESSIONS) is not algebra either.
    """
    return any(_ALPHA.search(s) and s.strip().lower() not in _NOT_EXPRESSIONS
               for s in expected_strings(entry))


# `equiv` verifies a whole EXPRESSION, written as lhs - rhs. It is the correct
# type for every "rewrite in this form" task, and it is the one type whose
# `expected` is not a value at all — so the numeric binding below, which asks
# "is each verified number in the box?", asks the wrong question of it. A study
# guide boxing \ans{25} for "(x-4)**2 + (y+1)**2 - 25" drew three faults reading
# "verified value 1 ... 2 ... 4 is in the worked steps but NOT in the box — the
# boxed value is wrong". The boxed value was not wrong; the rule is that the
# whole rewritten form belongs in the box. The author is then sent hunting for
# an arithmetic error that does not exist, three times over for one entry.
#
# The values still have to be bound — an equiv key that drops a term is a real
# fault — but they are reported ONCE, as what they are.
EQUIV_TYPES = {"equiv"}


def equiv_forms(entries):
    """The `expected` expressions of this problem's equiv entries."""
    return [e["expected"] for e in entries
            if e.get("type") in EQUIV_TYPES and isinstance(e.get("expected"), str)]


def main():
    # comments are blanked (length-preserving) so a commented-out \boxed or
    # '% \problem{...}' remark can neither count as an answer nor split a
    # segment; spans from segment_spans stay valid against this text
    tex = blank_comments(open(sys.argv[1]).read())
    data = json.load(open(sys.argv[2]))
    boxes = boxed_answers(tex)
    spans = segment_spans(tex)

    by_id = {}
    for e in data.get("problems", []):
        if isinstance(e, dict) and isinstance(e.get("id"), int):
            by_id.setdefault(e["id"], []).append(e)
    pc = data.get("problem_count")
    problem_count = pc if isinstance(pc, int) and pc > 0 else len(by_id)

    if not boxes:
        print("⚠ no \\boxed{}/\\ans{} answers found — box every final answer so "
              "printed answers can be bound to the verified JSON.")
        sys.exit(1)

    print(f"Answer-key binding: {sys.argv[1]}")
    if spans is None:
        # A key that cannot be segmented cannot be bound per problem, and a
        # whole-document fallback is exactly what let shuffled keys pass.
        print("  ❌ no problem structure found: use \\problem{...}, an "
              "enumerate \\item per problem, or one examplebox per worked "
              "example, so each printed answer can be bound to its problem.")
        sys.exit(1)

    segments = [tex[a:b] for a, b in spans]
    print(f"  {len(boxes)} boxed answers · {len(segments)} problem segments")

    # Box-segmented (study-guide) documents only: the segmenter fell through
    # to examplebox/tryitbox iff the box spans ARE the segment spans.
    kinds = box_spans(tex)
    box_mode = kinds is not None and [(a, b) for a, b, _ in kinds] == spans
    if box_mode:
        pairing = box_pairing_errors(tex, kinds)
        if pairing:
            for e in pairing:
                print(f"  ❌ {e}")
            sys.exit(1)

    if len(segments) != problem_count:
        print(f"  ❌ segment/problem count mismatch: the key splits into "
              f"{len(segments)} problem segment(s) but the verified JSON has "
              f"{problem_count} problems — give every problem its own "
              "segment (and boxed answer) so answers cannot shift.")
        sys.exit(1)

    if box_mode:
        role_errs = role_agreement_errors(kinds, by_id)
        if role_errs:
            for e in role_errs:
                print(f"  ❌ {e}")
            sys.exit(1)

    # The hard per-problem gate assumes every box belongs to a segment. A key
    # that prints answers outside the list (answer-bank style) degrades to
    # the whole-document presence check — loudly, never silently.
    outside = [s for s, _ in boxes if not any(a <= s < b for a, b in spans)]
    strict = not outside
    if outside:
        print(f"  ⚠ {len(outside)} boxed answer(s) sit outside every problem "
              "segment — per-problem binding DEGRADED to whole-document "
              "presence. Move final answers into their problem's segment to "
              "restore the hard per-problem gate.")

    seg_boxes = []   # per segment: number tokens of its concatenated boxes
    seg_box_text = []  # ...and their raw text, for answers that are not numbers
    for a, b in spans:
        content = " | ".join(c for s, c in boxes if a <= s < b)
        seg_boxes.append(num_tokens(content))
        seg_box_text.append(content)
    doc_tokens = num_tokens(tex)

    hard = []      # per-problem binding failure — wrong/missing boxed value
    soft = []      # degraded mode only: printed elsewhere, not in own segment
    equiv_faults = []  # an equiv answer whose rewritten form is not fully boxed
    for i in sorted(by_id):
        entries = by_id[i]
        if all(e.get("type") == "manual" for e in entries):
            continue
        relations = {r for r in (json_expected_relation(e) for e in entries) if r}
        if relations:
            printed = boxed_relations(seg_box_text[i - 1]
                                      if i - 1 < len(seg_box_text) else "")
            for r in sorted(relations):
                if not (printed & set(RELATION_ALIASES.get(r, (r,)))):
                    where = ("no relation symbol is boxed in this problem"
                             if not printed
                             else f"the boxed relation is {sorted(printed)[0]!r}")
                    hard.append((i, r, f"is the verified comparison, but {where}"))
        # Provenance is kept, not just the union: which ENTRY a value came from
        # decides how a miss should be explained, and an `equiv` entry's numbers
        # are pieces of one expression rather than answers in their own right.
        per_entry = [(e, json_expected_nums(e)) for e in entries]
        expected = set().union(*(nums for _, nums in per_entry))
        # 0 was filtered as "trivial", which meant a problem whose ANSWER is
        # zero had no printed-answer binding at all: the key could box 42 and
        # the gate still reported "every verified answer is boxed in its own
        # problem". Zero is an answer like any other. It is dropped only when
        # the entry has other expected values too — there it is an incidental
        # coordinate or coefficient rather than the answer being claimed.
        if len(expected) > 1:
            expected = {v for v in expected if abs(v) > 1e-9}
        # A leading minus is a SIGN; a mid-expression minus is an OPERATOR. So
        # one answer changes token set with term order: JSON "-1/x**2+6*x" gives
        # -1, while the identical box "6x - 1/x^2" gives +1, and binding failed.
        # Agents were reordering correct answer keys to satisfy the checker. For
        # a SYMBOLIC answer the sign is carried by the printed expression, not by
        # a token, so those are matched on magnitude. A purely numeric answer
        # keeps strict sign — that is where a sign error IS a wrong answer.
        symbolic = any(expected_is_symbolic(e) for e in entries)
        # A ± PAIR IS TWO ANSWERS, and collapsing it to one magnitude would let
        # a key print either root and pass. Measured: with a flat collapse, a
        # mutation sweep over the 600 recorded keys planting one wrong digit or
        # one flipped sign lost 17 detections, every one of them a solution set
        # where {7, -7} became {7} and the surviving root covered for the broken
        # one. So the collapse still happens — that is what stops a correct key
        # failing because "6x - 1/x^2" tokenises +1 against a JSON -1 — but a
        # magnitude the expected set holds in BOTH signs is remembered, and the
        # box has to print both.
        #
        # "Holds both signs" is read from ONE entry's SOLUTION SET — a list
        # `expected` — and nowhere else. Taking it off the merged set instead
        # produced four false failures across the 600 recorded keys, every one
        # an incidental pairing rather than two roots: "-25/(25 - x**2)**(3/2)"
        # yields -25 from the numerator and +25 from inside the denominator of
        # the SAME expression, and an equiv "2*(x + 4)" sat beside a solve [-4]
        # in another. Neither is a ± answer and neither key was wrong.
        pm_pairs = set()
        if symbolic:
            for e, _ in per_entry:
                if not isinstance(e.get("expected"), list):
                    continue
                roots = set()
                for r in e["expected"]:
                    roots |= json_expected_nums({"expected": r})
                pm_pairs |= {abs(v) for v in roots
                             if abs(v) > 1e-9 and -v in roots}
            expected = {abs(v) for v in expected}
        forms = equiv_forms(entries)
        equiv_nums, other_nums = set(), set()
        for e, nums in per_entry:
            got = {abs(v) for v in nums} if symbolic else set(nums)
            if e.get("type") in EQUIV_TYPES:
                equiv_nums |= got
            else:
                other_nums |= got
        # A literal that only an equiv entry claims is a piece of that entry's
        # expression; one that another entry also claims is a value in its own
        # right and keeps the ordinary diagnosis.
        equiv_only = equiv_nums - other_nums
        equiv_missing = []

        def unsigned(val, tok):
            """Magnitude AND the text that prints it, moved together.

            Mapping the value to abs() while leaving the token as '-0.33' was a
            half-conversion, and value_matches reads the TEXT for a decimal (to
            honour its written precision): it compared Decimal('0.33') against
            Decimal('-0.33') and failed. Only negative DECIMALS in symbolic
            problems were affected — integers take a branch that compares parsed
            values — so a correct key boxing a negative decimal beside a
            symbolic answer was rejected. The author's fix was to change the
            problem's initial condition so the answer came out positive: the
            checker rewrote the mathematics.

            Worth being plain about what this widens: a sign-only error on a
            decimal, in a problem that also carries a symbolic answer, now
            passes — as integers in the same position always have. It is not a
            check that was working and has been loosened; in that position the
            correct answer could not pass either. Strict sign still holds for
            purely numeric problems, which is where a sign error IS the wrong
            answer.
            """
            return abs(val), tok.lstrip("-") if "-" in tok[:1] else tok
        if not expected:
            continue
        seg = segments[i - 1] if i - 1 < len(segments) else ""
        for v in expected:
            box_toks = seg_boxes[i - 1] if i - 1 < len(seg_boxes) else []
            if symbolic:
                box_toks = [unsigned(val, tok) for val, tok in box_toks]
                for val, tok in list(box_toks):
                    if "/" in tok:
                        for part in tok.split("/"):
                            try:
                                box_toks.append(unsigned(float(part), part))
                            except ValueError:
                                pass
            raw_toks = seg_boxes[i - 1] if i - 1 < len(seg_boxes) else []
            if v in pm_pairs and strict:
                # Both roots have to be on the page. \pm counts as both (see
                # _PM), so \ans{\pm 7i} satisfies this and \ans{7i} does not.
                missing = [s for s in (1, -1)
                           if not any_match(s * v, raw_toks)]
                if missing:
                    hard.append((i, v, f"and {-v:g} are BOTH verified answers "
                                 f"— a ± pair — but only one sign is boxed. "
                                 f"Print both roots: \\ans{{\\pm {v:g}}}, or "
                                 f"\\ans{{{v:g} \\text{{ or }} {-v:g}}}"))
                continue
            if strict:
                if any_match(v, box_toks):
                    continue
                # An `equiv` answer is an EXPRESSION. Its literals are collected
                # and reported once, below, as the one thing that is actually
                # wrong — the rewritten form is not all inside a box.
                if v in equiv_only:
                    equiv_missing.append(v)
                    continue
                # A negative answer whose magnitude IS boxed is almost always
                # a detached sign: "k = - 2" tokenises as +2, because a minus
                # with a space after it is indistinguishable from the
                # subtraction in "3|x-5| - 2" without parsing the expression.
                # Both readings are defensible, so the checker cannot resolve
                # it — but the generic message ("the boxed value is wrong")
                # sends the author looking for an arithmetic slip that is not
                # there. Say what is actually different.
                if v < 0 and any_match(abs(v), box_toks):
                    hard.append((i, v, f"is boxed as {abs(v):g} without its "
                                 f"sign. If the sign is printed, put it against "
                                 f"the digit — \\ans{{-{abs(v):g}}}, not "
                                 f"\\ans{{- {abs(v):g}}} — a detached minus "
                                 f"cannot be told from a subtraction"))
                    continue
                # diagnose, don't just fail: was the right number nearby?
                if any_match(v, num_tokens(seg)):
                    hard.append((i, v, "is in the worked steps but NOT in the "
                                 "\\boxed{}/\\ans{} answer — the boxed value "
                                 "is wrong; box the verified answer"))
                else:
                    # diagnosis is tighter than the gate: a coarse integer
                    # box within 0.5 must not misattribute a swap
                    others = [k + 1 for k, toks in enumerate(seg_boxes)
                              if k != i - 1
                              and any(abs(v - val) <= 1e-4 for val, _ in toks)]
                    if others:
                        hard.append((i, v, "is boxed under problem "
                                     f"{others[0]} instead — swapped or "
                                     "shifted key"))
                    else:
                        hard.append((i, v, "is not printed in this problem's "
                                     "segment — transcription drift"))
            else:
                if not any_match(v, doc_tokens):
                    if v in equiv_only:
                        equiv_missing.append(v)
                    else:
                        hard.append((i, v, "appears NOWHERE in the answer key — "
                                     "transcription drift"))
                elif not any_match(v, num_tokens(seg)):
                    soft.append((i, v))

        # ONE fault per equiv entry, naming the type and the rule, instead of
        # one "the boxed value is wrong" per literal in the expression.
        if equiv_missing:
            missing = ", ".join(f"{v:g}" for v in sorted(set(equiv_missing)))
            shown = "; ".join(forms) if forms else "the verified expression"
            equiv_faults.append(
                f"problem {i}'s answer is an EXPRESSION, not a value: this "
                f"entry is \"type\": \"equiv\", so verify.py checked the whole "
                f"rewritten form ({shown}) rather than any single number. Box "
                f"that whole form — \\ans{{}} must hold the complete rewritten "
                f"expression, not one number out of it. Missing from the "
                f"boxed answer: {missing}. (If a literal really is absent from "
                f"your rewritten form, the form itself is wrong; nothing here "
                f"says a boxed VALUE is wrong.)")

    # ── Unit binding (tests/_units.py) ───────────────────────────────────────
    # Forward: a declared answer_unit must be printed inside the problem's own
    # boxed answer. Reverse: a lexicon unit printed in a box the JSON never
    # declared is unverified decoration — precisely the hole that let a key
    # answer a metres problem in feet while every numeric gate stayed green.
    unit_faults = []
    for i in sorted(by_id):
        entries = by_id[i]
        if all(e.get("type") == "manual" for e in entries):
            continue
        declared = [e["answer_unit"] for e in entries
                    if isinstance(e.get("answer_unit"), str)]
        if strict and i - 1 < len(spans):
            a, b = spans[i - 1]
            content = " | ".join(c for s, c in boxes if a <= s < b)
        else:
            content = " ".join(c for _, c in boxes)
        for u in declared:
            if not unit_in(content, u):
                unit_faults.append(
                    f"problem {i}'s boxed answer must print its verified unit "
                    f"'{u}' — add \\text{{{u}}} inside \\ans{{}}/\\boxed{{}}")
        # Words that will print run together. A box is set in math mode, so
        # \ans{no solution} reaches the student as "nosolution" — clean log,
        # every gate green, wrong on the page. Nothing else in the chain reads
        # a box as prose.
        for _, box_body in ((s2, c2) for s2, c2 in boxes
                            if not strict or (i - 1 < len(spans)
                                              and spans[i - 1][0] <= s2 < spans[i - 1][1])):
            for run in lost_spaces(box_body):
                unit_faults.append(
                    f"problem {i}'s boxed answer will print {run.split()[0]}"
                    f"{run.split()[1]} — a box is typeset in math mode, where "
                    f"spaces vanish. Wrap the words: \\text{{{run}}}")
        exp = [s for e in entries for s in expected_strings(e)]
        for u in undeclared_units(content, exp, declared):
            unit_faults.append(
                f"problem {i}'s key prints unit '{u}' that the verified JSON "
                f"never declares — add \"answer_unit\": \"{u}\" to problem {i} "
                f"so the unit is verified, or remove it")

    for pid, v, why in hard:
        shown = v if isinstance(v, str) else f"{v:g}"
        print(f"  ❌ problem {pid}: verified value {shown} {why}.")
    for msg in equiv_faults:
        print(f"  ❌ {msg}")
    for msg in unit_faults:
        print(f"  ❌ {msg}.")
    for pid, v in soft:
        print(f"  ⚠ problem {pid}: verified value {v:g} not in its own segment "
              "(printed elsewhere) — check problem/answer alignment.")

    if hard or unit_faults or equiv_faults:
        print(f"\n❌ {len(hard) + len(unit_faults) + len(equiv_faults)} binding "
              "failure(s) — fix the key before delivering.")
        sys.exit(1)
    if soft:
        print(f"\n⚠ {len(soft)} alignment warning(s) — heuristic, review by eye.")
        sys.exit(0)
    if strict:
        print("\n✅ every verified answer is boxed in its own problem")
    else:
        print("\n✅ every verified answer appears in the answer key")


if __name__ == "__main__":
    main()
