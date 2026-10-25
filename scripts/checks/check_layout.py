#!/usr/bin/env python3
r"""
check_layout.py — catch the layout faults that make a *correct* worksheet
unusable in front of a student.

Usage: python3 tests/check_layout.py <worksheet.tex> [--figs <figs.tex>]

Each fault below was found by generating a real sheet: every answer verified,
every figure label correct, and the printed page still misleading or unusable.
None is visible to verify.py, which only sees the JSON.

1. FIGURE SCOPE. A figure carrying numbers belongs to exactly one problem, but
   on the page it simply sits near several. If problem 6 has a triangle labelled
   a=6, b=8 and problems 7-8 have none, a student reading 7 sees a labelled
   triangle a few lines up and reasonably assumes it applies. The figure is
   correct and the worksheet is still wrong. Rule: within one problem list, no
   problem may be left with NO figure while another's figure carries values.
   Shared conventions belong in a value-free reference figure outside the list.

   What matters is the figureless problem, not the value-free one. A problem
   holding its own blank grid — "plot your counterexample here", "draw the line
   through these points" — is not at risk: the picture inside its block is
   visibly the one it means, and a grid's own axis numbers are scale, not
   another problem's data. Counting valued-against-total instead failed a sheet
   where all ten problems had a graph and three were empty axes to plot on, and
   the only edit that would have satisfied it was deleting those three grids.

2. WORK SPACE. Compact is the default; reserve writing room only on an explicit
   user request with \worksheetlayout{spacious}. In spacious mode ~5cm per
   problem or 8cm multi-step may be appropriate. The legacy floor applies only
   to that mode. Nothing
   enforced it, so a generator can emit itemsep=14pt (about half a line) and
   produce a sheet with nowhere to show work. Trig and multi-step algebra need
   three or four lines each. Space is credited from itemsep, signed \vspace
   (deliberate reclaiming with \vspace{-2.9cm} is charged, not ignored),
   \\[5cm] line skips, and the three standard skips — all of which put real
   ink-to-ink distance on the page. A BLANK plotting grid counts too: an empty
   coordinate plane is where the student writes, not a figure they read, and
   has_valued_figure already tells the two apart. A grid carrying data does not
   count, which is the same rule the message states.

3. PAGE-BREAK GLUE. LaTeX discards \vspace glue that falls at a page or column
   break, so workspace left outside a minipage silently vanishes exactly when
   its problem lands at a page bottom — a multi-page sheet loses the workspace
   of roughly one problem per page. The fix is structural: keep the workspace
   inside the problem's unbreakable minipage (\par\vspace*{5cm} before
   \end{minipage}, see references/latex-templates.md). A workspace-sized
   unstarred \vspace outside any minipage is therefore a fault. Starred
   \vspace* at least survives the break, so it is tolerated as a minimal fix.
   "Outside any minipage" includes the one \problem opens IN THE PREAMBLE:
   a \problem stem has no \begin{minipage} of its own to count, so glue written
   there is inside a minipage and is reported as a style note, never a fault.

4. ANSWER LOCATION. Bare workspace gives the grader nowhere to look and the
   student nothing to commit to — the final answer drowns in scratch work.
   Every enumerate \item must therefore contain one answer-location macro:
   \ansline (right-aligned blank), \ansblank (inline drill blank),
   \answerline{unit} (blank + measurement unit), or \noansline (explicit
   opt-out for problems whose worked product IS the answer — sketch, proof,
   construction). \problem regions are exempt BY DESIGN: the shipped
   preamble's \problem macro emits the answer line itself whenever its
   workspace argument is positive, so the document body shows nothing to
   count — construction, not linting, is the guarantee there. Rules run on
   comment-stripped text, so a commented-out marker can never satisfy this.

Both the enumerate/\item and the \problem{...} macro shapes are parsed — the
skill's first-taught template style is \problem, and a checker that only sees
enumerate lists passes a zero-workspace \problem sheet vacuously (the same
zero-parse failure class fixed in check_prose_consistency.py). Enumerate
parsing is DEPTH-AWARE via _tex_segments.enumerate_lists: every nested
part-list is checked as its own list against its own [itemsep=..], and a
naive regex that truncated the outer list at the first nested \end{enumerate}
(dropping every item after the multi-part problem) is gone.

Exit 0 clean, 1 on any fault, 2 when nothing parsed (no list and no \problem
block means nothing was checked — that is NOT a pass). Skips answer keys and
study guides, which are read rather than written on.
"""

import re
import sys

from _probfig import expand_probfigs, probfig_bodies
from _tex_segments import enumerate_lists

MIN_CM_PER_PROBLEM = 2.5      # floor only for explicitly spacious worksheets
# A worksheet page holds ~24cm of text. \problem wraps stem + workspace in ONE
# unbreakable minipage, so a workspace larger than the page cannot break and
# simply runs off the bottom margin: the engine reports "Overfull \vbox ...
# while \output is active", which check_log.py deliberately treats as a warning
# (vbox warnings are noisy on legitimately full pages). Nothing else catches it,
# so a 26cm workspace ships a sheet with content printed past the paper edge.
# Caught here instead, statically: no problem can legitimately ask for more
# workspace than a page has, so there is no false-positive direction.
MAX_CM_PER_PROBLEM = 20.0
UNIT_CM = {"cm": 1.0, "mm": 0.1, "in": 2.54, "pt": 0.0352778, "ex": 0.15, "em": 0.35}
# \bigskip/\medskip/\smallskip at their conventional sizes — coarse, but they
# are real writing room and ignoring them under-credits a legitimate sheet
SKIP_CM = {"bigskip": 0.42, "medskip": 0.28, "smallskip": 0.14}

# matches a \problem use site — \problem{...} or \problem[5cm]{...} (the macro
# takes the workspace as an optional first argument). Does NOT match the
# preamble's \newcommand{\problem}... definition: there the next char is `}`.
PROBLEM_RE = re.compile(r"\\problem(\[[^\]]*\])?\{")

# the answer-location macros the shipped preamble defines (rule 4). \b so a
# hypothetical \anslinesque never satisfies the rule.
ANSWER_RE = re.compile(r"\\(?:ansline|ansblank|answerline|noansline)\b")


def to_cm(value, unit):
    return float(value) * UNIT_CM.get(unit, 0.0)


def strip_comments(tex):
    """Blank TeX comments (unescaped % to end of line), preserving offsets.

    Commented-out material must neither satisfy a rule (a dead \\vspace{5cm}
    is not workspace) nor trip one (a comment MENTIONING \\vspace{5cm} is not
    stranded glue). Blanking instead of deleting keeps every reported line
    number true to the file the author is editing.
    """
    return re.sub(r"(?<!\\)%[^\n]*", lambda m: " " * len(m.group(0)), tex)


def blank_spans(text, spans, base=0):
    """Overwrite the given absolute spans with spaces inside text[base:...].

    Blanking (not deleting) keeps every remaining offset true to the source,
    the same discipline strip_comments follows."""
    chars = list(text)
    for a, b in spans:
        for i in range(max(a - base, 0), min(b - base, len(chars))):
            chars[i] = " "
    return "".join(chars)


def problem_regions(tex):
    """Each \\problem block as (workspace_cm_from_optional_arg, region, had_list).

    A region runs from one \\problem use to the next (or EOF): the workspace
    \\vspace and any figure live AFTER the macro call, so the trailing text —
    not just the braced stem — is what layout must see. Nested enumerate
    bodies are stripped (had_list=True): the multi-part template carries its
    workspace in the nested list's itemsep, which the enumerate pass already
    validates — counting the region's own \\vspace there would false-fail the
    skill's own template.
    """
    matches = list(PROBLEM_RE.finditer(tex))
    # depth-aware env spans: a naive .*? strip ends at the FIRST nested
    # \end{enumerate}, leaving the tail of a multi-part region in place —
    # the same truncation class enumerate_lists exists to kill
    env_spans = [span for _, span, _, _ in enumerate_lists(tex)]
    out = []
    for m, nxt in zip(matches, matches[1:] + [None]):
        start = m.start()
        end = nxt.start() if nxt else len(tex)
        region = tex[start:end]
        opt_cm = 0.0
        if m.group(1):
            o = re.search(r"(-?[\d.]+)\s*(cm|mm|in|pt|ex|em)", m.group(1))
            if o:
                opt_cm = to_cm(o.group(1), o.group(2))
        inner = [(a, b) for a, b in env_spans if a < end and b > start]
        stripped = blank_spans(region, inner, base=start)
        out.append((opt_cm, stripped, stripped != region))
    return out


# Unambiguous "there is a picture inside this problem" markers. Deliberately
# narrower than has_valued_figure's macro branch: this predicate can only make
# the scope rule MORE permissive, so it counts nothing it is not sure about.
FIGURE_ANY = re.compile(
    r"\\begin\{tikzpicture\}|\\begin\{axis\}|\\includegraphics\b|\\probfig\b")


def scope_note(valued, items):
    """The passing report, said accurately — including the mixed-but-clean case
    where some problems graph data and the rest hold their own blank grid."""
    if not valued:
        return f"none of the {len(items)} problems carries a valued figure"
    if len(valued) == len(items):
        return f"all {len(items)} problems carry valued figures"
    return (f"{len(valued)} of {len(items)} carry valued figures and every "
            f"other problem carries its own")


def has_own_figure(item):
    """Does this problem carry a picture of its own, valued or not?

    Anything has_valued_figure recognises counts, first and unconditionally —
    otherwise a macro-built figure (\\rtfig, \\probfig) is valued and figureless
    at the same time, and the scope rule reports every problem in the list as
    both. FIGURE_ANY only has to catch the pictures that carry NO values.
    """
    return has_valued_figure(item) or bool(FIGURE_ANY.search(item))


def has_valued_figure(item):
    """A figure whose visible labels contain a number: tikz \\node text, pic
    "..." quotes, figure-macro args, \\probfig{N}, or any \\includegraphics."""
    for fig in re.finditer(r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}", item, re.S):
        for node in re.finditer(r"\\node\b[^{]*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", fig.group(0)):
            if re.search(r"\d", node.group(1)):
                return True
        # pic-quote labels ("$34^\circ$") are printed values too — the taught
        # circle-angle template carries its ONLY numbers there. Same
        # extraction as check_prose_consistency.figure_label_numbers' pic
        # branch, so the two detectors cannot disagree about what counts as a
        # figure value. Accepted edge (fix both branches together if it ever
        # bites): a digit-subscripted label like $\theta_1$ counts as valued —
        # nothing in the repo emits one, and the failure direction is a loud
        # false FAIL, never a silent false PASS. Confined to the tikzpicture
        # body: straight-quoted prose digits elsewhere in the item must not
        # trip the figure rule.
        for q in re.finditer(r'"\s*\$?([^"$]*)\$?\s*"', fig.group(0)):
            if re.search(r"\d", q.group(1)):
                return True
    # pgfplots draws numeric tick labels BY DEFAULT, and it draws them as axis
    # ticks rather than as \node text, so the tikz scan above never saw them: a
    # coordinate plane with a full numbered grid read as value-free and the
    # all-or-nothing figure rule silently did not apply. Found by an eval agent
    # whose worksheet carried graphs on 3 of 12 problems and passed layout-ws
    # anyway. An axis therefore counts as valued unless BOTH tick sets are
    # explicitly emptied — the same "assume valued" stance as \includegraphics,
    # because the false direction here is a silent PASS.
    #
    # An axis that DRAWS NOTHING is exempt, and that exemption is not a
    # softening of the rule — it is the rule read correctly. The scope rule
    # exists because a valued figure sitting between two problems gets applied
    # to the wrong one. An empty numbered grid is a place to write, like the
    # \problem workspace above it; its numbers are the grid's own scale, and a
    # student cannot misread scale as another problem's data. Found on a
    # "plot a counterexample" problem, which is exactly the shape that needs a
    # blank plane and exactly the shape a value-carrying graph never has.
    seen = 0
    for ax in re.finditer(r"\\begin\{axis\}(?:\[(.*?)\])?(.*?)\\end\{axis\}",
                          item, re.S):
        seen += 1
        opts, body = ax.group(1) or "", ax.group(2) or ""
        if (re.search(r"xtick\s*=\s*\\empty", opts)
                and re.search(r"ytick\s*=\s*\\empty", opts)):
            continue
        # \addplot, \draw, \node, \fill — anything at all that puts marks
        # inside the axis makes it a figure again.
        if not re.search(r"\\[a-zA-Z]", re.sub(r"(?<!\\)%.*", "", body)):
            continue
        return True
    # An axis whose environment we could not read whole gets the assume-valued
    # treatment: the exemption above is only ever granted on evidence.
    if seen < len(re.findall(r"\\begin\{axis\}", item)):
        return True
    # \includegraphics is an opaque image: no checker can read the values it
    # almost certainly shows (a figure worth including carries labels), so it
    # must be ASSUMED valued and the all-or-nothing scope rule applies
    # unconditionally. check_prose_consistency additionally hard-fails it.
    if re.search(r"\\includegraphics\b", item):
        return True
    # macro-style figures: \rtfig{...}{$b=8$}... — any braced arg holding a
    # digit. The optional [..] arg (scale/styling, e.g. \rtfig[scale=1.2])
    # must neither defeat detection nor have its digits counted as values —
    # a macro the detector silently stops seeing is a false PASS on the
    # all-or-nothing figure rule, the dangerous direction.
    for mac in re.finditer(r"\\[a-zA-Z]*(?:rt|tri|fig)[a-zA-Z]*"
                           r"(?:\[[^\]]*\])?((?:\{[^{}]*\}){2,})", item):
        if re.search(r"\d", mac.group(1)):
            return True
    # \probfig{N} is generated by scripts/render_figures.py from the problem's
    # verified givens, so it ALWAYS carries values — but its single braced arg
    # is a problem index, which the two-args-with-a-digit test above cannot
    # see. Recognize the call itself, or a mixed \probfig/bare list would slip
    # past the all-or-nothing scope rule.
    if re.search(r"\\probfig\{\d+\}", item):
        return True
    return False


def space_cm(opts, item):
    """Vertical space a student gets for this problem."""
    cm = 0.0
    m = re.search(r"itemsep\s*=\s*([\d.]+)\s*(cm|mm|in|pt|ex|em)", opts)
    if m:
        cm += to_cm(m.group(1), m.group(2))
    # signed: \vspace{-2.9cm} after a 3cm itemsep leaves ~0.1cm of real room —
    # an unsigned sum credits space the student never gets
    for v in re.finditer(r"\\vspace\*?\{\s*(-?[\d.]+)\s*(cm|mm|in|pt|ex|em)\s*\}", item):
        cm += to_cm(v.group(1), v.group(2))
    # \\[5cm] line skips are workspace too — a sheet built on them is usable
    # and must not be rejected (that trains generators to route around the gate)
    for v in re.finditer(r"\\\\\*?\s*\[\s*(-?[\d.]+)\s*(cm|mm|in|pt|ex|em)\s*\]", item):
        cm += to_cm(v.group(1), v.group(2))
    for s in re.finditer(r"\\(bigskip|medskip|smallskip)\b", item):
        cm += SKIP_CM[s.group(1)]
    return cm


def problem_stem_spans(tex):
    r"""(start, end) of each \problem[..]{STEM} argument — brace-matched.

    The shipped preamble defines

        \newcommand{\problem}[2][0pt]{...\begin{minipage}{\linewidth}
            ... #2 \par\vspace*{#1} ... \end{minipage}\par}

    so the stem argument is typeset INSIDE the problem's minipage, and the
    minipage's \begin never appears in the document body at all. See
    stranded_workspace for what that broke.

    PROBLEM_RE is reused deliberately: it already declines to match the
    \newcommand definition itself (there the next character is `}`), so a
    document that redefines \problem locally is read the same way here.
    """
    out = []
    for m in PROBLEM_RE.finditer(tex):
        i, depth = m.end(), 1
        while i < len(tex) and depth:
            c = tex[i]
            if c == "\\":            # skip \{ and \} — escaped braces
                i += 2
                continue
            depth += (c == "{") - (c == "}")
            i += 1
        out.append((m.end(), i - 1))
    return out


def minipage_depth_fn(tex):
    r"""Return a pos -> minipage-nesting-depth function for this document.

    A \problem stem counts as one level of minipage even though no
    \begin{minipage} is written there: the macro opens one in the preamble.
    Counting only literal \begin{minipage} tokens made this function say
    "depth 0" for a position that is demonstrably inside a minipage.
    """
    stems = problem_stem_spans(tex)
    events = sorted([(m.start(), 1) for m in re.finditer(r"\\begin\{minipage\}", tex)] +
                    [(m.start(), -1) for m in re.finditer(r"\\end\{minipage\}", tex)] +
                    [(a, 1) for a, _ in stems] + [(b, -1) for _, b in stems])

    def depth_at(pos):
        d = 0
        for p, delta in events:
            if p >= pos:
                break
            d += delta
        return d
    return depth_at


def stranded_workspace(tex):
    r"""Workspace-sized unstarred \vspace outside any minipage (fault 3).

    Returns (faults, notes): faults are [(line, cm), ...] for glue that really
    is exposed to a page break; notes are [(line, cm), ...] for glue inside a
    \problem stem, which is a style remark, not a fault.

    THE MINIPAGE A \problem OPENS IS IN THE PREAMBLE, NOT IN THE BODY.
    This function used to count literal \begin{minipage} tokens in the document
    text, so an unstarred workspace \vspace written inside a \problem stem was
    reported as "sits outside any minipage" — on the sheet shape SKILL.md
    teaches FIRST, and about the one construction where the glue is safest:
    \problem wraps stem and workspace in ONE unbreakable minipage, so nothing
    there can fall at a page break in the first place. The author is told the
    space will vanish when it will not, and the offered remedy (star the glue)
    fixes a problem that was never present. 284 of the 600 recorded worksheets
    carry 1646 workspace \vspace* inside a \problem stem — every one of those
    sites is one character away from the wrong diagnosis.

    Only unstarred \vspace is considered at all: \vspace* survives a page
    break, so the space is never lost (though the templates' minipage form is
    still preferred, since it also keeps stem and workspace on the same page).
    """
    depth_at = minipage_depth_fn(tex)
    stems = problem_stem_spans(tex)
    faults, notes = [], []
    for m in re.finditer(r"\\vspace\{\s*(-?[\d.]+)\s*(cm|mm|in|pt|ex|em)\s*\}", tex):
        cm = to_cm(m.group(1), m.group(2))
        if cm < MIN_CM_PER_PROBLEM:
            continue
        line = tex.count("\n", 0, m.start()) + 1
        if any(a <= m.start() < b for a, b in stems):
            notes.append((line, round(cm, 2)))
        elif depth_at(m.start()) == 0:
            faults.append((line, round(cm, 2)))
    return faults, notes


# A blank plotting grid is WRITING SPACE, not a figure.
#
# The work-space floor counts glue only, so a problem whose room to work is an
# empty coordinate plane — "plot your counterexample here", "graph the line
# through these points" — measured 0cm and had to be given an artificial
# \problem[Ncm] that adds blank paper below a grid the student was always going
# to write on. has_valued_figure already draws exactly this distinction (an axis
# that draws nothing, or whose ticks are emptied, is not a figure to read), so
# the floor can use it rather than pretend the grid is not there.
#
# Deliberately narrow: an `axis` and nothing else. That is precisely where
# has_valued_figure already reasons about a blank grid ("an empty numbered grid
# is a place to write, like the \problem workspace above it"), so the floor and
# the figure rule agree about what an empty plane is.
#
# A bare tikzpicture `grid` path does NOT count, and the reason is a measured
# one: extending this to any \draw...grid exempted six recorded worksheets,
# among them an area model — a 4x3 rectangle the student COUNTS squares in and
# answers with "<", "=" or ">". That is a figure to read, and the problem needs
# writing room beside it exactly as the floor says. A pgfplots axis with
# nothing plotted in it has no such reading; it is blank paper with a scale.
PLOT_GRID = re.compile(r"\\begin\{axis\}")


def is_plotting_workspace(item):
    """A blank grid the student writes ON, rather than a figure they read."""
    return bool(PLOT_GRID.search(item)) and not has_valued_figure(item)


def main():
    argv = sys.argv[1:]
    scoped_sources = None
    if "--sources" in argv:
        i = argv.index("--sources")
        scoped_sources = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    figs_path = None
    if "--figs" in argv:
        i = argv.index("--figs")
        figs_path = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    if len(argv) != 1 or figs_path == "":
        print("Usage: check_layout.py <worksheet.tex> [--figs <figs.tex>]",
              file=sys.stderr)
        return 1
    path = argv[0]
    if scoped_sources is not None:
        from check_sources import validate
        try:
            validate(path, scoped_sources)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            print(f"Source review failed: {exc}", file=sys.stderr)
            return 1
    tex = open(path, encoding="utf-8").read()
    # Expand rendered \probfig{N} figures in place so both rules run on what
    # actually prints. Unresolved calls (stale figs, no --figs) stay in the
    # text — has_valued_figure counts them as valued, so the scope rule holds
    # either way.
    if figs_path:
        tex, _ = expand_probfigs(tex, probfig_bodies(open(figs_path, encoding="utf-8").read()))
    # blank comments AFTER expansion so rendered figure bodies are cleaned too
    tex = strip_comments(tex)
    layouts = re.findall(r"\\worksheetlayout\s*\{([^{}]*)\}", tex)
    if any(mode not in ("compact", "spacious") for mode in layouts):
        print("worksheetlayout must be compact or spacious", file=sys.stderr)
        return 1
    spacious = bool(layouts and layouts[-1] == "spacious")
    name = path.rsplit("/", 1)[-1]
    if re.match(r"^(ak|ss)_", name):
        print(f"check_layout: {name} is a key/guide, not written on — skipped")
        return 0

    faults = []
    print(f"Layout report: {path}")
    print("  mode: " + ("spacious (requested working room)" if spacious else "compact (no reserved working room)"))

    # Depth-aware: every enumerate at any depth is its own list, judged
    # against its own [itemsep=..] — a naive .*? regex ended the outer list at
    # the FIRST nested \end{enumerate}, so nested parts were counted as
    # top-level problems and every real item after them silently escaped both
    # rules (the false-PASS direction).
    lists = enumerate_lists(tex)
    for n, (opts, _env_span, item_spans, child_idxs) in enumerate(lists, 1):
        if not item_spans:
            continue
        # a nested part-list is checked as its own list (with its own opts),
        # so its items are blanked out of the parent item — otherwise a
        # part's figure would false-fail the parent's all-or-nothing rule
        child_item_spans = [sp for k in child_idxs for sp in lists[k][2]]
        its, had_nested = [], []
        for (s, e) in item_spans:
            inner = [(a, b) for a, b in child_item_spans if a >= s and b <= e]
            its.append(blank_spans(tex[s:e], inner, base=s))
            had_nested.append(bool(inner))
        valued = [i for i, it in enumerate(its, 1) if has_valued_figure(it)]
        bare = [i for i, it in enumerate(its, 1) if not has_own_figure(it)]

        # 1. figure scope — see problem_regions below for what this counts
        if valued and bare and scoped_sources is None:
            faults.append(
                f"list {n}: {len(valued)} of {len(its)} problems carry a figure with "
                f"values (items {valued}) while {len(bare)} carry no figure at all "
                f"(items {bare}). A student reading one of those will apply the "
                f"nearest figure to it. Give every problem in the list its own "
                f"figure, or move the shared labelling into a value-free reference "
                f"figure outside the list.")
        else:
            note = 'reviewed source binds figures to numbered problems' if scoped_sources is not None else scope_note(valued, its)
            print(f"  list {n}: figure scope ok ({note})")

        # 2. work space — items holding a nested part-list are skipped: their
        # workspace lives in the child's itemsep, which the child's own pass
        # enforces (mirrors problem_regions' had_list)
        thin = [(i, round(space_cm(opts, it), 2))
                for i, (it, nested) in enumerate(zip(its, had_nested), 1)
                if not nested and not is_plotting_workspace(it)
                and spacious and space_cm(opts, it) < MIN_CM_PER_PROBLEM]
        excessive = [(i, round(space_cm(opts, it), 2)) for i, it in enumerate(its, 1)
                     if not spacious and space_cm(opts, it) > 0.75]
        if excessive:
            faults.append(f"list {n}: compact mode has reserved working space {excessive}; remove it or declare \\worksheetlayout{{spacious}} for an explicit user request")
        if thin:
            worst = min(c for _, c in thin)
            faults.append(
                f"list {n}: {len(thin)} of {len(its)} problems have under "
                f"{MIN_CM_PER_PROBLEM}cm of work space (thinnest {worst}cm). "
                f"SKILL.md specifies ~5cm per problem, 8cm multi-step. Raise itemsep "
                f"or add \\vspace after each item.")
        else:
            print(f"  list {n}: {'requested work space' if spacious else 'compact spacing'} ok")

        # 4. answer location (\problem regions are exempt — see the docstring)
        noans = [i for i, it in enumerate(its, 1) if not ANSWER_RE.search(it)]
        if noans and spacious:
            faults.append(
                f"list {n}: items {noans} have no designated answer location. "
                f"End each item with \\ansline (right-aligned answer blank) or "
                f"an inline \\ansblank; mark \\noansline only where the worked "
                f"product IS the answer (sketch, proof, construction). A grader "
                f"should never hunt through scratch work for the final answer.")
        else:
            print(f"  list {n}: answer location ok "
                  f"(all {len(its)} items carry an answer-location macro)")

    # \problem-macro sheets: same two rules over the regions, treated as one
    # pseudo-list (a figure sits just as ambiguously between \problem blocks
    # as between \item entries)
    regions = problem_regions(tex)
    if regions:
        valued = [i for i, (_, r, _) in enumerate(regions, 1) if has_valued_figure(r)]
        # What creates the ambiguity is a problem with NO figure sitting beside
        # one whose figure carries data — that student has nothing of their own
        # to look at, so they look at the neighbour's. A problem holding its own
        # blank grid is not in that position: the picture inside its block is
        # visibly the one it means. Counting valued-vs-total instead of
        # valued-vs-figureless failed a sheet where all ten problems had a graph
        # and three of them were empty axes for the student to plot on — and the
        # only edit that would have satisfied it was deleting those three grids.
        bare = [i for i, (_, r, _) in enumerate(regions, 1) if not has_own_figure(r)]
        if valued and bare and scoped_sources is None:
            faults.append(
                f"problem blocks: {len(valued)} of {len(regions)} problems carry a "
                f"figure with values (problems {valued}) while {len(bare)} carry no "
                f"figure at all (problems {bare}). A student reading one of those "
                f"will apply the nearest figure to it. Give every problem its own "
                f"figure, or move shared labelling into a value-free reference "
                f"figure.")
        else:
            print(f"  problem blocks: figure scope ok "
                  f"({scope_note(valued, regions)})")

        # regions whose workspace lives in a nested list (multi-part template)
        # are governed by the enumerate pass above — skip the floor here
        thin = [(i, round(opt + space_cm("", r), 2))
                for i, (opt, r, had_list) in enumerate(regions, 1)
                if not had_list and not is_plotting_workspace(r)
                and spacious and opt + space_cm("", r) < MIN_CM_PER_PROBLEM]
        excessive = [(i, round(opt + space_cm("", r), 2)) for i, (opt, r, _) in enumerate(regions, 1)
                     if not spacious and (opt > 0 or space_cm("", r) > 0.75)]
        if excessive:
            faults.append(f"problem blocks: compact mode has reserved working space {excessive}; use \\problem{{...}} with no workspace, or declare \\worksheetlayout{{spacious}} for requested writing room")
        if thin:
            worst = min(c for _, c in thin)
            faults.append(
                f"problem blocks: {len(thin)} of {len(regions)} problems have under "
                f"{MIN_CM_PER_PROBLEM}cm of WRITING space (thinnest {worst}cm) — "
                f"a figure in the stem is not counted, however tall it is, "
                f"because a student cannot write on it (a BLANK plotting grid is "
                f"the exception: that is a place to write, and it counts). "
                f"SKILL.md specifies ~5cm per problem, 8cm multi-step. Pass the "
                f"workspace as the macro's optional argument — \\problem[5cm]{{...}} "
                f"— so it lives inside the problem's unbreakable minipage.")
        else:
            print(f"  problem blocks: {'requested work space' if spacious else 'compact spacing'} ok")

        # 5. oversized workspace — an unbreakable minipage taller than the page
        huge = [(i, round(opt + space_cm("", r), 2))
                for i, (opt, r, _) in enumerate(regions, 1)
                if opt + space_cm("", r) > MAX_CM_PER_PROBLEM]
        if huge:
            worst = max(c for _, c in huge)
            faults.append(
                f"problem blocks: {len(huge)} of {len(regions)} problems request more "
                f"than {MAX_CM_PER_PROBLEM}cm of work space (largest {worst}cm) "
                f"(problems {[i for i, _ in huge]}). \\problem keeps stem and workspace "
                f"in ONE unbreakable minipage, so a workspace taller than the ~24cm page "
                f"cannot break and prints past the bottom margin — the engine only warns "
                f"(Overfull \\vbox), so nothing else catches it. Split the problem into "
                f"parts, or move the extra room to a separate blank work page.")

    if not lists and not regions:
        print("\n  ⚠ PARSED ZERO PROBLEMS from this file.")
        print("    Nothing was checked, so this is NOT a pass. The worksheet")
        print("    must use \\problem{...}/\\problem[5cm]{...} or an")
        print("    enumerate/\\item list.")
        return 2

    # 3. page-break glue
    stranded, in_stem = stranded_workspace(tex)
    for line, cm in in_stem:
        # Inside a \problem stem the glue is already inside the macro's
        # unbreakable minipage, so it cannot be discarded at a break. Saying
        # otherwise sent authors to fix a fault that was not there.
        print(f"  ⚠ line {line}: workspace \\vspace{{{cm}cm}} sits inside a "
              f"\\problem stem, so it is already in the problem's unbreakable "
              f"minipage and will NOT be discarded at a page break. Prefer "
              f"\\problem[{cm}cm]{{...}} — the macro emits the answer line with "
              f"it — or star it (\\vspace*) if it must stay in the stem.")
    for line, cm in stranded:
        faults.append(
            f"line {line}: workspace \\vspace{{{cm}cm}} sits outside any minipage. "
            f"LaTeX discards \\vspace glue at a page or column break, so this space "
            f"vanishes exactly when its problem lands at a page bottom — the student "
            f"gets a stem with zero cm to work in. Put the workspace inside the "
            f"problem's unbreakable minipage (\\par\\vspace*{{{cm}cm}} before "
            f"\\end{{minipage}}, or \\problem[{cm}cm]{{...}} — see "
            f"references/latex-templates.md), or at minimum star it (\\vspace*).")

    if faults:
        print("\n❌ layout faults:")
        for f in faults:
            print(f"  • {f}")
        return 1
    print("\n✅ layout ok — figure scope and declared compact/spacious layout respected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
