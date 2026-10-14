#!/usr/bin/env python3
"""
check_study_guide.py — enforce the worked-example STRUCTURE of a study guide:
every examplebox opens with an explicit choose-the-tool strategy step before
any computation, and (for machine-verified examples) prints a final answer.

Usage: python3 tests/check_study_guide.py <ss_*.tex> <verify_ss_*.json>

Why: the decision a student actually struggles with — WHY this ratio/method,
given what is known and wanted — is the move that transfers (worked-example
research: subgoal labeling), and a one-line answer chain never shows it. The
\\step macro in templates/worksheet-preamble.tex gives the slot; this checker
guarantees the slot exists and is prose-first.

Rules, per examplebox (tryitboxes are exempt — a try-it is stem + inverted
answer only; check_answer_key.py binds its value):
  a. >= 2 \\step{...} lines
  b. the FIRST \\step is strategy, not computation: no \\ans/\\boxed inside,
     and after stripping math segments it still contains >= 4 words of prose
  c. >= 1 \\ans{...} or \\boxed{...} in the box, unless every JSON entry
     bound to the box is type "manual" (sketch/graph examples)

HONEST LIMIT: this checker enforces that the strategy slot exists and is
prose-first; the QUALITY of the strategy sentence is carried by the spec text
(references/latex-templates.md) and the manual-review-aid pass — the same
division of labor as check_prose_consistency.

Exit 0 = every worked example has the shape. Exit 1 = a box is missing the
strategy step, opens with computation, or prints no final answer.
"""
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _tex_segments import box_spans, blank_comments  # noqa: E402

_MATH = re.compile(r"\$[^$]*\$|\\\([^)]*?\\\)|\\\[.*?\\\]", re.S)
_ANSWER = re.compile(r"\\(?:ans|boxed)\{")


def step_bodies(segment):
    """Contents of each \\step{...} in order, nesting-aware (same brace scan
    style as check_answer_key.boxed_answers — a step quoting \\frac{}{} must
    not truncate at the inner brace)."""
    out = []
    for m in re.finditer(r"\\step\{", segment):
        i, depth, buf = m.end(), 1, []
        while i < len(segment) and depth:
            c = segment[i]
            depth += (c == "{") - (c == "}")
            if depth:
                buf.append(c)
            i += 1
        out.append("".join(buf))
    return out


def prose_word_count(text):
    """Words of prose left after math segments and control sequences are
    stripped — the mechanical floor for 'strategy is written in words'."""
    text = _MATH.sub(" ", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    return len(re.findall(r"[A-Za-z]+", text))


def check_boxes(tex, by_id):
    """One error list entry per structural violation, teaching the fix.
    Box position k (1-based) binds to JSON id k — the same positional
    contract check_answer_key.py uses."""
    kinds = box_spans(tex)
    if kinds is None:
        return ["no examplebox found: study guides keep one worked example "
                "per examplebox environment (SKILL.md step 3) — \\problem/"
                "enumerate shapes cannot carry the \\step structure."]
    errs = []
    example_no = 0
    for pos, (a, b, kind) in enumerate(kinds, start=1):
        if kind != "examplebox":
            continue
        example_no += 1
        seg = tex[a:b]
        steps = step_bodies(seg)
        if len(steps) < 2:
            errs.append(
                f"worked example {example_no} has no strategy step — open "
                "with \\step{why this ratio/method applies: what you want, "
                "what you know} before computing (then the computation in "
                "\\step 2).")
            continue
        first = steps[0]
        if _ANSWER.search(first) or prose_word_count(first) < 4:
            errs.append(
                f"worked example {example_no}'s first step is computation, "
                "not strategy — say in words which tool you chose and why, "
                "then compute in step 2.")
        entries = by_id.get(pos, [])
        manual = bool(entries) and all(e.get("type") == "manual" for e in entries)
        if not manual and not _ANSWER.search(seg):
            errs.append(
                f"worked example {example_no} prints no final answer — end "
                "with \\ans{...} (or \\boxed{...}) so the binding gate can "
                "see it.")
    return errs


def main():
    if len(sys.argv) != 3:
        print("Usage: check_study_guide.py <ss_*.tex> <verify_ss_*.json>",
              file=sys.stderr)
        sys.exit(2)
    tex = blank_comments(open(sys.argv[1]).read())
    data = json.load(open(sys.argv[2]))
    by_id = {}
    for e in data.get("problems", []):
        if isinstance(e, dict) and isinstance(e.get("id"), int):
            by_id.setdefault(e["id"], []).append(e)

    print(f"Study-guide structure: {sys.argv[1]}")
    errs = check_boxes(tex, by_id)
    for e in errs:
        print(f"  ❌ {e}")
    if errs:
        print(f"\n❌ {len(errs)} structure failure(s) — every worked example "
              "opens with a one-sentence strategy step (see the ss template "
              "in references/latex-templates.md).")
        sys.exit(1)
    print("  ✅ every worked example opens with a strategy step and prints "
          "its answer")


if __name__ == "__main__":
    main()
