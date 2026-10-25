# LaTeX templates

## Default shell

Use only the content the user requested, in the document language. The shared
preamble provides 12 mm margins, compact lists and language-neutral components.
It does not print a school name, name/date fields, instructions, English document
labels, verification/curriculum summaries, or a decorative separator by default.
Do not copy contextual examples, sample names or unused sections into a PDF.

```latex
\documentclass[12pt,a4paper]{article}
% Chinese: use \documentclass[UTF8,fontset=fandol,12pt,a4paper]{ctexart}
\input{worksheet-preamble}
\begin{document}
\wstitleblock{Requested title}{}{}
\problem{The actual question.}
\end{document}
```

Do not load geometry with hard-coded margins. `compile.sh` copies the shared
components and refreshes `mws-settings.tex` from the global `config.json` on every
build. Direct engine invocation uses the 12 mm fallback unless the generated
settings file is present; use the build scripts for current user settings.
A4, Letter and Legal are document-class options, chosen for the user's context.

## Components

| Component | Behavior |
| --- | --- |
| `\problem{stem}` | Numbered compact problem, no trailing work space; long content can span pages |
| `\worksheetlayout{spacious}` + `\problem[4cm]{stem}` | Explicitly requested work space |
| `\ans{...}` | Final mathematical answer; use in checked answer segments |
| `\wstitleblock{title}{subtitle}{date}` | Print only supplied nonempty fields |
| `\aktitleblock{title}{subtitle}{date}` | Same neutral title component; supply the actual answer-key title |
| `\sstitleblock{title}` | Supplied title only |
| `\wsheader{title}`, `\akheader{title}`, `\ssheader{title}` | Optional supplied running title, without a fixed suffix/prefix |
| `\akheader{title}` | Also enables compact answer boxes and paragraph spacing |
| `formulabox`, `examplebox`, `tryitbox`, `watchoutbox` | Optional boxes without printed labels; write any needed heading in the document language |
| `\step{...}`, `\why{...}`, `\fadestep{...}` | Numbered step, explanation or supplied partial step; no fixed English prose |

For combined PDFs, put all questions first, then start the answers on a new page.
Keep solution-only constructions out of student questions. Solutions that add
auxiliary objects must draw and label them beside the relevant reasoning.
Use fully braced `\frac{...}{...}` for printed mathematical quotients.

`\ansline`, `\ansblank`, `\answerline{unit}` are opt-in answer-location
components, not a reason to add blanks to a compact worksheet. `\noansline`
suppresses a trailing line in spacious mode. Do not redefine layout macros.
Optional localized labels `\mwsnamelabel`, `\mwsdatelabel`, `\mwsstemlabel`,
`\mwsleaflabel` may be renewed by a document that actually needs them.

## Answer keys and optional metadata

The default key contains the requested title and worked solutions. Quick-answer
tables are disabled (`quick_answers: false`). Existing `\input{qa_STEM}` lines
remain compatible: the renderer refreshes the file with no printed content.
When enabled, add `\input{qa_STEM}` under the title. Verification and curriculum
metadata belong in reports/conversation; the default PDF has no appended report.

## Figures, accessibility and notation

Read [figure-patterns.md](figure-patterns.md) only for needed diagram/plot patterns.
Use `\input{figure-macros}` for shipped figure components. Plotted numbers and
semantic givens must agree with the verification data. Labels on geometry have
transparent backgrounds and clear anchors; inspect the final rendered pages.

Large print uses `extarticle` with 14pt/17pt and
`\accessiblemode{large|dyslexia|both}`. `\mwslocale{eu}` changes `\dec{3.75}`
to decimal-comma notation and `\mtimes` to multiplication-cross notation; the
verification JSON retains ordinary decimal points and computation syntax.

## Page budget

`page_budget.py --from-tex FILE` estimates pages from problem count, type size,
figures and requested work space. A budget is not proof of visual quality.
If a document overruns, inspect actual pages and remove unused sections or split
long content. Never shrink readable figures to force a page target.
Study-guide JSON `pages` controls its page cap (default 2, allowed 1–6).
