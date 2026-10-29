<a id="readme-top"></a>

<div align="center">

<h1>Math Worksheets Skill</h1>
<p><strong>Math practice, faithful reproduction and reusable authoring guidance for your AI agent</strong></p>

<p>
  <a href="https://github.com/Tommie-P-xl/math-worksheets-skill/actions/workflows/tests.yml"><img src="https://github.com/Tommie-P-xl/math-worksheets-skill/actions/workflows/tests.yml/badge.svg" alt="Checks"></a>
  <a href="VERSION"><img src="https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2FTommie-P-xl%2Fmath-worksheets-skill%2Fmain%2FVERSION&amp;query=%24&amp;prefix=v&amp;label=version&amp;color=2563eb&amp;cacheSeconds=300" alt="Skill version from VERSION"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-64748b" alt="MIT license"></a>
</p>

<p><a href="README.zh-CN.md">简体中文</a> &nbsp;|&nbsp; <a href="README.md">English</a></p>
<p><a href="#quick-start">Quick start</a> &nbsp;·&nbsp; <a href="#output-previews">Output previews</a> &nbsp;·&nbsp; <a href="#global-question-bank">Global bank</a> &nbsp;·&nbsp; <a href="#prompt-templates">Prompt templates</a></p>

</div>


Ask your AI agent for math practice, or give it existing questions as text,
screenshots or photos. Get printable PDFs, independently checked answers and
mathematical diagrams drawn with code. Supports elementary math through AP
Calculus BC, using the model and tools your agent already has.

An optional global question bank supplies reusable examples and authoring guidance.
Archival is off by default: each question and guide update needs separate user
review and approval. See [the bank workflow](references/question-bank.md).

| New practice | Faithful reproduction | Global reference bank |
|:---|:---|:---|
| Design within taught scope, solve independently, and deliver questions, keys and optional guides. | Review photos and handwriting, preserve original givens, and redraw mathematical figures with code. | Reuse approved examples and authoring guidance across projects; archival is off by default. |


<details>
<summary>Contents</summary>

- [Quick start](#quick-start)
- [Output previews](#output-previews)
- [Install](#install)
- [Prompt templates](#prompt-templates)
- [How it works](#how-it-works)
- [Global question bank](#global-question-bank)
- [Version and builds](#version-and-builds)
- [Attribution](#attribution)

</details>


---

<a id="quick-start"></a>

## Quick start

| 1 · Install the skill | 2 · Prepare the runtime | 3 · Ask your agent |
|---|---|---|
| Download `math-worksheets.zip` from [Releases](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest), then install with CC Switch or manually. | Bank management needs only Python; PDF output additionally needs Bash, SymPy, LaTeX and Poppler. See [full dependencies](#runtime-dependencies). | Specify taught scope, count, language and deliverables, or upload questions for faithful reproduction. |

```text
Use math-worksheets to create 4 NEW questions similar to the uploaded example.
Confirm the grade and taught methods; match its assessment structure and demand.
Deliver an A4 worksheet and detailed key, with questions and answers on separate pages.
Ask before saving each question or guide update; do not archive without my approval.
```

> **Choose the mode first:** use new practice for style references, and reproduction
> to preserve supplied wording and numbers. Calculation checks are not automatic
> proofs of every explanation or figure; see [How it works](#how-it-works).


---

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

<p align="right"><a href="#readme-top">Back to top</a></p>


---

### Function 3: browse the bank, then request similar questions by number

| Summary cards: three-column selection | Detailed view: full question and answer figures |
|:---:|:---:|
| [<img src="docs/examples/bank-browser/browser.png" width="480" alt="Three-column summary cards without figures">](docs/examples/bank-browser/browser.png) | [<img src="docs/examples/bank-browser/browser-detail.png" width="480" alt="One question per row with formulas, question figure and worked-answer figure">](docs/examples/bank-browser/browser-detail.png) |

| 1 · Open the bank | 2 · Choose references | 3 · Return to chat |
|---|---|---|
| Ask the agent: “Open my question bank so I can choose reference questions.” | Filter by grade, topic, type or difficulty; select summary cards and switch to the detailed view to inspect full questions and answers. | Click **复制参考提示词** (copy reference prompt), paste into chat and add the quantity, taught scope and deliverables. |

The screenshot shows the working tool with **four synthetic demo questions**.
The summary screenshot selects similar triangles `Q1` and Pythagoras `Q3`; the
detailed screenshot expands Q3 and its answer figure. Short numbers stay fixed
across view changes, filters, pages, revisions and new inserts.
For example, the next chat message can be:

```text
Use math-worksheets. Make two new questions of the same type as each of Q1 and Q3.
The grade-9 student has learned similar triangles and the Pythagorean theorem.
Preserve the reasoning structure, with slightly lighter calculations.
Deliver a Chinese A4 worksheet and answer key. Do not archive the new questions.
```

The agent resolves those exact records, reads their full solutions and demand
information, then designs and independently checks new questions. The copied
prompt includes the **bank home, titles and revisions** for matching the viewed
records. Demo numbers belong only to the demo bank; use your own bank's numbers.

The installable ZIP includes the viewer, KaTeX renderer, fonts and licenses.
Basic browsing needs only existing Python and a desktop browser; there is no
server, frontend installation or CDN request. During export, saved TikZ/pgfplots
are automatically compiled with existing TeX/Poppler tools and embedded into the
HTML. Opening that generated page requires neither TeX nor network access.

<a id="bank-browser-start"></a>

#### Enable and open the question browser

**Install the latest ZIP containing the viewer first.** To upgrade, update the
same installed skill from the new ZIP, then reload skills or restart the agent.
There is no additional enable switch. Personal bank data is outside the ZIP and
is not replaced by a skill update. Existing schema-2 banks need no migration;
do not run `init` or `migrate --apply` just to enable browsing. For schema 1,
follow [Upgrade an existing bank](#upgrade-an-existing-bank).

The easiest launch method is to tell the agent:

```text
Use math-worksheets. Open my global question bank for browsing and give me the HTML file link.
```

For a manual launch, **set `skillDir` / `SKILL_DIR` to the actual directory
containing `SKILL.md`**. These examples use Codex's manual install location;
check CC Switch for its installed path. Existing installations may also live
under `~/.codex/skills/math-worksheets`.

**Windows PowerShell:**

```powershell
$skillDir = "$env:USERPROFILE\.agents\skills\math-worksheets"
$browseFile = "$env:USERPROFILE\MathWorksheetsBrowse\bank.html"
python "$skillDir\scripts\question_bank.py" browse --out $browseFile --open
```

**macOS / Linux terminal:**

```bash
SKILL_DIR="$HOME/.agents/skills/math-worksheets"
python3 "$SKILL_DIR/scripts/question_bank.py" browse --out "$HOME/MathWorksheetsBrowse/bank.html" --open
```

The command creates `~/MathWorksheetsBrowse/bank.html` and attempts to open it
in the default browser. If that fails, double-click the file or follow the
agent's file link. The output directory is created automatically and must be
outside the skill and bank data directories. For a custom bank, append
`--home "ACTUAL_BANK_HOME"`. An empty bank shows an empty page; approve questions
for archival before browsing them.

The two buttons above the results switch between:

- **摘要卡片** (summary cards): three compact desktop columns with numbers, titles, keywords, summaries and difficulty. Full stems, all images and answer expanders are omitted; narrow screens reduce the column count.
- **详细展示** (detailed view): one complete question per row with compact worksheet-scale figures and structured subparts. Click images to enlarge, or expand **查看答案与完整解答** for rendered answers, worked solutions and auxiliary figures. Images and zoom controls appear only in this mode.

Each detailed question also provides:

- **复制题干 Markdown / 复制答案 Markdown**: copy the stem or answers separately, with `$…$` / `$$…$$` formulas and fenced TikZ/SVG source for figures, ready for AI discussion. The answers include the final result, worked solution and supplementary diagrams. Each part also has an `.md` download.
- **导出 PDF**: choose stem only, answers only, or both, then open the preview and click **打印 / 保存 PDF**. Select Save as PDF in the browser's print dialog; disable browser headers and footers for a clean document.
- **导出 PNG**: the same range selector downloads a high-resolution PNG with rendered formulas and images. PDF/PNG contain only the selected content, without filters, selection controls or source metadata.

Exports run locally offline without changing the bank or requiring Node.js.
Inline formulas no longer create scrollbar widgets; formulas wider than their
container scale to fit the available width.

**Answer layout and multiple methods:** start each subpart/case on a separate
paragraph, display key derivations, and give the reason, calculation/proof and
conclusion in order. Keep the primary method in `solution` and additional complete
methods in optional `alternative_solutions` entries `{title, solution}`. HTML shows
numbered method sections; answer Markdown and answer/both PDF/PNG exports include
all methods with their formulas and auxiliary diagrams. Existing single-method
records need no migration or duplication. Ask the agent to add a named method to
the original question and review the revision before saving. Demo Q3 includes
Pythagoras and a coordinate method. See [answer conventions](references/solutions.md)
and [bank JSON](references/question-bank.md).

Neither mode shows a separate diagram-givens section. Stems, answers and solutions
share formula rendering, including common LaTeX text/list structures, nested
numbering, the `\ans` macro and legacy expressions without math delimiters.
Reference selection persists across modes. Select questions, click **复制参考提示词**, then paste the prompt into
chat with the requested quantity and deliverables. Re-run the same command and
refresh the browser after bank changes; no skill reinstall is needed.
Simple SVG, TikZ and pgfplots diagrams are previewed. All saved figures for a
question appear in order and can be clicked to enlarge. Export also renders
auxiliary diagrams embedded in solutions, without appending
duplicates from answer overlays. Tiny numeric-coordinate drawings receive a
readable preview scale and clear point-label positions; saved coordinates and
database content remain unchanged. Generating TikZ/pgfplots
previews requires **XeLaTeX (or pdfLaTeX) and `pdftoppm`** on PATH, with the
standalone, TikZ and pgfplots packages. Chinese/Unicode labels additionally need
XeLaTeX and ctex/Fandol fonts. Missing tools or compilation failures produce a
specific page notice and a `diagram_warnings` entry with the question number;
install the missing dependencies and regenerate. Use `--no-diagrams` to
deliberately skip TeX compilation for a quick text-only export.
After upgrading the skill, regenerate older HTML snapshots with the new
`browse` command before refreshing the browser; reloading an old snapshot alone
cannot add the previously omitted images.

[Scenario and reproduction steps](docs/examples/bank-browser/README.md) ·
[Download the offline demo HTML](https://github.com/Tommie-P-xl/math-worksheets-skill/raw/refs/heads/main/docs/examples/bank-browser/browser.html) ·
[Lightweight options and usage](references/bank-browser.md)

---

## Install

### CC Switch: install the release ZIP

1. Open [Releases](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest)
   and download the asset named **`math-worksheets.zip`**.
2. In **CC Switch → Skills → Install from ZIP**, select the downloaded ZIP.
3. Enable/sync the skill for Claude Code, Codex or your chosen agent.
4. Install the runtime dependencies below. If the skill does not appear, restart
   the agent, or point it directly at the installed `SKILL.md`.

The ZIP contains one `math-worksheets/` directory with the skill, scripts,
templates, references, offline bank viewer, formula fonts and licenses. README images, example PDFs, tests and release
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
| Python ≥3.10 + SymPy ≥1.12 | Answer checking; recommend the measured upstream version 1.14.0 |
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

<p align="right"><a href="#readme-top">Back to top</a></p>


---

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


<details>
<summary>Text input</summary>

**Text input**

```text
Use math-worksheets to turn the question text below into an A4 PDF.
Keep the original wording, values, options and order; do not create extra questions.
Redraw functions/geometry where needed. Solve independently and deliver a concise key.
[Paste the questions here]
```

</details>

<details>
<summary>Screenshot/photo with handwriting — the real example above</summary>

**Screenshot/photo with handwriting — the real example above**

```text
Use math-worksheets to reproduce the attached geometry photo as a Chinese A4 worksheet.
Keep all three parts, labels, conditions and their order. Exclude handwritten answers.
Ask about any important symbol/label obscured by handwriting rather than guessing.
Redraw both mathematical figures with code. Independently solve and verify the answers.
Deliver the worksheet and a concise key, with an explanation diagram for the last part.
No study guide is needed. Save everything in my chosen output directory.
```

</details>

<details>
<summary>Student PDF only</summary>

**Student PDF only**

```text
Reproduce these supplied questions using math-worksheets. Deliver only the blank
student worksheet; solve/check the answers internally. Exclude handwritten working
and do not add answer-only auxiliary lines to the student figures.
```

</details>

<details>
<summary>Complex photo/illustration</summary>

**Complex photo/illustration**

```text
Typeset this train/photo-based question. Redraw mathematical diagrams with code.
For the complex image, first offer a clean crop, then supported image generation,
then a programmatic schematic preserving all solving information. Let me choose.
Do not invent labels or reconstruct unreadable givens from an imagined answer.
```

</details>

<details>
<summary>Graphical explanation or guide only</summary>

**Graphical explanation or guide only**

```text
Make a concise verified answer key for these supplied function/geometry questions.
Whenever a solution adds auxiliary lines, intersections or reflected points,
include the resulting labeled diagram in that answer. Use LaTeX fraction commands
for every mathematical quotient in answers, including intermediate steps and
coordinates; do not print slash fractions. Keep solution-only information out of
the student PDF.
```

```text
Make only a two-page study guide for [topic], with rules, worked examples and try-it
questions. Verify the computed results; do not generate a separate worksheet.
```

</details>


<p align="right"><a href="#readme-top">Back to top</a></p>


---

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

<p align="right"><a href="#readme-top">Back to top</a></p>


---

## Global question bank

The bank stores **text and code only**: complete stems, answers, worked solutions,
tags, demand analysis, semantic diagram givens, and inline TikZ/pgfplots/SVG.
Plots and auxiliary constructions are code, so an agent can understand a saved
reference entirely from text. Photos can still be current-task inputs; the bank
keeps filename/locator/hash or URL provenance and never copies their bytes.
Personal bank data is excluded from installable packages.

Questions still require individual user approval. After an insert/revision,
inspect the stage/subject guide: propose an approved concise update when the
solution contributes reusable guidance, or record an assessment that existing
guidance suffices. `guide-status` tracks pending IDs and revisions. Each
stage/subject has one directly editable Markdown guide.

### Data home and live configuration

| Platform | Default home |
| --- | --- |
| Windows | `%LOCALAPPDATA%/MathWorksheets` |
| macOS | `~/Library/Application Support/MathWorksheets` |
| Linux | `${XDG_DATA_HOME:-~/.local/share}/math-worksheets` |

Override with `MWS_DATA_HOME` or `--home`. Reinstalling the skill preserves data.
`config --init` materializes a complete `config.json`; edits apply on the next
command/build. See [all settings](references/configuration.md).

The file remains standard JSON. `_comments` supplies a short Chinese description
and default for every parameter; it does not affect runtime values. `config --init`
refreshes those notes and fills missing defaults while preserving valid settings.
Existing configurations without `_comments` remain supported.

<details>
<summary>All configuration parameters, defaults and meanings</summary>

| Parameter | Default | Meaning |
| --- | --- | --- |
| `guide_max_chars` | `6000` | Maximum characters per stage/subject guide, including headings and links (500–12000). |
| `backup_keep` | `1` | Automatic backup generations to retain (1–100); manual backups are untouched. |
| `auto_backup_enabled` | `true` | Back up the committed previous state before writes. |
| `reference_limit` | `10` | Distinct question + guide references allowed per authoring request (1–100). |
| `reference_default` | `5` | Default retrieval count, including the guide; no greater than reference_limit. |
| `context_max_chars` | `10000` | Default retrieval character budget, at least 1200 and no greater than context_max_chars_limit. |
| `context_max_chars_limit` | `50000` | Largest allowed retrieval character budget, at most 1000000. |
| `guide_excerpt_chars` | `2400` | Maximum characters in a retrieved guide excerpt. |
| `stem_excerpt_chars` | `1600` | Maximum characters in each retrieved question stem excerpt. |
| `answer_excerpt_chars` | `500` | Maximum characters in each retrieved answer excerpt. |
| `solution_excerpt_chars` | `900` | Maximum characters in each solution excerpt; use show for complete text/code. |
| `givens_excerpt_chars` | `1200` | Maximum characters in each semantic diagram-givens excerpt. |
| `duplicate_threshold` | `0.82` | Text similarity threshold for duplicate review, greater than 0 and at most 1. |
| `duplicate_scan_limit` | `300` | Recent questions compared for possible duplicates. |
| `duplicate_candidate_limit` | `5` | Maximum possible duplicate candidates shown in a preview. |
| `guide_review_on_commit` | `true` | Require the agent to check guide coverage after question inserts or revisions. |
| `default_question_count` | `10` | Practice quantity when the user does not specify one. |
| `page_margin_left_mm` | `12` | PDF left text margin in millimeters (5–50). |
| `page_margin_right_mm` | `12` | PDF right text margin in millimeters (5–50). |
| `page_margin_top_mm` | `12` | PDF top text margin in millimeters (5–50); leave space for optional headers. |
| `page_margin_bottom_mm` | `12` | PDF bottom text margin in millimeters (5–50). |
| `page_numbers` | `true` | Display template page numbers. |
| `name_date_fields` | `false` | Display first-page name/date blanks; documents supply localized labels. |
| `header_rule` | `false` | Display a separator rule beneath the running header. |
| `quick_answers` | `false` | Generate a quick-answer table without a verification/curriculum appendix. |
| `problem_gap_mm` | `1.5` | Compact question spacing in millimeters; decimals are allowed. |
| `answer_problem_gap_mm` | `2` | Answer-key question spacing in millimeters; use a positive integer. |

</details>

Each write snapshots the committed previous state. Retention applies only to
tool-owned automatic backups; manual backups remain untouched. Snapshots contain
the database, guides, config and checksum manifest, with no images.

### Upgrade an existing bank

Install the updated skill, inspect the dry run, then explicitly apply it. Migration preserves
IDs, revisions, math text, complete solutions and drawing code. It removes
attachment dependencies from current records and audit history, validates a
text-only snapshot, then cleans managed source files. Visual-only solutions
block migration until their text/code is complete; missing mathematics is never
invented.

```bash
python SKILL_DIR/scripts/question_bank.py migrate
python SKILL_DIR/scripts/question_bank.py migrate --apply --backup-keep 1
python SKILL_DIR/scripts/question_bank.py doctor
python SKILL_DIR/scripts/question_bank.py stats
python SKILL_DIR/scripts/question_bank.py config --init
python SKILL_DIR/scripts/question_bank.py guide-status --stage 初中 --subject 数学
python SKILL_DIR/scripts/question_bank.py show QUESTION_ID
python SKILL_DIR/scripts/question_bank.py backup --out /chosen/path/bank.zip
```

Replace `SKILL_DIR` with the installation path; quote paths with spaces in
PowerShell. See [bank commands/schema](references/question-bank.md) for approvals,
export and restore. Restore old-schema ZIPs with a compatible older skill into
an isolated home before migrating them to schema 2.

### PDF templates

Defaults are compact content and 12 mm margins. Templates print supplied titles
and optional page numbers without fixed name/date text, continuation labels,
learning slogans, curriculum or verification appendix pages. Content follows the
requested language. Historical previews illustrate features rather than the current defaults.


---

## Version and builds

[Cumulative changes since v4.0.0](CHANGELOG.md).

Release identity is maintained only in root [`VERSION`](VERSION). The badge reads
that file directly, and publishing derives its tag from it. The badge service may
cache updates briefly.
[`tools/version.py`](tools/version.py) reads it for tag validation. Source files,
documentation and the fixed `math-worksheets.zip` filename contain no duplicated
skill release numbers. GitHub release titles/tags are derived when publishing.

| Artifact | Where to get it |
|---|---|
| Installable package and checksum | The [latest release](https://github.com/Tommie-P-xl/math-worksheets-skill/releases/latest) contains `math-worksheets.zip` and `.zip.sha256`. |
| Source and history | [Repository](https://github.com/Tommie-P-xl/math-worksheets-skill) · [Release notes](RELEASE_NOTES.md) · [Maintainer tools](tools/README.md) |

<details>
<summary>Expand: maintainer build and verification commands</summary>

```bash
python tools/version.py
python tools/version.py --tag
python tools/package_skill.py
python -m unittest discover -s tests -v
```

Build output goes to `dist/`; the ZIP contains only the `math-worksheets/` runtime
directory. The release workflow validates the tag, builds the package and runs
tests before publishing ZIP and SHA-256 assets. Full tests require the PDF runtime
above. Personal banks, originals and backups never enter the release package.

</details>


<p align="right"><a href="#readme-top">Back to top</a></p>


---

## Attribution

Fork of [stellawuellner/math-worksheets-skill](https://github.com/stellawuellner/math-worksheets-skill).
Retains its verifier, templates and mathematical references. Original previews
come from upstream commit `21312be`; the Chinese photograph example was generated
and checked in this fork. [MIT license](LICENSE).

<p align="right"><a href="#readme-top">Back to top</a></p>
