# Math Worksheets Skill

English | [简体中文](README.zh-CN.md)

[![checks](https://github.com/Tommie-P-xl/math-worksheets-skill/actions/workflows/tests.yml/badge.svg)](https://github.com/Tommie-P-xl/math-worksheets-skill/actions/workflows/tests.yml)
[![release](https://img.shields.io/github/v/release/Tommie-P-xl/math-worksheets-skill)](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Ask your AI agent for math practice, or give it existing questions as text,
screenshots or photos. Get printable PDFs, independently checked answers and
mathematical diagrams drawn with code. Supports elementary math through AP
Calculus BC, using the model and tools your agent already has.

[Output previews](#output-previews) · [Install](#install) · [Prompt templates](#prompt-templates) · [How it works](#how-it-works)

## Output previews

### Function 1: generate practice questions

| Worksheet | Answer key | Study guide |
|:---:|:---:|:---:|
| [<img src="docs/samples/upstream/worksheet_geometry-1.png" width="250" alt="Geometry worksheet">](docs/samples/upstream/worksheet_geometry-1.png) | [<img src="docs/samples/upstream/answerkey_geometry-1.png" width="250" alt="Worked answer key">](docs/samples/upstream/answerkey_geometry-1.png) | [<img src="docs/samples/upstream/skills_summary-1.png" width="250" alt="Study guide">](docs/samples/upstream/skills_summary-1.png) |
| Mathematical figures and printable questions | Quick answers and worked solutions | Rules, examples and try-it problems |

These previews illustrate the worksheet, answer key and study-guide formats.
Their attribution is recorded below. Also see a [data-handling worksheet](docs/samples/upstream/worksheet_data-1.png)
and [answer-key summary page](docs/samples/upstream/answerkey_summary_page.png).
The preview set illustrates a layout with writing room; the current default is
compact, as demonstrated in Function 2. Request writing space explicitly when needed.

### Function 2: reproduce supplied questions

| Uploaded source | Clean student worksheet | Answer key with explanation diagram |
|:---:|:---:|:---:|
| [<img src="docs/examples/photo-folding/source.png" width="250" alt="Original photo with handwriting">](docs/examples/photo-folding/source.png) | [<img src="docs/examples/photo-folding/worksheet.png" width="250" alt="Reproduced Chinese worksheet">](docs/examples/photo-folding/ws_photo_folding.pdf) | [<img src="docs/examples/photo-folding/answer-key.png" width="250" alt="Concise folding solution and diagram">](docs/examples/photo-folding/ak_photo_folding.pdf) |
| Preserve the photo as evidence | Exclude handwritten working; redraw both figures | Independent calculation; add answer-only explanations |

This fork's actual test preserves the three original geometry parts and rebuilds
the diagrams with TikZ. It produces a one-page worksheet and a two-page key;
the key preview shows the solution page, with the verification summary on page two. The application answer
is `CP = 9√5/5`. Ten CAS checks pass; two geometric reasoning entries remain
explicitly marked for manual review. See the
[transcription, prompt and reproducible checks](docs/examples/photo-folding/README.md),
[worksheet PDF](docs/examples/photo-folding/ws_photo_folding.pdf) and
[complete answer-key PDF](docs/examples/photo-folding/ak_photo_folding.pdf).

## Install

### CC Switch: install the release ZIP

1. Open [Releases](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest)
   and download the asset named **`math-worksheets-v*.zip`**.
2. In **CC Switch → Skills → Install from ZIP**, select the downloaded ZIP.
3. Enable/sync the skill for Claude Code, Codex or your chosen agent.
4. Install the runtime dependencies below. If the skill does not appear, restart
   the agent, or point it directly at the installed `SKILL.md`.

The ZIP contains one `math-worksheets/` directory with the skill, scripts,
templates, references and license. README images, example PDFs, tests and release
tools stay outside the installable package. SHA-256 files are attached to releases.
See [CC Switch's Skills guide](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/zh/3-extensions/3.3-skills.md).

### Manual installation

Extract the same ZIP, then place its **`math-worksheets` folder** in your agent's
skill location:

| Agent | Personal skill directory |
|---|---|
| Claude Code | `~/.claude/skills/math-worksheets/` |
| Codex | `~/.agents/skills/math-worksheets/` |
| Other agents | Use their skill directory, or explicitly reference `SKILL.md` |

Codex users can explicitly mention `$math-worksheets`; other agents can use the
plain-language prompts below. See the [official skill documentation](https://learn.chatgpt.com/docs/build-skills).
To inspect/develop the fork, clone it anywhere:

```bash
git clone --depth 1 https://github.com/Tommie-P-xl/math-worksheets-skill.git
```

Then ask: `Follow /absolute/path/math-worksheets-skill/SKILL.md to make my worksheet.`

### Runtime dependencies

| Tool | Purpose |
|---|---|
| Bash | Run the build chain; on Windows, Git Bash or MSYS2 |
| Python + SymPy ≥1.12 | Answer checking; recommend the measured upstream version 1.14.0 |
| Tectonic or pdflatex | Compile ordinary LaTeX documents; pgfplots ≥1.18 required |
| XeLaTeX + CJK fonts | Chinese/Unicode examples; ctex and Fandol fonts are used here |
| Poppler `pdftotext` | Check text positions in the compiled PDFs |

```bash
python -m pip install "sympy==1.14.0"
```

Use [Tectonic](https://github.com/tectonic-typesetting/tectonic/releases) or an
installed TeX distribution. On Debian/Ubuntu, Chinese examples need
`texlive-xetex` and `texlive-lang-chinese`; Poppler tools are in `poppler-utils`.
On Windows, run the scripts in Bash with Python, TeX and `pdftotext` on its PATH.
If multiple Pythons are installed, set `MWS_PYTHON` to the interpreter that has
SymPy. `MWS_LATEX_ENGINE=xelatex` explicitly selects the Chinese-capable engine;
auto mode detects ctex/xeCJK/fontspec documents.

## Prompt templates

Question layout is compact by default, without reserved writing space between stems.
Original fill-in blanks remain. Ask explicitly for writing room when desired.
Geometry labels use transparent backgrounds and are placed clear of lines.

### General request

```text
Use math-worksheets.
Mode: [new practice / reproduce supplied questions / study guide only]
Input/topic: [topic, pasted question text, or attached screenshots/photos]
Level and quantity: [for new practice; do not add questions in reproduction mode]
Language/paper: [English/Chinese/etc.; A4/Letter]
Deliver: [worksheet + concise key + guide / worksheet + key / worksheet only]
Figures: redraw mathematical figures programmatically; ask about complex photos.
Answers: solve independently, verify supported responses, keep explanations concise.
Output directory: [your chosen folder]
```

### Function 1 prompt templates: generate practice questions

| Scenario | Copyable prompt |
|---|---|
| Law of sines/cosines | `Use math-worksheets to make Leo 8 law-of-sines/cosines problems, with a figure for each, a worked key and a study guide.` |
| Elementary multiplication | `Make Lucy, a third grader, a 12-problem times-tables worksheet, with an answer key and study guide.` |
| Factoring | `Make 15 factoring-trinomial problems for an eighth grader, ramping the difficulty, with concise worked solutions.` |
| Data handling | `Make 8 problems reading a bar chart and calculating mean, median, mode and range. Include the chart, verified answers and a guide.` |
| Calculus | `Make 10 AP Calculus chain-rule problems with a worked key and a short derivative-rules guide.` |
| Tiered equations | `Make support/core/challenge systems-of-equations worksheets aligned to 8.EE.C.8. Verify each tier separately and include its key.` |
| New practice from a style reference | `Use this homework photo as a style/difficulty reference, then create 10 NEW graphing-polynomial problems with matching grids and worked answers.` |

The style-reference case creates **new questions**. To typeset the original
questions themselves, choose reproduction below.

### Function 2 prompt templates: reproduce and explain supplied questions

**Text input**

```text
Use math-worksheets to turn the question text below into an A4 PDF.
Keep the original wording, values, options and order; do not create extra questions.
Redraw functions/geometry where needed. Solve independently and deliver a concise key.
[Paste the questions here]
```

**Screenshot/photo with handwriting — the real example above**

```text
Use math-worksheets to reproduce the attached geometry photo as a Chinese A4 worksheet.
Keep all three parts, labels, conditions and their order. Exclude handwritten answers.
Ask about any important symbol/label obscured by handwriting rather than guessing.
Redraw both mathematical figures with code. Independently solve and verify the answers.
Deliver the worksheet and a concise key, with an explanation diagram for the last part.
No study guide is needed. Save everything in my chosen output directory.
```

**Student PDF only**

```text
Reproduce these supplied questions using math-worksheets. Deliver only the blank
student worksheet; solve/check the answers internally. Exclude handwritten working
and do not add answer-only auxiliary lines to the student figures.
```

**Complex photo/illustration**

```text
Typeset this train/photo-based question. Redraw mathematical diagrams with code.
For the complex image, first offer a clean crop, then supported image generation,
then a programmatic schematic preserving all solving information. Let me choose.
Do not invent labels or reconstruct unreadable givens from an imagined answer.
```

**Graphical explanation or guide only**

```text
Make a concise verified answer key for these supplied function/geometry questions.
Add a small programmed diagram where intersections, auxiliary lines or an abstract
step need visual explanation. Keep solution-only information out of the student PDF.
```

```text
Make only a two-page study guide for [topic], with rules, worked examples and try-it
questions. Verify the computed results; do not generate a separate worksheet.
```

## How it works

The agent designs or transcribes questions, independently solves them, and writes
LaTeX plus verification JSON. The build checks answer data, answer slots, units,
source consistency and writing space, compiles the PDFs, then checks text collisions.
Reproduction additionally binds reviewed transcription and external-image records.

| Mode | Default documents |
|---|---|
| New practice | Worksheet + key + guide |
| Existing questions | Worksheet + key; guide optional |
| Worksheet only | Student PDF; answers still checked internally |
| Guide only | Guide PDF with checked examples |

Proofs, explanations, OCR fidelity and external-image content require review.
The CAS gate verifies supported mathematics, not every sentence of a proof or
every pixel of a figure. A clear review record is not a machine proof.

## Attribution

Fork of [stellawuellner/math-worksheets-skill](https://github.com/stellawuellner/math-worksheets-skill).
Retains its verifier, templates and mathematical references. Original previews
come from upstream commit `21312be`; the Chinese photograph example was generated
and checked in this fork. [MIT license](LICENSE).
