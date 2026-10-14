#!/usr/bin/env python3
"""
check_facet_coverage.py — cross-file facet gates: every facet the worksheet
tests must have a study-guide worked example, and a declared "subtitle" must
appear verbatim in the worksheet's title block.

Usage: check_facet_coverage.py <ws.tex> <verify_ws.json> [<verify_ss.json>]
       (omit the ss JSON under --worksheet-only builds)

WHY: the real failure this kills came in two halves. A worksheet subtitle
promised "angles of elevation and depression" while zero problems exercised
depression — the title was hand-written, uncoupled from any plan. And the
same sheet tested the Pythagorean theorem with no Pythagorean worked example
in the study guide, violating SKILL.md's "one section per distinct skill
tested" with no mechanical check. SKILL.md step 3 now directs the subtitle be
COMPOSED from the facet list in the verify JSON and copied into the tex; this
checker proves the copy happened (the tex cannot drift from the JSON) and
that the study guide teaches every facet the worksheet tests.

Reads JSON + tex text only — no LaTeX engine, CI-safe.

Exit 0: no facet plan (legacy sheets pass unchanged), or all gates green.
Exit 1: a worksheet facet lacks a tagged study-guide example, the ss JSON has
zero facet tags, or the subtitle is missing from the title block.
"""

import json
import re
import sys


def norm(s):
    """Whitespace-normalize so a line-wrapped tex subtitle still matches."""
    return " ".join(s.split())


def main():
    if len(sys.argv) not in (3, 4):
        print("Usage: check_facet_coverage.py <ws.tex> <verify_ws.json> "
              "[<verify_ss.json>]", file=sys.stderr)
        return 2
    tex_path, ws_path = sys.argv[1], sys.argv[2]
    ss_path = sys.argv[3] if len(sys.argv) == 4 else None
    ws = json.load(open(ws_path))
    if not ws.get("facets"):
        print("no facet plan — nothing to check")
        return 0
    errors = []
    ws_facets = {p.get("facet") for p in ws.get("problems", [])
                 if isinstance(p, dict) and p.get("facet")}

    if ss_path is not None:
        ss = json.load(open(ss_path))
        ss_facets = {p.get("facet") for p in ss.get("problems", [])
                     if isinstance(p, dict) and p.get("facet")}
        if not ss_facets:
            # Zero tags must never read as "nothing missing" — that silent
            # pass would gut the subset gate.
            errors.append(
                f"{ss_path} has zero \"facet\" tags but the worksheet "
                f"declares facets {sorted(ws_facets)} — tag each study-guide "
                "entry with the facet its worked example demonstrates")
        else:
            for f in sorted(ws_facets - ss_facets):
                errors.append(
                    f"worksheet tests {f!r} but the study guide has no "
                    f"worked example tagged {f!r} — add an examplebox + "
                    "verify_ss entry, or retag")
            if not (ws_facets - ss_facets):
                print(f"facet coverage: worksheet facets {sorted(ws_facets)} "
                      "all have study-guide examples")
    else:
        print("no study-guide JSON given (--worksheet-only) — "
              "subset gate skipped")

    subtitle = ws.get("subtitle")
    if subtitle:
        tex = open(tex_path).read()
        # The title block is everything before the first problem — searching
        # the whole file would let a subtitle buried in a stem count.
        m = re.search(r"\\problem\b|\\begin\{enumerate\}", tex)
        head = tex[:m.start()] if m else tex
        if norm(subtitle) in norm(head):
            print(f"subtitle bound: {subtitle!r} found in the title block")
        else:
            errors.append(
                f"subtitle {subtitle!r} (from {ws_path}) does not appear "
                f"verbatim in the title block of {tex_path} (searched before "
                "the first \\problem/enumerate) — copy the JSON subtitle "
                "into the worksheet title, or fix the JSON")

    for e in errors:
        print(f"❌ {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
