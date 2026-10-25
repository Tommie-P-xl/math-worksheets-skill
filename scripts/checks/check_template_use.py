#!/usr/bin/env python3
r"""
check_template_use.py — enforce SKILL.md's "\input the shipped template,
never retype it" mechanically.

Usage: python3 tests/check_template_use.py <doc.tex>
                [--template <worksheet-preamble.tex>]

The shipped shell carries \fittedtitle overflow protection, the
workspace-in-minipage \problem semantics, and the exact environment names the
downstream binding gates expect. A hand-rolled preamble drifts in precisely
the places CI (which has no LaTeX engine) cannot see: box styling, headers,
title fitting, workspace glue. Nothing enforced the rule until this gate —
one real session hand-rolled all three document shells and every other gate
stayed green.

Three rules, all on comment-blanked text:

  A. \input{worksheet-preamble} must appear before \begin{document}.
  B. Every \input target must be a shipped template (worksheet-preamble,
     figure-macros) or a rendered figs_/meta_/qa_ file: a local preamble file
     is exactly where hand-rolled redefinitions hide from a doc-only scan.
  C. No definition (\newcommand/\renewcommand/\providecommand/\def,
     \newenvironment/\renewenvironment/\newmdenv/\renewmdenv, \definecolor)
     of an identifier the template ships. The protected set is PARSED from
     templates/worksheet-preamble.tex at run time, never hardcoded — a
     hardcoded list drifts the day the template gains a macro.

Exit 0 pass, 1 fail, 2 usage / missing file.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _tex_segments import blank_comments  # noqa: E402

# \input targets that never count as hand-rolling: the two shipped templates
# and the figs files scripts/render_figures.py emits
WHITELIST = ("worksheet-preamble", "figure-macros")

DEF_CMD = re.compile(r"\\(?:newcommand|renewcommand|providecommand)\s*\*?\s*"
                     r"\{?\s*\\([a-zA-Z]+)\}?")
DEF_TEX = re.compile(r"\\def\s*\\([a-zA-Z]+)")
DEF_ENV = re.compile(r"\\(?:newenvironment|renewenvironment)\s*\*?\s*"
                     r"\{([a-zA-Z]+)\}")
DEF_MDENV = re.compile(r"\\(?:newmdenv|renewmdenv)\s*(?:\[[^\]]*\])?\s*"
                       r"\{([a-zA-Z]+)\}")
DEF_COLOR = re.compile(r"\\definecolor\s*\{([a-zA-Z]+)\}")


def protected_identifiers(template_tex):
    """{name -> kind} for everything the shipped preamble defines.

    Derived, never hardcoded: command names from \\newcommand{\\X}, environment
    names from \\newmdenv[..]{X}, color names from \\definecolor{X}. Only
    top-level \\newcommand forms are scanned — \\renewcommand inside a macro
    body (e.g. \\headrulewidth) is LaTeX plumbing, not a shipped identifier.
    """
    tpl = blank_comments(template_tex)
    names = {}
    for m in re.finditer(r"\\newcommand\s*\{\s*\\([a-zA-Z]+)\s*\}", tpl):
        names[m.group(1)] = "command"
    for m in DEF_MDENV.finditer(tpl):
        names[m.group(1)] = "environment"
    for m in DEF_COLOR.finditer(tpl):
        names[m.group(1)] = "color"
    return names


def check(doc_tex, template_tex, template_path):
    """Return a list of fault strings (empty = pass)."""
    doc = blank_comments(doc_tex)
    protected = protected_identifiers(template_tex)
    faults = []

    # A. the template must be \input BEFORE \begin{document} (preamble-only
    # macros defined mid-document would not compile anyway)
    begin_doc = doc.find(r"\begin{document}")
    preamble = doc[:begin_doc] if begin_doc != -1 else doc
    if not re.search(r"\\input\{worksheet-preamble(?:\.tex)?\}", preamble):
        faults.append(
            "missing \\input{worksheet-preamble} before \\begin{document}")

    # B. foreign \input files: a local preamble is where hand-rolled
    # redefinitions live, invisible to the rule-C scan of this file alone.
    # figs_/meta_/qa_ files are CONSTRUCTED by the shipped renderers from the
    # verify JSON (render_figures/render_meta/render_quick_answers), so they
    # are the opposite of hand-rolled — the whole point of the construction
    # pipeline is that these inputs are allowed while everything else is not.
    _RENDERED = ("figs_", "meta_", "qa_")
    for m in re.finditer(r"\\input\{([^}]*)\}", doc):
        target = m.group(1).strip()
        base = target[:-4] if target.endswith(".tex") else target
        if base in WHITELIST or os.path.basename(base).startswith(_RENDERED):
            continue
        faults.append(
            f"\\input{{{target}}} is not a shipped template — only "
            f"\\input{{worksheet-preamble}}, \\input{{figure-macros}} and "
            f"rendered figs_*/meta_*/qa_* files are allowed")

    # C. shadowed identifiers: every *definition* verb LaTeX offers, because a
    # post-template override must use \renew* to compile and a pre-template
    # stub can use any of them
    for regex in (DEF_CMD, DEF_TEX):
        for m in regex.finditer(doc):
            if m.group(1) in protected and m.group(1) not in {"schoolname", "mwsnamelabel", "mwsdatelabel", "mwsstemlabel", "mwsleaflabel"}:
                faults.append(
                    f"\\{m.group(1)} is redefined here but shipped by the "
                    f"template ({template_path} defines this "
                    f"{protected[m.group(1)]})")
    for regex in (DEF_ENV, DEF_MDENV):
        for m in regex.finditer(doc):
            if m.group(1) in protected:
                faults.append(
                    f"environment '{m.group(1)}' is redefined here but "
                    f"shipped by the template ({template_path})")
    for m in DEF_COLOR.finditer(doc):
        if m.group(1) in protected:
            faults.append(
                f"color '{m.group(1)}' is redefined here but shipped by the "
                f"template ({template_path})")
    faults.extend(header_title_faults(doc))
    return faults


# D. HEADER TITLE LENGTH. The running head is a fixed-width box; a title too
# long for it is shrunk to fit (\mws@fitl). Shrinking prevents the collision
# that used to overprint the Name/Date blanks, but a shrunk title is degraded
# output, and nothing on the page says so — the document just quietly gets
# harder to read, on every page, because a running head repeats. Caught here
# instead, statically, before the compile.
#
# Budgets are measured, not guessed: \small\bfseries averages 5.48pt/char and
# \headwidth is 469.8pt, so the worksheet's page-1 head (which reserves 8.4cm
# for the Name/Date blanks plus a 0.5cm gutter) fits ~39 characters. The
# answer key and study guide reserve nothing on the right, so they fit ~68.
# A 10% buffer covers titles of unusually wide characters.
HEADER_BUDGET = {
    "wsheader": 60,   # no reserved name/date slot
    "akheader": 60,   # measured 68 (" --- Answer Key" already subtracted)
    "ssheader": 60,   # measured 67 ("Skills Summary: " already subtracted)
    # \skillheading had a budget in fact but not in this table, so it was the
    # one head with no pre-compile check: three separate eval-run agents
    # overflowed it and only found out at compile-ss, with an overfull hbox and
    # no hint of the cause. It sits in the study-guide body at margin=0.85in and
    # SKILL.md encourages appending the skill slug to it, which is exactly what
    # pushes it over. Measured: overflow begins just past 57 characters.
    "skillheading": 57,
}
# The study guide runs at a wider text block than the running head, so it does
# not take the A4 running-head penalty.
BODY_HEADS = {"skillheading"}
# A4 is 6mm narrower than Letter, so every head slot loses about 4 characters.
# Scaling the budget by the width ratio keeps one rule honest on both papers
# instead of quietly passing on Letter and overflowing on A4.
A4_WIDTH_RATIO = 21.0 / 21.59
# Accessibility modes set a larger base type size, and the running head scales
# with it, so the same title that fits at 12pt is shrunk at 17pt. Measured
# average character widths at \small\bfseries: 5.48pt at 12pt, 5.87pt at 14pt,
# 7.04pt at 17pt. A large-print sheet is exactly the one that must not have a
# shrunken header, so the budget scales rather than being waived.
SIZE_RATIO = {10: 1.15, 11: 1.07, 12: 1.00, 14: 0.93, 17: 0.78, 20: 0.66}
HEADER_RE = re.compile(r"\\(wsheader|akheader|ssheader|skillheading)\{([^{}]*)\}")


def visible_len(title):
    """Characters a reader sees: strip TeX markup and math delimiters, and
    count an escaped symbol as the one glyph it prints."""
    t = re.sub(r"\\[a-zA-Z]+\s*", "x", title)   # \alpha -> one glyph
    t = t.replace("$", "").replace("{", "").replace("}", "")
    return len(t.strip())


def header_title_faults(doc):
    out = []
    a4 = bool(re.search(r"\\documentclass\[[^\]]*a4paper", doc))
    m = re.search(r"\\documentclass\[[^\]]*?(\d+)pt", doc)
    size = int(m.group(1)) if m else 12
    for m in HEADER_RE.finditer(doc):
        macro, title = m.group(1), m.group(2)
        n = visible_len(title)
        cap = HEADER_BUDGET[macro]
        if a4 and macro not in BODY_HEADS:
            cap = int(cap * A4_WIDTH_RATIO)
        cap = int(cap * SIZE_RATIO.get(size, 1.0))
        if n > cap:
            out.append(
                f"\\{macro} title is {n} characters; "
                + ("the study-guide text block fits "
                   if macro in BODY_HEADS else "the running-head slot fits ")
                + f"about {cap}"
                f"{' on A4' if a4 else ''}{f' at {size}pt' if size != 12 else ''}"
                + (". It will overflow the text block and fail compile-ss. "
                   "Name the skill in plain words and leave the slug to the "
                   "JSON — the coverage gate reads the tag, not the heading."
                   if macro in BODY_HEADS else
                   ". It will be shrunk to fit on EVERY page, which is "
                   "legible but visibly degraded. Use a short running title "
                   "(\"Triangle Trig Practice\", not the full course name) — the "
                   "full topic still gets its full size in the title block."))
    return out


def main():
    argv = sys.argv[1:]
    template_arg = None
    if "--template" in argv:
        i = argv.index("--template")
        template_arg = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    if len(argv) != 1 or template_arg == "":
        print("Usage: check_template_use.py <doc.tex> "
              "[--template <worksheet-preamble.tex>]", file=sys.stderr)
        return 2
    doc_path = argv[0]
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = template_arg or os.path.join(
        repo, "templates", "worksheet-preamble.tex")

    if not os.path.isfile(doc_path):
        print(f"Error: document not found: {doc_path}", file=sys.stderr)
        return 2
    if not os.path.isfile(template_path):
        # mirror compile.sh's partial-checkout error: the template IS the
        # contract, so a missing template means nothing can be checked
        print(f"Error: shipped template not found at {template_path} "
              f"(partial checkout?). Restore the skill's templates/ "
              f"directory.", file=sys.stderr)
        return 2

    doc = open(doc_path, encoding="utf-8").read()
    faults = check(doc, open(template_path, encoding="utf-8").read(), template_path)
    name = os.path.basename(doc_path)
    print(f"Template-use report: {doc_path}")
    if not faults:
        print("✅ template shell ok — shipped preamble \\input, nothing shadowed.")
        return 0

    # A title that is too long and a hand-rolled preamble are different faults
    # with different fixes, and they were printed under one verdict. An author
    # whose only problem was a 60-character \skillheading got the headline
    # "hand-rolled shell" and twelve lines telling them to start the document
    # with the shipped shell — which it already did. Two authors in one run
    # rebuilt against that misdirection. The rule was right; the verdict it was
    # filed under was not.
    title_faults = header_title_faults(doc)
    shell_faults = [f for f in faults if f not in title_faults]

    if title_faults:
        print("\n❌ heading too long for its slot:")
        for f in title_faults:
            print(f"  • {f}")
        if not shell_faults:
            print("\n  The document shell itself is fine — this is only about "
                  "the heading text.")
    if not shell_faults:
        return 1

    print("\n❌ hand-rolled shell:")
    for f in shell_faults:
        print(f"  • {f}")
    print(f"""
  Start {name} with the shipped shell (SKILL.md step 3):

    \\documentclass[12pt]{{article}}
    \\input{{worksheet-preamble}}
    \\input{{figure-macros}}    % when using the shipped figure macros

  compile.sh stages worksheet-preamble.tex and figure-macros.tex beside your
  .tex automatically. Margins come from the global config.json.
  The shipped shell carries \\fittedtitle overflow protection, the
  workspace-in-minipage \\problem semantics, and the exact environment names
  the downstream gates bind to — a hand-rolled preamble drifts where CI
  (no LaTeX engine) cannot see.""")
    return 1


if __name__ == "__main__":
    sys.exit(main())
