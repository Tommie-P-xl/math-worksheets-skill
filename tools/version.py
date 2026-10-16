"""Read the sole release version from SKILL.md; prepare derived release metadata."""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SEMVER = r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"


def get_version(root=ROOT):
    """Read metadata.version in YAML frontmatter without a runtime dependency."""
    content = (Path(root) / "SKILL.md").read_text(encoding="utf-8-sig")
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.S)
    if not frontmatter:
        raise ValueError("SKILL.md: missing YAML frontmatter")
    metadata = re.search(r"(?m)^metadata:\s*\n((?:[ \t]+[^\n]*\n?)*)", frontmatter[1])
    values = re.findall(r"(?m)^  version: ([^\s]+)\s*$", metadata[1] if metadata else "")
    if len(values) != 1 or not re.fullmatch(SEMVER, values[0]):
        raise ValueError("SKILL.md metadata.version must contain one major.minor.patch value")
    return values[0]


def release_notes(root=ROOT):
    """Only current release prose is published; historical entries stay in Git."""
    content = (Path(root) / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    if not content.startswith("# Current release\n"):
        raise ValueError("RELEASE_NOTES.md must begin with '# Current release'")
    current = re.split(r"(?m)^## v" + SEMVER + r"\s*$", content, maxsplit=1)[0]
    body = current.split("\n", 1)[1].strip()
    if not body:
        raise ValueError("Current release notes are empty")
    return f"# v{get_version(root)}\n\n{body}\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", action="store_true", help="print the derived v-prefixed tag")
    parser.add_argument("--check-tag", help="fail if this tag differs from the source version")
    parser.add_argument("--notes-out", type=Path, help="write current notes with a derived version heading")
    parser.add_argument("--github-output", type=Path, help="append version/tag outputs for GitHub Actions")
    args = parser.parse_args(argv)
    try:
        version = get_version()
        tag = "v" + version
        if args.check_tag is not None and args.check_tag != tag:
            raise ValueError(f"tag/version mismatch: got {args.check_tag!r}, expected {tag!r}")
        if args.notes_out:
            args.notes_out.write_text(release_notes(), encoding="utf-8")
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as output:
                output.write(f"version={version}\ntag={tag}\n")
        print(tag if args.tag else version)
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
