"""Read release identity exclusively from VERSION and prepare publishing metadata."""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SEMVER = r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"


def get_version(root=ROOT):
    """Accept one major.minor.patch line in the root VERSION file."""
    value = (Path(root) / "VERSION").read_text(encoding="utf-8-sig").strip()
    if not re.fullmatch(SEMVER, value):
        raise ValueError("VERSION must contain one major.minor.patch value")
    return value


def release_notes(root=ROOT):
    """Publish unnumbered notes; release tags carry derived identity in GitHub."""
    content = (Path(root) / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    if not content.startswith("# Current release\n"):
        raise ValueError("RELEASE_NOTES.md must begin with '# Current release'")
    body = content.split("\n", 1)[1].strip()
    if not body:
        raise ValueError("Current release notes are empty")
    return f"# Current release\n\n{body}\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", action="store_true", help="print the derived v-prefixed tag")
    parser.add_argument("--check-tag", help="fail if this tag differs from the source version")
    parser.add_argument("--notes-out", type=Path, help="write the current unnumbered release notes")
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
