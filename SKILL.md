---
name: math-worksheets
description: Create printable math worksheet PDFs, concise verified answer keys, and optional study guides. Use for new practice problems or faithful reproduction of existing questions from text, screenshots, or photos, including mathematical diagrams and handwritten interference.
metadata:
  version: 3.7.2
  author: trond.ai; fork maintained by Tommie-P-xl
---

# Math worksheets

Resolve `SKILL_DIR` to this file's directory. Use the agent's existing model,
file access, vision capabilities and shell; no agent-specific runtime is required.

## Choose the workflow

- **New practice:** infer or gather topic, level, quantity (default 10), paper size,
  language and difficulty. Read [authoring.md](references/authoring.md) for the
  detailed authoring rules. Default outputs: worksheet, concise worked answer key,
  and study guide. Honor explicit requests for fewer documents.
- **Existing questions:** when given question text, screenshots or photos to turn
  into a worksheet, read [reproduction.md](references/reproduction.md). Preserve
  supplied questions and order; do not invent replacement questions or change
  numbers to make verification easier. Default outputs: worksheet and independently
  checked concise answer key; a study guide is optional. If only a worksheet was
  requested, verify solutions internally without delivering an answer key.
- **Guide only:** create `ss_STEM.tex` and `verify_ss_STEM.json`, then build with
  `--study-guide-only`. See [authoring.md](references/authoring.md).

## Mathematical and visual accuracy

Use [problem-library.md](references/problem-library.md) for verification recipes
and [standards-map.md](references/standards-map.md) when curriculum alignment is
requested or useful. In reproduction mode, preserve source order rather than
imposing a difficulty ramp or adding curriculum tags absent from the source.

Solve every response independently, including questions with no answer supplied.
Handwritten working or an existing answer is a hypothesis, never ground truth.
Use the fixed `scripts/verify.py` with one JSON entry per response (several entries
may share a problem id). Declare `problem_count` and cover ids `1..N`.
Run `python scripts/verify.py --schema` for the current schema.
Proofs, constructions, sketches and explanations are `manual`; numeric/symbolic
parts of those same questions still receive machine checks.

Draw functions and geometry using TikZ/pgfplots and the shipped macros where
practical. Data, labels and computed answers must agree. A source illustration
that cannot be redrawn faithfully follows the choices in reproduction.md;
do not silently substitute an AI image for mathematical evidence.

Keep answer prose compact: the essential setup, decisive steps and final answer
with units/domain restrictions. Read [solutions.md](references/solutions.md) when
graphs or abstract reasoning need explanatory diagrams. Add a diagram when it
clarifies the reasoning; distinguish answer-only information from question givens.

## Build and deliver

Default to compact question layout: no reserved working area between stems.
Keep original inline fill-in blanks and figures, but do not add trailing answer
lines or blank plotting/work areas unless requested. Use `\problem{...}` without
a positive workspace argument and compact enumerate spacing. Only when the user
explicitly requests working space, declare `\worksheetlayout{spacious}` and add
the requested space inside each problem block. Keep figure size readable in either
mode; compact layout does not mean shrinking diagrams.

Geometry point/side labels must have transparent backgrounds and sit clear of
all nearby segments, arcs and other labels. Move the anchor/position or add a
small offset into a free sector; never hide a collision with white fill. Inspect
the actual rendered diagram at its final print size, including internal points
and multi-line intersections. See [solutions.md](references/solutions.md).

Read [latex-templates.md](references/latex-templates.md) for document shells and
figure styles. Each document must `\input{worksheet-preamble}`; do not retype or
override shipped macros. Keep files and assets in the chosen work directory:

- `ws_STEM.tex`, `ak_STEM.tex`, optional `ss_STEM.tex`
- `verify_STEM.json`, and `verify_ss_STEM.json` when a guide exists
- `sources_STEM.json` in reproduction mode; see reproduction.md for its schema

Use `bash "$SKILL_DIR/scripts/build.sh" WORK/verify_STEM.json --outdir OUTPUT`.
Use `--no-study-guide` for worksheet + key, `--worksheet-only` for worksheet alone,
and `--reproduce --sources WORK/sources_STEM.json` for source reproduction
(implies no study guide). Generate a requested guide in a separate guide-only build.

Required tools: Bash, Python with SymPy >=1.12 (measured upstream baseline 1.14.0),
Tectonic or pdflatex with pgfplots >=1.18, and Poppler's `pdftotext`.
The scripts prefer a Python that can import SymPy. Set `MWS_PYTHON` to one
interpreter path when necessary, especially on Windows with multiple Pythons.
Use Bash paths in shell commands and UTF-8 for generated text.
For non-Latin content, choose and test a compatible font/LaTeX setup before the
full build; do not silently translate the user's original question to English.
Chinese documents can use `ctexart` with `fontset=fandol`; install XeLaTeX and
the Chinese language/font packages. `compile.sh` auto-selects XeLaTeX for
ctex/xeCJK/fontspec sources when available. Set `MWS_LATEX_ENGINE=xelatex` to
select it explicitly; `auto`, `tectonic` and `pdflatex` are also supported.

Exit 0: gates passed. Exit 1: fix the named failure and rebuild. Exit 2: no
automated failure, but manual answers or externally reviewed image content remain.
Never describe those items as machine-verified. Gates check math data, source
consistency, workspace, units, log faults and PDF text collisions; they do not
prove OCR fidelity, pedagogical quality, every solution step or all diagram geometry.
Inspect rendered PDFs, especially reproduced and explanatory figures. Deliver
only the requested documents and their paths/attachments, with a short note on
unresolved manual-review limits. Do not deliver a question with unresolved givens.
