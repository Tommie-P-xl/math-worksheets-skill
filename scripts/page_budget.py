#!/usr/bin/env python3
r"""
page_budget.py — derive a worksheet's page budget from what it actually asks
of the student, instead of a flat cap.

Usage: python3 scripts/page_budget.py <verify.json> [--doc ws|ak]
                [--paper letter|a4|legal] [--max-pages]
                [--from-tex ws.tex | --type-size 17pt --accessible large]

WHY THIS EXISTS
A single number ("worksheets may not exceed 8 pages") is wrong in both
directions at once. Fifty linear-graphing problems each need their own
coordinate plane and legitimately run past twenty pages; a flat cap fails that
sheet, and the only way to pass is to shrink the planes or drop the workspace,
which is exactly the compression this system exists to prevent. Meanwhile ten
arithmetic drills that somehow filled eight pages sail through the same cap
while wasting seven sheets of a school's paper budget.

So the budget is COMPUTED from the problem set: how many problems, and how much
room each kind of problem deserves. The gate then asks the only question worth
asking — did this sheet land where its own content says it should? — and it is
two-sided:

  too many pages  -> bloat: paper spent on layout accident, not on work space
  too few pages   -> compression: the work space was squeezed to fit

Space is never the thing that gives. If a sheet needs more pages, it gets them;
the budget moves. What the gate refuses is a page count that does not match the
work the sheet contains.

COST MODEL (cm of column height, worksheet geometry: 24.1cm usable per page)
Each problem costs a fixed overhead plus the workspace its kind deserves. The
workspace figures are SKILL.md's own guidance (~5cm standard, 8cm multi-step,
10cm+ for graphs), and the overheads are measured from the shipped preamble.

Per problem:
  0.4cm  \problem lead-in
  0.6cm  stem (1.2cm when the stem is a word problem: longer prose wraps)
  0.3cm  answer line
  + workspace by class (below)
  + 5.0cm when the problem carries a figure (a coordinate plane or geometric
    figure is ~9cm tall and partly overlaps the workspace the student would
    otherwise use)

Two-column drill sheets pack two problems per row, so a sheet whose problems are
ALL compact is charged half the per-problem height. Compact means the room a
problem ACTUALLY gets — what its author declared, or the type default when
nobody declared anything — not what its type would have got by default.

A problem's several verifier entries are one BLOCK on the page, so the budget
merges them: the block is charged the tallest workspace any of its entries
claims, carries a figure if any entry does, and is a word problem if any entry
says so. Reading those facts off the first entry alone is what made the budget
under-measure and then fail correct sheets at compile.

Exit 0 always when the JSON parses (this computes a budget, it does not judge a
document). --max-pages prints just the ceiling, for build.sh to pass to
compile.sh. Exit 2 on unreadable/oversized input.
"""
import json
import math
import os
import re
import sys

# Usable column height per page at the worksheet's margins (top/bottom 0.75in
# = 1.905cm each). US Letter is the default because that is what the schools
# this was built for use; A4 is 1.8cm taller per page, which is a real
# difference over a long set (about one page saved every fourteen), so the
# budget must know which one it is sizing for rather than assume.
PAPER_CM = {
    "letter": 27.94 - 2 * 1.905,   # 8.5 x 11in
    "a4":     29.70 - 2 * 1.905,   # 210 x 297mm
    "legal":  35.56 - 2 * 1.905,   # 8.5 x 14in
}
DEFAULT_PAPER = "letter"

# A worksheet is a practice set, not a workbook. Beyond this the request is
# better served as several worksheets, which also print and grade better.
MAX_PROBLEMS = 100

OVERHEAD_CM = 0.4 + 0.3          # lead-in + answer line
STEM_CM = 0.6
WORD_PROBLEM_STEM_CM = 1.2
FIGURE_CM = 5.0

COMPACT, STANDARD, MULTISTEP = 3.0, 5.0, 8.0

# verify type -> workspace class. Unknown types fall back to STANDARD, which is
# the middle of the range: a new check type can never silently make the budget
# absurdly tight or absurdly loose.
WORKSPACE = {
    "compare": COMPACT, "estimate": COMPACT, "read_data": COMPACT,
    "probability": COMPACT,

    "solve": STANDARD, "zeros": STANDARD, "factor": STANDARD,
    "expand": STANDARD, "eval": STANDARD, "slope": STANDARD,
    "distance": STANDARD, "midpoint": STANDARD, "stats": STANDARD,
    "equiv": STANDARD, "approx": STANDARD,

    "system": MULTISTEP, "inequality": MULTISTEP, "series": MULTISTEP,
    "limit": MULTISTEP, "diff": MULTISTEP, "integrate": MULTISTEP,
    "definite_integral": MULTISTEP, "triangle": MULTISTEP,
    "solve_interval": MULTISTEP, "polygon_area": MULTISTEP,

    # open reasoning: a proof, sketch or explanation needs room to write prose
    "manual": MULTISTEP,
}

# How far the actual page count may sit from the computed ideal before the gate
# objects. Pagination is lumpy — a problem that will not fit at the foot of a
# page moves whole to the next one — so the ideal is a target, not an identity.
SLACK_OVER = 2      # pages of pagination slop allowed above the ideal
SLACK_UNDER = 0.30  # fraction below the ideal that counts as compression


# ── Type size ───────────────────────────────────────────────────────────────
# Every cm above is measured at 12pt. SKILL.md offers large-print and
# dyslexia-friendly output and promised "the page budget adapts automatically;
# larger type simply means more pages" — and it did not adapt at all: nothing
# here knew the document's point size, so a large-print sheet was sized against
# 12pt constants. Measured, not estimated: a prose-heavy 10-problem sheet is 4
# pages at 12pt against a ceiling of 4, and 5 pages at 17pt. The gate failed a
# correct accessible worksheet, and the only edits that would have satisfied it
# were cutting problems or shortening stems — the compression this module exists
# to refuse.
#
# The factors are the typeset height of one identical paragraph in each of the
# twelve documented configurations, divided by its height at 12pt. They are
# measured because they are not derivable: \accessiblemode raises leading on top
# of the point size, so 14pt large-print text is 1.69x tall, not the 1.17x its
# point size suggests. Reproduce with tests/test_page_budget_type_size.py.
#
# Only TEXT scales. workspace_cm is a physical measurement the author declares
# in centimetres and \problem lays down as literal vertical space, and a figure
# is drawn at a fixed size — neither moves when the type does.
TEXT_SCALE = {
    ("12pt", "none"): 1.00, ("12pt", "large"): 1.22,
    ("12pt", "dyslexia"): 1.44, ("12pt", "both"): 1.44,
    ("14pt", "none"): 1.38, ("14pt", "large"): 1.69,
    ("14pt", "dyslexia"): 1.69, ("14pt", "both"): 1.69,
    ("17pt", "none"): 1.77, ("17pt", "large"): 2.17,
    ("17pt", "dyslexia"): 2.57, ("17pt", "both"): 2.57,
}
DEFAULT_SIZE, DEFAULT_ACCESS = "12pt", "none"


def text_scale(size=DEFAULT_SIZE, access=DEFAULT_ACCESS):
    """Scale factor for text-derived costs. Unknown combinations fall back to
    the largest factor for that point size, then to 12pt: a size this table has
    not measured must not be charged LESS than one it has."""
    if (size, access) in TEXT_SCALE:
        return TEXT_SCALE[(size, access)]
    same_size = [v for (sz, _), v in TEXT_SCALE.items() if sz == size]
    return max(same_size) if same_size else TEXT_SCALE[(DEFAULT_SIZE, DEFAULT_ACCESS)]


# ── What the JSON cannot see ────────────────────────────────────────────────
# A stem is charged a flat 0.6cm (1.2cm for a word problem), which is right for
# a sentence and badly wrong for a stem holding a coordinate grid, a ten-frame,
# or a table to fill in. Three separate authors in one run hit the same wall in
# the same way: every pre-compile gate green, then compile-ws failing by one
# page, fixed by declaring workspace_cm covering the block's real height. The
# budget could not have known — it reads the JSON, and the picture is in the .tex.
#
# It CAN know now that --from-tex exists, so it says so BEFORE three compiles
# run rather than after. Deliberately a note and not a charge: a tikzpicture's
# height is whatever its author drew, and guessing it would trade a rebuild the
# author can fix for a budget nobody can predict. What the note does is name the
# problem, quote the height its own axis declares when it declares one, and ask
# for the one number only the author knows.
STEM_PICTURE_RE = re.compile(
    r"\\begin\{(tikzpicture|axis|tabular|tabularx)\}|\\probfig\b|\\includegraphics\b")
DECLARED_HEIGHT_RE = re.compile(r"\bheight\s*=\s*([\d.]+)\s*(cm|mm|in|pt)")
PROBLEM_USE_RE = re.compile(r"\\problem(?:\[[^\]]*\])?\{")


def stem_regions(tex):
    r"""Each \problem block's text, in document order — same region convention as
    check_layout: a block runs from one \problem use to the next, because the
    picture and the workspace sit AFTER the macro call, not inside its braces."""
    marks = [m.start() for m in PROBLEM_USE_RE.finditer(tex)]
    return [tex[a:b] for a, b in zip(marks, marks[1:] + [len(tex)])]


def unpriced_pictures(spec, tex):
    """[(problem_number, what_it_holds, declared_height_cm_or_None), ...]

    Only problems that declare NO workspace_cm are reported: declaring it is how
    an author takes responsibility for a block's real height, and repeating the
    warning afterwards would train people to ignore it.
    """
    regions = stem_regions(tex)
    if not regions:
        return []
    # SAME merge the charge uses, deliberately: this note and the cost model
    # must never again disagree about whether an author declared a workspace.
    # When they did, the note asked for a field the sheet already carried.
    order, merged = merged_problems(spec, require_int_id=True)
    ws_declared = {pid: m.get("workspace_declared") for pid, m in zip(order, merged)}
    out = []
    for i, region in enumerate(regions):
        pid = order[i] if i < len(order) else i + 1
        if ws_declared.get(pid):
            continue
        m = STEM_PICTURE_RE.search(region)
        if not m:
            continue
        h = DECLARED_HEIGHT_RE.search(region)
        cm = None
        if h:
            cm = to_cm_unit(float(h.group(1)), h.group(2))
        out.append((pid, m.group(1) if m.lastindex else m.group(0).strip("\\"), cm))
    return out


def to_cm_unit(value, unit):
    return value * {"cm": 1.0, "mm": 0.1, "in": 2.54, "pt": 0.0352778}.get(unit, 1.0)


def effective_workspace(p):
    """The workspace this problem ACTUALLY gets, in cm.

    A declared workspace_cm replaces the type default rather than adding to it:
    the author measured the block, the table only guessed at it. Everything that
    reasons about how much room a problem has must ask this one function —
    reading WORKSPACE directly is how the two-column halving came to be decided
    by a number no problem on the sheet was actually using (see budget()).
    """
    default = WORKSPACE.get(p.get("type", "manual"), STANDARD)
    ws = p.get("workspace_cm")
    # verify.py runs first and rejects a non-numeric workspace_cm, but this
    # module is also called directly, so it degrades to the type default rather
    # than dying on input it did not validate.
    try:
        return float(ws) if ws is not None else default
    except (TypeError, ValueError):
        return default


def merge_entries(entries):
    """One problem's several verifier entries collapsed into the one BLOCK the
    page gives them.

    Several checks bind to a single problem id — a numeric answer, a rubric for
    the explanation, a second part — and they arrive as separate JSON entries.
    The page does not care: \\problem lays down one block per id. So the facts
    that describe that block have to be gathered from ALL of the id's entries,
    not read off whichever one happens to be first.

    Keeping only the first entry is what this used to do, and it lost every
    workspace_cm an author wrote on a later one — while unpriced_pictures, forty
    lines up in this same file, merged across entries and therefore stayed
    quiet. The budget under-measured, the ceiling came out short, and the
    compile then failed the sheet asking the author to declare a field they had
    already declared. Reproduced in a run: the same numbers moved from the last
    entry of each id to the first took a sheet from 65cm to 129cm, ideal 3 to
    ideal 6, against a real 7 pages.

    WHERE ENTRIES DISAGREE THE BLOCK GETS THE TALLEST CLAIM. Each entry claims
    the room it needs — what it declared, or its type's default when it declared
    nothing — and the block has to hold all of them, so the block is as tall as
    the tallest. A problem that computes a value AND asks for the reasoning is
    two entries, `eval` and `manual`, and the writing part still needs its prose
    room whether or not the arithmetic part put a number on itself.

    That matters because a default is a CLAIM, not a blank. Taking only the
    declared numbers would let a 5.5cm written on the `eval` half quietly shrink
    the 8cm the `manual` half was asking for, and an author who declared one
    number for one check would have silently resized a part they never touched.
    Measured against the compiled page count of the 600 recorded worksheets:
    counting defaults as claims puts 50 more sheets closer to their real length
    and 7 further than reading the declared numbers alone. Single-entry problems
    — most of any sheet — are unaffected either way: the max of one number is
    that number.
    """
    merged = dict(entries[0])
    merged["workspace_cm"] = max(effective_workspace(e) for e in entries)
    # What the cost model charges and what the AUTHOR actually wrote are two
    # different questions, and the advisory note needs the second one: a block
    # sized by a type default has not been measured by anybody, and saying so is
    # the whole point of the note. Both answers come out of this one merge so
    # the charge and the note can never again disagree about the same sheet.
    declared = [e.get("workspace_cm") for e in entries]
    declared = [d for d in declared if d is not None]
    merged["workspace_declared"] = declared[0] if declared else None
    for e in entries:
        if isinstance(e.get("figure"), dict):
            merged["figure"] = e["figure"]
            break
    if any(e.get("word_problem") for e in entries):
        merged["word_problem"] = True
    return merged


def merged_problems(spec, require_int_id=False):
    """(ids in document order, one merged problem per id).

    The single place this module turns a verify JSON's entry list into the list
    of blocks a reader will see. Everything that counts problems, charges them
    or reports on them goes through here.
    """
    groups, order = {}, []
    for p in spec.get("problems", []):
        pid = p.get("id")
        if require_int_id and not isinstance(pid, int):
            continue
        if pid not in groups:
            groups[pid] = []
            order.append(pid)
        groups[pid].append(p)
    return order, [merge_entries(groups[i]) for i in order]


def problem_cost(p, scale=1.0):
    """Column height one problem deserves, in cm, at the document's type size."""
    stem = WORD_PROBLEM_STEM_CM if p.get("word_problem") else STEM_CM
    cost = (OVERHEAD_CM + stem) * scale + effective_workspace(p)
    if isinstance(p.get("figure"), dict):
        cost += FIGURE_CM
    return cost


def budget(spec, paper=DEFAULT_PAPER, size=DEFAULT_SIZE, access=DEFAULT_ACCESS):
    """Return the budget dict for a parsed verify JSON."""
    page_cm = PAPER_CM.get(paper, PAPER_CM[DEFAULT_PAPER])
    scale = text_scale(size, access)
    # one BLOCK per problem id: several checks may bind to the same problem, and
    # charging a problem twice would inflate the budget — but the id's facts are
    # spread across its entries, so they are merged rather than picked from the
    # first one. See merge_entries.
    _, unique = merged_problems(spec)

    declared = spec.get("problem_count", len(unique))
    costs = [problem_cost(p, scale) for p in unique]
    total = sum(costs)

    # PAGINATION IS QUANTISED AND THE SUM IS NOT. \problem wraps stem and
    # workspace in ONE unbreakable minipage, so a block taller than half the
    # column packs one per page and strands the rest of it. Four authors in one
    # run hit the same wall: a 12-problem sheet where every problem carries a
    # figure ran to 10 real pages against a ceiling of 7, and declaring
    # workspace_cm honestly moved the ceiling to 9 — still short, because the
    # sum never sees the stranded space. The gate then reads as "declare more
    # workspace_cm", and an author who follows it literally keeps inflating a
    # number that is supposed to be a measurement. That is the dishonest
    # direction, produced by a model that could not describe the page.
    #
    # So blocks that cannot share a page are charged what they actually take.
    # This RAISES ceilings; it never tightens one, because a sheet whose blocks
    # do pack is unaffected. The remedy the report names changes accordingly:
    # the fix for a one-per-page sheet is a shorter block, not a bigger number.
    tall = [c for c in costs if c > page_cm / 2]
    if tall:
        packed = sum(c for c in costs if c <= page_cm / 2)
        total = sum(math.ceil(c / page_cm) * page_cm for c in tall) + packed

    # AN ALL-COMPACT SHEET IS THE TWO-COLUMN DRILL FORMAT: TWO PER ROW, so it
    # is charged half height. What makes a sheet compact is the room its
    # problems actually get, and this used to ask the TYPE DEFAULT instead —
    # a number that stops being true the moment an author declares
    # workspace_cm, which is precisely when it matters.
    #
    # The types with the compact default are `compare` and `estimate` (and
    # `read_data`, `probability`): the elementary comparison and estimation
    # bands. So a sheet of eight compare problems each declaring 6cm of work
    # space, set as ordinary single-column \problem with no multicols anywhere
    # in the .tex, was silently charged half of what it had declared.
    # Reproduced by changing ONE type field and nothing else: 32.0cm -> 64.1cm,
    # ideal 2 -> 3, against a real 3 pages; a second sheet 43.8 against a true
    # 87.6, ideal 2 against a real 4.
    #
    # The consequence lands on the author twice. The ceiling derives from the
    # ideal, so the sheet gets one one to two pages tighter than its content
    # needs; and the remedy this module prints — declare more workspace_cm —
    # then buys half of every centimetre it declares, so following the advice
    # literally cannot close the gap. Asking effective_workspace ends both.
    all_compact = bool(unique) and all(
        effective_workspace(p) <= COMPACT
        and not isinstance(p.get("figure"), dict) for p in unique)
    if all_compact:
        total /= 2.0

    title_block_cm = 2.0 * scale             # title + rule + instruction line
    ideal = max(1, math.ceil((total + title_block_cm) / page_cm))
    return {
        "problems": len(unique),
        "declared_count": declared,
        "content_cm": round(total, 1),
        "ideal_pages": ideal,
        "max_pages": ideal + SLACK_OVER,
        "min_pages": max(1, math.floor(ideal * (1 - SLACK_UNDER))),
        "two_column": all_compact,
        "paper": paper,
        "tall_blocks": len(tall),
        "type_size": size,
        "accessible": access,
        "sheets_duplex": math.ceil(ideal / 2),
    }


def render(b, doc="ws"):
    lines = [
        f"Page budget ({doc}, {b['paper']}"
        + (f", {b['type_size']}"
           + (f" {b['accessible']}-print" if b.get("accessible", "none") != "none" else "")
           if b.get("type_size", DEFAULT_SIZE) != DEFAULT_SIZE
           or b.get("accessible", DEFAULT_ACCESS) != DEFAULT_ACCESS else "")
        + f"): {b['problems']} problems, "
        + f"{b['content_cm']}cm of content"
        + (" (two-column drill: charged at half height)" if b["two_column"] else ""),
        f"  ideal {b['ideal_pages']} page(s) · accepted range "
        f"{b['min_pages']}-{b['max_pages']} · "
        f"{b['sheets_duplex']} sheet(s) of paper double-sided",
    ]
    if b.get("tall_blocks"):
        n = b["tall_blocks"]
        lines.append(
            f"  NOTE: {n} problem block(s) are taller than half a page, so only "
            f"one fits per page and the rest of each page is stranded. The "
            f"budget charges for that. If this sheet is longer than you want, "
            f"the fix is a SHORTER BLOCK — a smaller figure, or workspace beside "
            f"the figure instead of under it — not a larger workspace_cm, which "
            f"raises the ceiling without recovering the stranded space.")
    for pid, what, cm in b.get("unpriced", []):
        lines.append(
            f"  NOTE: problem {pid}'s stem holds a {what} and declares no "
            f"workspace_cm, so it is charged {STEM_CM}cm like a one-line stem"
            + (f" — its own options say height={cm:.1f}cm" if cm else "")
            + ". Declare workspace_cm covering the block's real height, or this "
            "sheet will overrun the budget at compile time.")
    if b["max_pages"] > 12:
        lines.append(
            f"  NOTE: this set needs {b['ideal_pages']} pages of paper. If that is "
            f"more than intended, ask for fewer problems — do NOT shrink the work "
            f"space to fit, which is what makes a sheet unusable.")
    return "\n".join(lines)


SIZE_RE = re.compile(r"\\documentclass\s*\[([^\]]*)\]")
ACCESS_RE = re.compile(r"\\accessiblemode\s*\{\s*([a-z]+)\s*\}")


def read_type_size(tex_path):
    """(size, accessible-mode) as the document itself declares them.

    Reading the .tex is the only honest source: the verify JSON says nothing
    about type, and asking the author to pass flags that must agree with a file
    they already wrote is a rule that gets forgotten exactly when it matters —
    on the accessible sheet, which is the one a flat 12pt budget mis-sizes.
    A file that cannot be read falls back to the 12pt default rather than
    failing: this is a sizing hint, not a gate.
    """
    try:
        tex = open(tex_path, encoding="utf-8", errors="replace").read()
    except OSError:
        return DEFAULT_SIZE, DEFAULT_ACCESS
    size = DEFAULT_SIZE
    m = SIZE_RE.search(tex)
    if m:
        for opt in m.group(1).split(","):
            opt = opt.strip().lower()
            if re.fullmatch(r"\d+pt", opt):
                size = opt
    a = ACCESS_RE.search(tex)
    return size, (a.group(1) if a else DEFAULT_ACCESS)


def main():
    argv = sys.argv[1:]
    doc = "ws"
    if "--doc" in argv:
        i = argv.index("--doc")
        doc = argv[i + 1] if i + 1 < len(argv) else "ws"
        del argv[i:i + 2]
    paper = DEFAULT_PAPER
    if "--paper" in argv:
        i = argv.index("--paper")
        paper = (argv[i + 1] if i + 1 < len(argv) else DEFAULT_PAPER).lower()
        del argv[i:i + 2]
        if paper not in PAPER_CM:
            print(f"page_budget: unknown paper {paper!r}; known: "
                  f"{', '.join(sorted(PAPER_CM))}", file=sys.stderr)
            return 2
    size, access = DEFAULT_SIZE, DEFAULT_ACCESS
    tex_source = ""
    if "--type-size" in argv:
        i = argv.index("--type-size")
        size = (argv[i + 1] if i + 1 < len(argv) else DEFAULT_SIZE).lower()
        del argv[i:i + 2]
    if "--accessible" in argv:
        i = argv.index("--accessible")
        access = (argv[i + 1] if i + 1 < len(argv) else DEFAULT_ACCESS).lower()
        del argv[i:i + 2]
    # --from-tex reads both off the document, so build.sh never has to parse
    # LaTeX and an author never has to remember to pass two flags that must
    # agree with the file they already wrote.
    if "--from-tex" in argv:
        i = argv.index("--from-tex")
        tex_path = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
        size, access = read_type_size(tex_path)
        try:
            tex_source = open(tex_path, encoding="utf-8", errors="replace").read()
        except OSError:
            tex_source = ""
    only_max = "--max-pages" in argv
    if only_max:
        argv.remove("--max-pages")
    if len(argv) != 1:
        usage = next(line for line in __doc__.splitlines()
                     if line.startswith("Usage:"))
        print(usage, file=sys.stderr)
        return 2
    path = argv[0]
    if not os.path.exists(path):
        print(f"page_budget: no such file: {path}", file=sys.stderr)
        return 2
    try:
        spec = json.load(open(path))
    except Exception as e:                                  # noqa: BLE001
        print(f"page_budget: cannot parse {path}: {e}", file=sys.stderr)
        return 2

    b = budget(spec, paper, size, access)
    if tex_source:
        b["unpriced"] = unpriced_pictures(spec, tex_source)
    if b["problems"] > MAX_PROBLEMS:
        print(f"page_budget: {b['problems']} problems exceeds the {MAX_PROBLEMS}-problem "
              f"ceiling. Split this into several worksheets: past ~100 problems a "
              f"single sheet is a workbook, and it prints and grades worse than "
              f"two focused sets.", file=sys.stderr)
        return 2

    # the answer key holds worked solutions, not work space: it runs shorter
    # than the worksheet but never shorter than the problem list itself
    if doc == "ak":
        # +1: the generated bank now claims the LAST page for its verification
        # and curriculum summary (\AtEndDocument\clearpage), so every key is
        # one page longer than its solutions — and the rubber inter-problem
        # glue the key gained is already inside the 0.9 factor's slack.
        b["max_pages"] = max(3, math.ceil(b["ideal_pages"] * 0.9) + SLACK_OVER + 1)
        b["min_pages"] = 1

    if only_max:
        print(b["max_pages"])
    else:
        print(render(b, doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
