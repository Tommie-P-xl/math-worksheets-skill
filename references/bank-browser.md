# Browse first, then ask for similar questions

## Open the bank

Use the existing Python (3.11 or newer) and an installed browser on Windows,
macOS or Linux. Basic browsing needs no Bash, SymPy, web server, npm or pip
package. Generating full TikZ/pgfplots previews uses existing TeX and Poppler
tools as described below. Resolve `SKILL_DIR` as usual; use absolute paths:

```text
python SKILL_DIR/scripts/question_bank.py browse --out WORK/bank.html --open
```

Install/update the skill from the latest ZIP and reload it in the agent first;
there is no separate enable switch. Use `~/MathWorksheetsBrowse/bank.html` as a
persistent default output when no work directory was requested. Existing schema-2
data needs no migration or initialization. Question numbers are consecutive in
first-archival order; guide and revision events do not consume question numbers.
For legacy schema 1 only, follow the migration procedure in
[question-bank.md](question-bank.md). For a non-default data home, append
`--home "ACTUAL_BANK_HOME"` to the browse command and use that same home for
subsequent reference selection.

If the platform uses `python3`, substitute that command. `--open` attempts to
launch the default browser. If no graphical browser is available, return the
generated file link so the user can open it on a desktop. The file contains its
data, scripts, formula renderer and fonts; it can be moved and opened offline.
The output must be outside the skill installation and bank data home. Repeating
the command refreshes that output file, leaving the database unchanged.
An empty bank produces an empty-state page and does not initialize personal storage.

The page supports keyword/short-number search, stage, subject, grade, topic, type
and difficulty filters, pagination and two view modes:

- **摘要卡片** is the default desktop three-column overview: number, title,
  keywords, summary and demand metadata, with no full stem, images, zoom controls
  or answer expander. Narrow screens reduce the number of columns.
- **详细展示** shows one complete question per row with all subparts and compact
  diagrams. Answers and solutions expand here, using the same text/formula
  renderer and showing their auxiliary figures in place. Images, including
  answer images and zoom controls, exist only in this mode.

Neither view displays a separate diagram-givens section. Stored semantic givens
remain available to agent retrieval; they are not duplicated in the visual page.
Mode, filter and page changes retain the current reference selection. Select
references across pages and filters, then choose **复制参考提示词**. Selection
lasts for the current page session; refreshing the page clears it. The prompt
contains short numbers, the bank home, titles and revisions. **复制题号** copies
only the short numbers, useful within a chat already using the same bank.
If clipboard access is unavailable, use the visible manual-copy text area.

## Resolve the selected questions

Example user request after browsing:

> 参考题库 Q1、Q3，各出 2 道同类型题。保持推理结构，计算量稍降。
> 输出中文 A4 题目和答案，暂不收录新题。

1. Read `config`, use the bank home provided with the request (default home when
   none was specified), and retrieve the exact references:

   ```text
   python SKILL_DIR/scripts/question_bank.py select Q1 Q3 --fields title,stem,answer,solution,alternative_solutions,tags,demand,diagram,verification
   ```

   Add `--home BANK_HOME` when the copied prompt names a non-default home.
   `show Q1` also works. Unknown numbers are errors; do not guess a nearby record.
2. Check title/revision against the copied snapshot. If changed, explain the
   difference before relying on it; if a different bank is indicated, use that
   bank. Short numbers alone have meaning only within the same bank.
3. Keep selected questions and any guide documents within the configured combined
   `reference_limit`. `select` deduplicates UUID/short-number aliases and rejects
   a selection over the cap; it never silently drops requested questions. Browser
   selection is for the human and does not put the full bank into model context.
4. Read the original givens, full solution and demand information. Preserve the
   skill/reasoning pattern and any requested difficulty adjustment, solve the
   new questions independently, and use the ordinary worksheet workflow. Merely
   changing numbers is insufficient. Reference selection is not archival consent.

## Short number contract

`Q` plus a positive decimal number, with no padding or long hash: `Q1`, `Q27`.
The number is the question's consecutive position in first-archival order,
starting at 1. Guide updates and question revisions do not consume numbers.
Existing UUIDs and schema 2 stay unchanged; there is no migration, mapping file
or write on first browse. Numbers do not change when sorting, filtering, revising,
adding questions or restoring the same backup. A separately created bank can have the
same numbers; JSONL export alone is not a backup of the numbering/history.

Commands return `id` (original internal ID), `short_id` and `revision`. Use the
internal ID from `show`/`select` in revision proposals and guide-review commands.
When upgrading from event-based numbers, old gaps close and subsequent question
numbers move forward. Regenerate old snapshots and reselect references using the
current titles/revisions; do not interpret old event-based numbers as aliases,
because they may now name a different question.

A record without an archival event is not assigned an invented number; inspect
its history and use its full ID instead. Normal approved inserts always have one.

## What is rendered

### Copy or export one question

Stems and answers separate numbered subparts and prose paragraphs, with substantial
derivations on their own lines. Legacy dense prose receives conservative paragraph
breaks without changing mathematical source or drawing code. Multiple saved
methods appear as numbered sections; all answer exports include each method's
complete content and diagrams. Primary `solution` works as before; optional
`alternative_solutions` entries `{title, solution}` add named methods without a
schema migration. See [solutions.md](solutions.md) for the authoring convention.

Detailed mode provides **复制题干 Markdown** beside the stem and
**复制答案 Markdown** inside the expanded answers. Copying preserves mathematical
source using `$…$` and `$$…$$`; diagram nodes preserve their original fenced
TikZ/SVG source, including figures embedded in solutions and answer overlays.
The original bank record is unchanged. `.md` downloads provide the same text;
when clipboard access is unavailable, a local text box permits manual copying.

Each toolbar's range selector chooses **仅题干**, **仅答案**, or **题干和答案**
for visual export. **导出 PDF** opens a rendered preview; click
**打印 / 保存 PDF** and choose the browser's Save as PDF destination. Turn off
browser headers/footers if desired. Print CSS excludes the bank UI and metadata.
**导出 PNG** downloads a 2× image at a fixed 760-CSS-pixel content width, including
on mobile. Both use the same safe renderer, embedded images and formula fonts.
No server, network, new bank event, npm installation or extra Python package is
involved. The MIT-licensed 20 KB html-to-image browser bundle and its license are
included in the skill ZIP and embedded in each HTML snapshot. PDF uses the
installed browser's print engine. If a browser cannot create PNG, the preview
remains available with an export error and the PDF option.

Default figure previews are limited to 288 × 224 CSS pixels (and the available
container width), near worksheet figure-to-text proportions; the full-resolution
image remains accessible by clicking. This applies to question and answer
figures equally. Inline/display math uses no scroll containers; formulas that
exceed their content width scale to fit instead of showing tiny scrollbars.

### Saved content and preview dependencies

- Stems, answers and solutions share one safe content renderer. Inline/display TeX formulas using `$…$`,
  `$$…$$`, `\(…\)` and `\[…\]` render using bundled KaTeX with all WOFF2 fonts.
  Common LaTeX text wrappers, `\textbf`, `\par`, nested enumerate/itemize lists,
  circled subpart labels, blanks and `\ans` are rendered as readable content.
  Older undelimited math runs are recognized for display, including `sqrt`
  notation, Chinese angle prefixes such as `角ACD` and plain line names `l1`/`l2`
  (shown as `\angle ACD` and `l_1`/`l_2`); arithmetic and saved source are preserved.
  Explicitly delimited TeX is not rewritten. Unsupported math remains visible as source/error text. This is a preview, not
  a replacement for the full LaTeX worksheet build.
- Simple stored SVG geometry and plots render as an image. The supported static
  subset includes paths, lines, polygons, circles, text and groups with geometry,
  transform, font and paint attributes. SVGs using external resources, styles,
  scripts, definitions or unsupported elements display their code instead.
- TikZ/pgfplots are compiled at export time using XeLaTeX (preferred) or pdfLaTeX
  with standalone/TikZ/pgfplots packages, then converted to PNG with Poppler's
  `pdftoppm`. Chinese/Unicode labels require XeLaTeX and ctex/Fandol fonts.
  Original `tikzpicture` blocks are rendered in order, including multiple figures
  wrapped in worksheet minipages. Bare TikZ/axis code is wrapped in a picture.
  Numeric-coordinate geometry is enlarged when its original physical scale is
  too small; recognized Latin point labels are positioned clear of straight
  segments and other labels using the shipped geometry helper. Straight paths
  with named, numeric or mixed endpoints all count, including coordinate axes.
  Coordinates and
  geometry are not changed. Images are embedded in the HTML, displayed and
  enlarged only in detailed mode. No TeX engine is bundled into the ZIP or
  loaded in the browser.
- TikZ/SVG figures embedded in answers and worked solutions are rendered at their
  content positions. Distinct `answer_overlay` figures appear as answer
  supplements; figures already present in the solution are not appended twice.
  Bare TikZ overlays on a single saved question picture are composed into a
  separate answer image. Answer-only figures are never added to the question.
- Missing tools, invalid code or rendering timeouts leave a specific page notice
  and a `diagram_warnings` entry in the command's JSON result. Inspect these
  warnings instead of treating a source-only card as a rendered figure. Fix the
  indicated dependency/code, then regenerate. To intentionally skip compilation,
  use `browse --out WORK/bank.html --no-diagrams`.

The HTML is a complete snapshot of the approved questions, including solutions;
it is not bundled into the installation ZIP. Personal questions remain outside
the skill. Rendering runs in temporary working directories without shell escape
and does not update bank records. No CDN requests or network service are used by
the viewer. An exported page with its images can be opened on a machine without
any TeX tools.

## Lightweight options considered

| Option | Runtime and distribution | Fit for this scenario |
| --- | --- | --- |
| **Python stdlib → standalone HTML + bundled KaTeX (chosen)** | Existing Python generates once; optional installed TeX/Poppler renders TikZ; browser opens the resulting offline file | Cross-platform, no running service, fixed short numbers, moveable snapshot |
| HTML with CDN formula rendering | Smaller installation, network needed for uncached formulas/fonts | Less suitable for reliably offline browsing |
| Python local HTTP viewer | Python and browser; a process/port stays open | Useful if live updates or editing become necessary; current task only selects references |
| Framework/server UI | Additional Python/JS packages and a running service | More setup than this read-only picker needs |
| Bundled desktop runtime | Separate runtime/binaries for each OS | Unnecessary packaging cost when a browser is already available |

KaTeX's [browser distribution](https://katex.org/docs/browser.html) documents the
JS/CSS/font assets. The ZIP includes the minified scripts, CSS, WOFF2 fonts and
MIT license, not npm tooling or other font formats. Snapshot generation embeds
only WOFF2 font sources as data URLs. See `templates/katex/NOTICE` for the pinned
version, upstream distribution and integrity hash. Refreshing this vendor code
is a maintainer action; no downloads occur on a user's browse command.

Measured in this change: the complete runtime ZIP is about **0.64 MiB**, versus
about **0.28 MiB** before the viewer (roughly **0.36 MiB** added). The standalone
four-question demo HTML is about **0.67 MiB**, including embedded fonts and
scripts. Actual snapshots grow with the stored question/solution text and SVGs.
These measurements describe generated artifacts, not installed browser size.
