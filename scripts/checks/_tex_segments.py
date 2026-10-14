#!/usr/bin/env python3
"""
_tex_segments.py — split a LaTeX document into per-problem segments.

Shared segmentation for the binding checkers (check_answer_key.py,
check_layout.py, and check_prose_consistency.py all parse through it). Why a
helper: the
shipped templates emit THREE document shapes, and a checker that parses only
one silently skips the others — the exact parser gap that let a fully swapped
enumerate-style answer key pass green (audit B1) after c2608b9 had fixed the
mirror-image gap in check_prose_consistency.py only.

Shapes, tried in order:

  1. \\problem{...} macros (answer-key template): a segment runs from each
     \\problem to the next, so the worked steps and \\boxed answers that
     FOLLOW the statement stay attached to their problem. Tolerates the
     optional-argument form \\problem[8cm]{...}.
  2. enumerate/\\item lists (worksheet template): DEPTH-AWARE — only \\item
     tokens belonging directly to an outermost enumerate start a segment.
     A naive regex split truncates at the first nested \\end{enumerate} and
     over-splits multi-part problems whose parts are their own nested list.
  3. examplebox/tryitbox environments (study-guide template): one worked
     example or try-it per box, in DOCUMENT ORDER (SKILL.md: entries are
     listed example, try-it, example, try-it — binding is positional), so
     ss_ documents bind per box exactly like answer keys bind per problem.

segment_spans(tex) -> list of (start, end) offsets into tex, or None when
none of the three shapes appears — callers decide how loudly to fail.

box_spans(tex) -> list of (start, end, kind) with kind "examplebox" or
"tryitbox", or None. Public for the sibling checkers (check_answer_key's
pairing/role rules, check_prose_consistency's study-guide path,
check_study_guide) — comments are blanked here so a commented-out box can
never create a phantom segment.
"""
import re

# \begin{enumerate} / \end{enumerate} never false-match the option text
# ([itemsep=4cm] carries no backslash) and \b keeps \itemsep from matching
# \item. itemize is tracked too: an \item of a bullet list nested inside a
# problem must not start a new problem segment.
_LIST_TOKEN = re.compile(
    r"\\begin\{(enumerate|itemize)\}|\\end\{(enumerate|itemize)\}|\\item\b")

_COMMENT = re.compile(r"(?<!\\)%[^\n]*")

# enumerate options must sit immediately after \begin{enumerate} — parity
# with the (\[[^\]]*\])? of the naive regex enumerate_lists replaces
_OPTS = re.compile(r"\[[^\]]*\]")


def blank_comments(tex):
    """Overwrite LaTeX comments with spaces, PRESERVING length and offsets.

    A commented-out \\item or a '% \\problem{...}' remark would otherwise
    start a phantom segment and shift every answer after it. Blanking (not
    deleting) keeps every span valid against the original text. \\% escapes
    are kept — they are printed percent signs, not comments.
    """
    return _COMMENT.sub(lambda m: " " * len(m.group(0)), tex)


def _problem_spans(tex):
    """One span per \\problem{...} use, running to the next \\problem or EOF.
    The regex skips the preamble definition (\\newcommand{\\problem}... has no
    '{' directly after the name) and accepts an optional [length] argument."""
    starts = [m.start() for m in re.finditer(r"\\problem(?:\[[^\]]*\])?\{", tex)]
    if not starts:
        return None
    return list(zip(starts, starts[1:] + [len(tex)]))


def _item_spans(tex):
    """One span per top-level \\item across every outermost enumerate.

    Walks list tokens with an environment stack instead of a regex over the
    whole environment: nested part-lists (multi-part template) and itemize
    bullets inside an item must extend the current segment, not split it."""
    spans, stack, item_start = [], [], None
    for m in _LIST_TOKEN.finditer(tex):
        opened, closed = m.group(1), m.group(2)
        if opened:
            stack.append(opened)
        elif closed:
            if stack == ["enumerate"] and item_start is not None:
                spans.append((item_start, m.start()))
                item_start = None
            if stack:
                stack.pop()
        else:  # \item
            if stack == ["enumerate"]:
                if item_start is not None:
                    spans.append((item_start, m.start()))
                item_start = m.start()
    return spans or None


def _box_spans(tex):
    """One (start, end, kind) per examplebox OR tryitbox body, in document
    position order — a single alternation regex so interleaved example/try-it
    pairs come out exactly as printed, matching the positional JSON contract."""
    spans = [(m.start(2), m.end(2), m.group(1)) for m in re.finditer(
        r"\\begin\{(examplebox|tryitbox)\}(.*?)\\end\{\1\}", tex, re.S)]
    return spans or None


def box_spans(tex):
    """Public box segmentation: (start, end, kind) triples or None.
    Blanks comments first (length-preserving, so spans stay valid against
    the caller's original text)."""
    return _box_spans(blank_comments(tex))


def enumerate_lists(tex):
    """Every enumerate environment at ANY depth, in document order.

    Returns [(opts, env_span, item_spans, child_idxs), ...]:
      opts       — the [..] immediately after \\begin{enumerate}, or ""
                   (parity with the naive regex this replaces)
      env_span   — (start of \\begin{enumerate}, end of \\end{enumerate})
      item_spans — (start-of-\\item, start of next sibling \\item or own \\end)
      child_idxs — indices (into the returned list) of enumerate lists nested
                   directly inside this one; an itemize in between does not
                   break the link, so a part-list's items can always be
                   blanked out of the enclosing enumerate item.

    Why per-list at any depth rather than outermost-only: check_layout must
    validate a nested part-list against its OWN [itemsep=..] options — that
    is how the multi-part template's workspace floor is enforced — while the
    parent pass blanks the child's items so a part's figure or spacing is
    never mis-attributed to the parent item. itemize frames are tracked but
    never emitted and never split items (parity with _item_spans). Comments
    are blanked internally — length-preserving, so every returned span is
    valid against the caller's text.
    """
    tex = blank_comments(tex)
    lists = []   # appended at close time (children first), sorted below
    # frame: [env, opts, begin_start, item_spans, open_item_start, child_idxs]
    frames = []
    for m in _LIST_TOKEN.finditer(tex):
        opened, closed = m.group(1), m.group(2)
        if opened:
            o = _OPTS.match(tex, m.end())
            frames.append([opened, o.group(0) if o else "", m.start(), [], None, []])
        elif closed:
            if not frames:
                continue
            env, opts, begin, item_spans, item_start, kids = frames.pop()
            if env == "enumerate":
                if item_start is not None:
                    item_spans.append((item_start, m.start()))
                idx = len(lists)
                lists.append((opts, (begin, m.end()), item_spans, kids))
                for f in reversed(frames):
                    if f[0] == "enumerate":
                        f[5].append(idx)
                        break
        else:  # \item
            if frames and frames[-1][0] == "enumerate":
                f = frames[-1]
                if f[4] is not None:
                    f[3].append((f[4], m.start()))
                f[4] = m.start()
    # the stack walk closes children before parents; reports must count lists
    # in the order a reader sees them, or the shipped "list 2:" faults would
    # renumber — sort by \begin offset and remap the child links to match
    order = sorted(range(len(lists)), key=lambda i: lists[i][1][0])
    remap = {old: new for new, old in enumerate(order)}
    return [(lists[i][0], lists[i][1], lists[i][2],
             sorted(remap[k] for k in lists[i][3])) for i in order]


def segment_spans(tex):
    """Per-problem (start, end) spans, or None if no known shape parses."""
    tex = blank_comments(tex)
    boxes = _box_spans(tex)
    return (_problem_spans(tex) or _item_spans(tex)
            or ([(a, b) for a, b, _ in boxes] if boxes else None))
