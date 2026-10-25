# Maintainer tools

Run `python -m unittest discover -s tests -v` with Bash, SymPy 1.14.0,
pdflatex/Tectonic, XeLaTeX with ctex/Fandol fonts, and pdftotext available. Tests compile real PDFs, exercise
source/asset failures and build/run an extracted runtime-only ZIP.

Run `python tools/package_skill.py` to create a deterministic ZIP and SHA256 file
in `dist/`. The single top-level `math-worksheets/` directory is compatible with
CC Switch's recursive SKILL.md discovery. Packaging uses an explicit allowlist of runtime
files; README, tests, Git metadata and maintainer files do not enter the skill.

For a release, edit only root `VERSION` for release identity. Do not repeat
skill release numbers in source filenames, documentation or package names.
`tools/version.py` reads that file for tag validation and Actions outputs;
release notes use an unnumbered heading. Dependency constraints and database
schema identifiers remain independent runtime compatibility data.

```bash
python tools/version.py
python tools/version.py --tag
python tools/package_skill.py
```

Commit the release changes, create the tag printed by `--tag` on that commit, then
push the commit and tag. The release workflow checks tag/version agreement,
validates runtime and package, and uploads the ZIP plus checksum. Manual dispatch
can publish an existing matching tag. It checks out that tag, not the dispatch
branch. Keep these maintenance instructions out of runtime SKILL.md.

Run `python tools/build_photo_example.py` to rebuild the real photograph example.
It performs independent symbolic geometry checks, regenerates reviewed LaTeX and
verification records, and runs the reproduction gate chain with XeLaTeX. Read the
example's transcription/review notes first. The original source image is preserved.
