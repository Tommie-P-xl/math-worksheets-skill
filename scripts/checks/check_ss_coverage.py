#!/usr/bin/env python3
"""
check_ss_coverage.py — every skill the worksheet tests must have a tagged
study-guide entry: the guide COVERS the worksheet, mechanically.

Usage: python3 tests/check_ss_coverage.py <verify_ws.json> <verify_ss.json>

Why: standards tags cannot distinguish skills (a 20-problem sheet can carry
one standard across five distinct Parts), so SKILL.md's "one section per
distinct skill tested" was prose-only — a study guide with ONE worked example
would pass every gate green. This gate reads the "skill" tags on both JSONs
and requires each distinct worksheet skill to appear on at least one
study-guide entry.

Tagging is ALL-OR-NOTHING by the audit-3b principle (an optional gate is a
vacuous gate): zero or partial worksheet tagging is a failure here, never a
silent pass. Guide-only skills (extra material) are legal — the requirement
is one-directional, worksheet → study guide.

A phantom ss JSON entry added just to satisfy this gate cannot survive the
chain: the downstream answer-key-ss gate anchors every entry to a real
examplebox/tryitbox (segment count == problem_count, positional binding), so
the entry must correspond to a printed, verified worked example.

Like all label matching (cf. "standard"), a dishonest mislabel passes; the
realistic failure mode — honestly omitting a skill from the guide — is caught.

Exit 0 = all worksheet skills covered. Exit 1 = untagged/invalid tags or an
uncovered skill.

stdlib-only (like check_answer_key.py): runs anywhere python3 runs.
"""
import json
import re
import sys


def norm(s):
    return s.strip().casefold()


def loose(s):
    """Near-miss key: case/whitespace/hyphen-vs-underscore collapsed, so a
    'Right Triangle' vs 'right_triangle' mismatch is self-diagnosing."""
    return re.sub(r"[\s_\-]+", "", norm(s))


def load_problems(path):
    with open(path) as f:
        data = json.load(f)
    return [p for p in data.get("problems", []) if isinstance(p, dict)]


def validate_tags(problems, path):
    errs = []
    for p in problems:
        if "skill" not in p:
            continue
        s = p["skill"]
        if not isinstance(s, str) or not s.strip() or len(s) > 40:
            errs.append(
                f"  ❌ {path}: problem {p.get('id')}: \"skill\" must be a "
                f"non-empty string of at most 40 chars, got {s!r} — use a "
                "short stable name like \"right-triangle-trig\".")
    return errs


def main():
    if len(sys.argv) != 3:
        print("Usage: check_ss_coverage.py <verify_ws.json> <verify_ss.json>",
              file=sys.stderr)
        sys.exit(2)
    ws_path, ss_path = sys.argv[1], sys.argv[2]
    ws = load_problems(ws_path)
    ss = load_problems(ss_path)

    print(f"Skill coverage: {ws_path} → {ss_path}")
    errs = validate_tags(ws, ws_path) + validate_tags(ss, ss_path)
    if errs:
        for e in errs:
            print(e)
        sys.exit(1)

    tagged = [p for p in ws if "skill" in p]
    if not tagged:
        print("  ❌ NO worksheet problem carries a \"skill\" tag — skills "
              "coverage cannot be checked, and an unchecked gate is a vacuous "
              "gate. Tag every ws problem with \"skill\": \"<short-name>\" "
              "(names should mirror the worksheet's Parts) and tag each ss "
              "worked example with the skill it demonstrates.")
        sys.exit(1)
    untagged = [p.get("id") for p in ws if "skill" not in p]
    if untagged:
        print(f"  ❌ worksheet tagging is PARTIAL — problem id(s) {untagged} "
              "have no \"skill\" tag. Tag every problem (repeat the tag "
              "across problems of the same Part) so coverage checks the "
              "whole sheet.")
        sys.exit(1)

    ws_skills = {norm(p["skill"]) for p in tagged}
    ss_skills = {norm(p["skill"]) for p in ss if "skill" in p}
    uncovered = sorted(ws_skills - ss_skills)
    if uncovered:
        for sk in uncovered:
            near = [t for t in sorted(ss_skills) if loose(t) == loose(sk)]
            hint = (f" (near-miss in the guide: {near[0]!r} — unify the "
                    "spelling)" if near else "")
            print(f"  ❌ worksheet skill {sk!r} has no study-guide entry"
                  f"{hint} — add a formulabox+examplebox section for it to "
                  "the study guide, with one JSON entry tagged "
                  f"\"skill\": \"{sk}\".")
        print(f"     ws skills: {sorted(ws_skills)}")
        print(f"     ss skills: {sorted(ss_skills)}")
        sys.exit(1)

    extra = sorted(ss_skills - ws_skills)
    note = f" (guide-only extras: {extra})" if extra else ""
    print(f"  ✅ {len(ws_skills)} worksheet skill(s), all covered by the "
          f"study guide{note}")


if __name__ == "__main__":
    main()
