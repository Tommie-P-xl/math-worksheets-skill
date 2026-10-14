# Math Worksheets Skill

English | [简体中文](README.zh-CN.md)

Create printable math worksheets from a topic request, or reproduce existing
questions from text, screenshots and photos. The agent solves each response
independently; SymPy checks supported answers before PDF delivery.

## Install

Download `math-worksheets-v*.zip` from
[Releases](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest),
then use **CC Switch → Skills → Install from ZIP** and enable it for your agent.
The archive contains one `math-worksheets/` folder with runtime files only.

Requires Bash, Python with `sympy>=1.12` (recommended `1.14.0`), Tectonic or
pdflatex with pgfplots >=1.18, and Poppler's `pdftotext`. On Windows, use
Git Bash/MSYS2 with these tools on its PATH. Set `MWS_PYTHON` to a specific
SymPy-capable interpreter if needed.

Alternatively, clone this repository and ask your agent to follow `SKILL.md`.

## Use

> Use math-worksheets to make 10 quadratic-equation questions on A4, with a concise worked answer key and a study guide.

> Turn these screenshots into a PDF worksheet in their original order. Exclude handwritten working, ask about obscured givens, redraw mathematical figures programmatically, and independently verify the concise answers.

> Typeset these supplied questions; deliver only the student PDF and verify solutions internally.

New practice defaults to worksheet + key + guide. Reproduction defaults to
worksheet + key, with the guide optional. For complex photos/illustrations,
the agent asks you to choose a clean crop, supported image generation, or a
mathematically faithful programmatic schematic. Difficult solutions may include
a small explanatory diagram while keeping prose concise.

## Accuracy and attribution

The build checks answer data, document consistency, units, work space, LaTeX logs
and PDF text collisions. Reproduction also binds reviewed source records and
external image files. Proofs, explanations, OCR fidelity and image content remain
review-dependent; a review record is not a CAS proof.

Fork of [stellawuellner/math-worksheets-skill](https://github.com/stellawuellner/math-worksheets-skill).
Retains its verifier, templates and mathematical references. [MIT license](LICENSE).
