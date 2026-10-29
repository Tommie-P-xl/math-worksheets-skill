# Maintainer tools

Run `python -m unittest discover -s tests -v` with Bash, SymPy 1.14.0,
pdflatex/Tectonic, XeLaTeX with ctex/Fandol fonts, and Poppler's pdftotext/pdftoppm available. Tests compile real PDFs, exercise
source/asset failures and build/run an extracted runtime-only ZIP.

Run `python tools/package_skill.py` to create a deterministic ZIP and SHA256 file
in `dist/`. The single top-level `math-worksheets/` directory is compatible with
CC Switch's recursive SKILL.md discovery. Packaging uses an explicit allowlist of runtime
files; README, tests, Git metadata and maintainer files do not enter the skill.

Run `python tools/build_browser_example.py` to rebuild the standalone bank-picker
demo from four synthetic questions in temporary storage. It never reads personal
data. Open the generated HTML, choose the geometry-calculation type, select Q1
and Q3, and capture the browser for the README screenshot. The Python bank tests
also generate HTML from an extracted ZIP; the existing three-OS CI matrix runs
those checks. `tools/check_browser_ui.cjs` verifies the generated demo offline in
Chromium, including both view modes, question and answer formulas/images, nested
subparts, zoom, selection and mobile layout. Runtime CI rebuilds the demo from
current source before running this check and installs Playwright in temporary
storage; it is not an end-user or ZIP dependency. For a
local run set `MWS_PLAYWRIGHT_MODULE` to an installed Playwright module directory
(optional `MWS_BROWSER_CHANNEL=chrome`) and run `node tools/check_browser_ui.cjs`.
An optional HTML path tests another snapshot. Set `MWS_SCREENSHOT_DIR` to capture
both README view images. Run `node tools/check_browser_exports.cjs` with the same
environment to verify all questions' Markdown code exports and exercise actual
PNG downloads, scoped print/PDF output and mobile PNG sizing offline. An optional
HTML path tests a personal snapshot without uploading it; `MWS_EXPORT_DIR` keeps
test artifacts outside the source tree for visual review. Otherwise temporary
export artifacts are removed after testing. Browser assets are pinned under
`templates/katex/` and `templates/html-to-image/`; keep the MIT
license and NOTICE when updating them, and update the runtime allowlist if its
file set changes. Browsing users never need npm or pip packages. The Q3 demo now
uses TikZ, so building its image requires TeX and pdftoppm; the generated demo HTML
already embeds the result for users without those tools.

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
