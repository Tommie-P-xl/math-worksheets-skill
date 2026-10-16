# New problem authoring

Before designing new/similar questions, follow [question-bank.md](question-bank.md):
extract the source demand, retrieve at most 10 bank questions/guide documents in
total, then use available official web references only when local context is
inadequate. Ask individually before archiving uploads, outputs or guide changes;
declining archival never blocks authoring. For Chinese curricula, align to the
confirmed taught scope rather than forcing an unrelated CCSS/AP grade label.

## Layout policy

Use compact question layout by default: no reserved working space between stems.
Keep original inline blanks and readable diagrams. Only when the user explicitly
requests writing room, add `\worksheetlayout{spacious}` and choose the requested
workspace. Examples below with positive `\problem[Ncm]`, large itemsep or blank
working grids are spacious examples, not defaults. This policy takes precedence
over older workspace recommendations in detailed examples.

Geometry letters/side labels have transparent backgrounds. Choose an anchor and
offset in a clear region; do not cover lines with white-filled label boxes. Inspect
the rendered figure at the intended print size. Tick-label styling and open-point
markers on coordinate graphs are separate from geometry letter placement.

Applies to newly designed worksheets. For source reproduction, read reproduction.md; its output choices and fidelity rules take precedence.

### 1. Gather requirements

Ask (or infer from context):
- **Student**: name, grade, course (e.g. "8th grade, Pre-Algebra")
- **Topic**: e.g. "factoring trinomials", "solving two-step equations"
- **Problem count**: default 10 if not specified
- **Page use**: the page budget is COMPUTED from the problem set (`scripts/page_budget.py`), not fixed. Fifty graphing problems that each need a coordinate plane legitimately run past 20 pages and are allowed to; a flat cap could only be met by shrinking the work space, which is the one thing that must never give. `build.sh` prints the ideal page count and the double-sided sheet count before compiling, so paper cost is visible. If a set is bigger than intended, reduce the PROBLEM COUNT, never the work space. Hard ceiling: 100 problems — past that, split into several worksheets
- **Paper size**: US Letter by default. For A4 or Legal, add the paper as a documentclass option (`\documentclass[12pt,a4paper]{article}`) with metric geometry margins, and pass `--paper a4` to `page_budget.py`. See `references/latex-templates.md` → "Paper size"
- **Accessibility**: for large-print or dyslexia-friendly output use `\documentclass[17pt]{extarticle}` (or 14pt) plus `\accessiblemode{large|dyslexia|both}`. The page budget adapts automatically; larger type simply means more pages. See `references/latex-templates.md` → "Accessibility"
- **Locale**: `\mwslocale{eu}` prints decimal commas and `\times`. The verify JSON stays canonical (period decimals) — only the printed form is localised, via `\dec{}` and `\mtimes`. Pair this with A4 paper for European users
- **Format preference**: timed quiz, homework practice, mixed difficulty, or topic drill.
  For a **timed quiz**, point values are the default: place `\probpts{N}` at the end of
  each stem and `Score: \underline{\hspace{1.5cm}} / \totalpoints\ pts` in the title
  block (rendered in step 4c). Difficulty stars (`\probmeta{N}`) are opt-in for
  practice/mixed-difficulty sheets on request; skip markers for early-elementary
  drills unless asked.

**Photo input shortcut**: If the user provides a photo of homework or a textbook page, read the image with whatever vision capability your agent provides (or by reading the image file directly) to extract problem types, format, and difficulty, then mirror that style exactly.

### 2. Design problems

Design problems appropriate to the student's level. Increase difficulty gradually across the set. Every problem must be mathematically correct — verify your own solutions.

See `references/problem-library.md` for topic-specific problem type menus.

**The grade level never prints on the worksheet or the study guide.** `\wstitleblock` takes a course argument and does not typeset it: a child working a grade below or above reads the label before the mathematics, and it tells the student nothing they need. The level is the adult's information, so it prints on the ANSWER KEY — in the title block and again in a generated **Curriculum** section beside the standards codes and the difficulty range, which is where a parent or teacher actually looks. Keep passing the course argument: it is the one place the level is declared, and the answer key's curriculum section reads it from there.

**Tag every problem** with `"standard"` (a code from `references/standards-map.md` — never invent codes, and **grep that file before concluding it lacks a row**: 11 reviewed cases asserted a missing row that was there, two of them naming the exact code they called absent, and then tagged a high-school sheet with a grade-8 standard), `"difficulty"` (1–5 per that file's ladders), `"bloom"` (recall/apply/analyze/justify, same file), and `"skill"` (a short stable name for the skill the problem exercises, e.g. `"right-triangle-trig"` — reuse the same name across problems of the same Part). Skill tags are all-or-nothing and GATING: the study guide must contain an entry tagged with each distinct worksheet skill, enforced by `build.sh`'s `coverage-ss` gate; a partially tagged sheet fails it. Ramp difficulty: start at 1–2, majority 2–3, end with one or two 4–5 challenges. Verification reports standards coverage, the bloom mix, the skill mix (the set the study guide must cover), and flags ramp drops, so a parent can see exactly which standards the sheet exercises and at what cognitive level.

**Facets (skill coverage):** a facet is a distinct method the sheet tests (e.g. `side-from-angle` vs `angle-from-sides` vs `pythagorean`) — standards codes are usually one constant per sheet and cannot show this. For sheets of 10+ problems, declare top-level `"facets": [...]` in the verify JSON and tag **every** problem with a `"facet"` from that list; consult `references/problem-library.md` → "Facet checklists" (topics without a table use your own lowercase-kebab names). The gate is strict: an unlisted facet, a planned facet with zero problems, or an untagged problem is a build failure. Tag TRUTH is your responsibility — the gate verifies plan/tag consistency, not that a tag describes its problem. Tag the `verify_ss_` entries' `"facet"` too: the facet-coverage gate (step 5) requires every worksheet facet to have a study-guide worked example.

**Interleave after the warm-up:** a blocked warm-up over the first third of the sheet is fine; after that, keep same-facet runs to 3 or fewer so the student must *choose* the method — unless the sheet is genuinely a drill, declared with top-level `"format": "drill"`. `verify.py` flags longer runs (exit 2, manual review) with a concrete swap suggestion. See `references/problem-library.md` → "How to interleave".

**Misconception traps:** consult the misconception table (`references/problem-library.md` → "Misconception traps & error analysis") when choosing givens — pick numbers so the canonical wrong method lands visibly off the correct answer — and declare `"traps"` on the 2–3 problems you designed that way. Traps are optional, but declared ones are machine-checked (step 4) AND printed in the answer key as a "Common wrong answers" block (`scripts/render_quick_answers.py` emits one `\commonerror` line per trap, so the grader sees "If they got 7.37: used cos instead of tan"). Declaring traps therefore pays twice: it hardens the problem design and it turns grading into teaching.

**Tiered worksheets (differentiation, on request):** when asked for tiers (support/on-level/challenge), build ONE set of problem skeletons, then re-parameterize per tier — same structure and standards, different givens and difficulty band (support: 1–2 with a hints box and a worked first step; core: 2–3; challenge: 3–5). Each tier gets its OWN verify JSON (the gate re-checks every tier) and file prefix: `wsS_`/`wsC_`/`wsX_` + matching keys. Because construction is JSON-first, a tier is a data change, not a rewrite.

**Tier naming for the build driver:** give each tier its own *stem* — `verify_factoring_S_2026-07-27.json` with `wsS_factoring_S_2026-07-27.tex` (or plain `ws_factoring_S_...`; both are discovered). What matters is that two tiers never share a stem in one directory: `scripts/build.sh` derives the document names from the verify JSON's stem, and two candidates for one role is a hard discovery error, not a guess.

### 3. Write LaTeX source

Follow SKILL.md's required answer presentation: include a labeled diagram of
every auxiliary construction used in a solution, and typeset all mathematical
quotients in answer text with fully braced LaTeX fraction commands. See
[solutions.md](solutions.md) for scope and examples; computation/JSON syntax
continues to use ordinary division operators.

Write **three** `.tex` files to `/tmp/`:
- `ws_TOPIC_DATE.tex` — student worksheet (blank work areas)
- `ak_TOPIC_DATE.tex` — answer key (full step-by-step solutions)
- `ss_TOPIC_DATE.tex` — skills summary / study guide (cheat sheet)

The **skills summary** is a reference card (2 pages by default — see "Length" below) the student can use while working through the worksheet or when studying. Per skill section: **formulabox → examplebox → tryitbox**. Its structure is not house taste; each element carries a documented learning effect, and the macros exist so using the effect costs one line:

- The worked example IS the worked-example effect: novices learn more from studying a worked solution than from solving, and the `\step` structure with a strategy first line is what makes the reasoning visible rather than just the arithmetic.
- The **try-it** is retrieval practice — the single best-supported study behaviour there is. It re-parameterizes the example (same skeleton, new givens) and prints only the stem plus the upside-down answer, so checking requires attempting first.
- **`\why{...}`** (optional, at most one per example) prints a one-line self-explanation aside after a step — *the reason the move is legal*, not a restatement of it. A printed model of self-explanation teaches the habit the research prompts train. Keep it conceptual and number-free; the prose checker reads any numbers in it against the entry.
- **`\fadestep{...}`** (optional, inside a try-it) turns it into a completion problem: the setup shown ("Started for you: …"), the finish left to the student. Backwards-fading measurably beats the straight example-to-problem jump **on multi-step skills** — use it when the example needed 3+ computational steps, skip it on one-move skills where the bare try-it is the right next step. End the box with the check answer right-aligned: `\hfill\rotatebox{180}{\footnotesize check: $\ans{...}$}`.
- **Dual coding:** when a skill is spatial (trig ratios, transformations, area models, number lines), put a small **value-free** diagram in its formulabox next to the rule, built from the shipped figure macros or house styles — a rule the student can *see* is retained better than the same rule in symbols alone. Value-free, so the figure-scope rules never apply; budget for it via "pages" below if two diagrams push past the default.
- Boxes carry printed title tabs (RULE / EXAMPLE / TRY IT / WATCH OUT) so a student scanning for the formula finds it without reading — do not add your own headings inside boxes.

It contains:
**Length.** The default budget is **2 pages**, and the discipline of the small page is most of what makes a reference card one. Declare a top-level `"pages"` (integer 1–6) in the verify_ss JSON only when (a) diagrams the skills genuinely need — a unit circle, a transformation grid, labelled solids — do not fit the default, or (b) the user asked for a longer guide. `verify.py` validates the field; `build.sh` reads it for the compile-ss page cap. The five-full-sections ceiling below scales with it: about 2–3 full sections per page.

**Study guide without a worksheet.** When the user wants ONLY a study guide ("make Leo a reference sheet for the unit circle"), write just `ss_TOPIC_DATE.tex` + `verify_ss_TOPIC_DATE.json` and build with `bash scripts/build.sh /tmp/verify_ss_TOPIC_DATE.json --study-guide-only`. Every guide-integrity gate still runs (verify, template, compile with page cap, answer binding, structure, prose, overprint); only the sheet-relative gates (skill coverage, facets) skip, because there is no sheet. The guide's worked examples are still fully machine-verified.

- One section per distinct skill tested, matching the worksheet's `"skill"` names. **The slug belongs in the JSON, not in the heading** — `\skillheading` is gated at 57 characters (the budget includes the `"Skill N --- "` prefix, which eats about 12), and the coverage gate reads the JSON tag, never the printed title. Six eval-run agents overflowed this heading by echoing the slug in parentheses to make the tagging visible to a reader; it does not need to be visible there. Sections are — `build.sh`'s `coverage-ss` gate fails the build if any worksheet skill lacks a tagged study-guide entry. **Five full sections is the hard ceiling** for the 2-page cap (a full section costs ~234pt against a 1382pt two-page budget); aim for 3–4. When over budget, drop the watch-out box first, then merge two thin skills, then shorten worked examples — never drop the try-it. Add no `\vspace` between boxes; they carry their own spacing. See `references/latex-templates.md` → "Page budget"
- A **formula/rule box** (blue) per skill — the key facts and formulas
- A **mini worked example** (green) per skill — a `\step` strategy line naming why this tool applies, then the computation — fewer steps than worksheet problems, never a bare answer chain (see the exemplars in `references/latex-templates.md`)
- A **try-it** (violet) per worked example — a re-parameterization of that section's example (same skeleton, new givens), printing ONLY the stem plus the verified answer upside down INSIDE the box via `\rotatebox{180}{\footnotesize check: $\ans{...}$}` — no worked steps; solving it is the student's job. Formula-only sections (no example) are legal and need no try-it
- An optional **watch-out box** (orange) — common mistakes worth flagging
- Optional **key vocabulary** section at the bottom

See `references/latex-templates.md` → "Skills Summary / Study Guide Template" for the full shell and box macros.

**Verify the study guide too.** Its worked mini-examples are math the student learns from first, so they must not be exempt from the gate (audit 3c). Write a second verification file `/tmp/verify_ss_TOPIC_DATE.json` — one entry per worked example's computation AND one per try-it. Entries MUST be listed in document order (example, try-it, example, try-it, …) because binding is positional; tag each try-it entry `"role": "tryit"` and each entry with the `"skill"` it demonstrates. The build driver (step 5) verifies it and binds its printed answers automatically; a missing `ss_` document or `verify_ss_` JSON is a **build failure**, not a skip. Formula boxes (no computed answer) need no entry; every *worked example or try-it with a printed result* does. `check_answer_key.py` segments ss documents **by box** (`examplebox`/`tryitbox`) — keep one worked example or try-it per box, and one **id** per box — so box count = `problem_count` = the number of distinct ids. A box whose example needs more than one check (a distance AND the perimeter built from it) may carry several entries under that one id; what must not happen is two boxes sharing an id, or one box holding two, and print each result with `\ans{...}` (defined in the study-guide shell); a result set in bare `\boldsymbol` is invisible to the gate. A try-it may be type `manual` only when its paired example is also `manual` (exit-2 visibility, never silent). The structure gate (`scripts/checks/check_study_guide.py`) additionally requires ≥2 `\step` lines and a boxed final answer per examplebox — the first step is the strategy sentence, capped at ONE sentence (page 1 fills fast and the guide is hard-capped at 2 pages — enforced mechanically: the `compile-ss` gate reads the page count from the engine's log and fails a 3-page guide).

**Subtitle from facets:** when `"facets"` is declared, write a top-level `"subtitle"` in the verify JSON composed from that facet list *first*, then copy it verbatim into the worksheet's title block. The facet-coverage gate (step 5) binds the two, so the title can never promise a skill the sheet doesn't plan.

See `references/latex-templates.md` for document templates, coordinate planes, tables, geometric figures, and answer key patterns.

**Use the figure HOUSE STYLES before raw TikZ** — `references/latex-templates.md` → "Figure house style". The preamble ships graph styles (`wsgrid`, `wsgridwide`, `wsgridq1`, `wstrig`, `wsfuntall` + `wscurve`/`wsasym`/`wsopen`/`wsclosed`), chart styles (`wsbar`, `wshist`, `wsboxplot`, `wsboxplot pair`, `\wsdotplot`, `wsstemleaf`, `\wspictorow`) and `figure-macros.tex` ships geometry marks (`\congtick`, `\parallelmark`), a transformation grid (`\gridtrifig`), fixed-size solids (`\cylfig` … `\cylnetfig`) and the K-4 model set (`\tenframefig`, `\arrayfig`, `\basetenfig`, `\clockfig`, `\fraclinefig`, `\tapefig`, `\coinrowfig`, …). Four rendered-page reviews found the raw-TikZ route producing grids students cannot plot on, self-overprinting solids, color-only semantics that die in photocopy, and hand-rolled K-4 models with broken proportions — the styles encode the fixes once. Two standing rules: figures are SPACE-GENEROUS (budget `workspace_cm` for the style's natural size rather than scaling it down), and every "sketch/plot" problem's answer key prints the model graph on the same grid style the worksheet used.

**Draw diagrams in TikZ, not as imported images.** TikZ uses the document's own fonts and line weights, so a figure's labels match the surrounding mathematics exactly — an imported bitmap or an externally-drawn PDF does not, and cannot be regenerated when the numbers change. The shipped preamble loads TikZ, pgfplots and the libraries below for every document, so nothing needs requesting:

| Library | Use it for | Template |
|---|---|---|
| `arrows.meta` | number lines, vectors, mapping diagrams — `-{Stealth}` reads as an arrow at small sizes where a bare `->` reads as a tick | "Number line" |
| `patterns` | shaded fraction / percent / probability area models; hatching survives photocopying where a light grey fill does not | "Shaded area model" |
| `decorations.pathreplacing` | braces on bar models and part-whole diagrams | "Brace annotating a part" |
| `pgfplots: statistics` | box plots | "Box plot" |
| `pgfplots: fillbetween` | area between curves | "Area between two curves" |
| `pgfplots: groupplots` | two displays with shared limits | "Two displays for a compare item" |
| `adjustbox` | scaling a figure that is genuinely too wide | "Fitting an oversized figure" |
| `positioning`, `intersections`, `shapes.geometric` | relative node placement, named-path constructions, sorting-diagram nodes | — |

**The binding rule applies to every one of them: a figure's numbers come from the same JSON the checker reads.** The sharpest trap is the box plot. Hand pgfplots raw data and it computes quartiles by an interpolating convention, while `verify.py`'s `stats` type uses school median-of-halves — on `[4, 6, 7, 9, 11, 12, 18]` verify says median 9, q1 6, q3 12 and pgfplots draws median 8 with a box from 5 to 11.5. The sheet would print a figure contradicting its own answer key, and no gate reads inside a plot. Declare the five-number summary as `stats` entries and pass those values with `boxplot prepared`.

`forest`, `tikz-cd`, `circuitikz`, `chemfig` and `quantikz` are deliberately NOT loaded — see the reasons in `templates/worksheet-preamble.tex`. Factor trees and probability trees, the one genuinely mathematical case, draw fine with TikZ's built-in `child` syntax at no extra load cost.

**Answer-key shell:** the `ak_` document starts exactly like the worksheet
(`\input{worksheet-preamble}`), then `\akheader{TOPIC}` + `\aktitleblock{...}`, and ONE
`\input{qa_TOPIC_DATE}` line directly under the title block — the build driver's
quick-answers gate regenerates that bank from the verify JSON every build and **fails a
key that hand-rolls its preamble or never `\input`s the bank** (both messages teach the
fix). `\akheader` switches `\ans{...}` to a compact same-line box, so end each worked
solution's last step with `\ans{x = 5.00}`; keep the display `\[ \boxed{...} \]` form
for long or multi-value answers. See `references/latex-templates.md` → "Answer Key
Patterns".

**Preamble — \input the shipped template, never retype it.** Start every document with:
```latex
\documentclass[12pt]{article}
\usepackage[margin=1in, top=0.75in, bottom=0.75in]{geometry}  % ss_: margin=0.85in, top/bottom 0.7in
\input{worksheet-preamble}
\input{figure-macros}    % when using the shipped figure macros (\rtfig, \trifig, \refrt)
```
`$SKILL_DIR/templates/worksheet-preamble.tex` carries the packages, `\problem`, `\fittedtitle`, the `\wsheader`/`\akheader`/`\ssheader` + title-block macros, and the study-guide box environments; `templates/figure-macros.tex` carries the figure macros. `compile.sh` (and therefore `build.sh`) stages both files beside your `.tex` automatically, so `/tmp` compiles just work — but only when you compile through the scripts, never by invoking the engine directly. Only `geometry` stays in the document (margins differ between worksheets and study guides). `build.sh` enforces this mechanically — the `template-ws`/`template-ak`/`template-ss` gates (`scripts/checks/check_template_use.py`) fail any document that hand-rolls its shell, `\input`s a non-shipped preamble file, or redefines a shipped macro/environment/color.

**Work space:** use `\problem{...}` without reserved space by default.
For an explicit writing-space request, declare `\worksheetlayout{spacious}`;
about 5cm per problem, 8cm for multi-step work or a user-specified amount is then
appropriate. Keep requested space inside the problem's unbreakable block. The
layout gate only enforces the 2.5cm writing-space floor in spacious mode.

**Page overrun: count problems per page BEFORE choosing a remedy.** `page_budget.py`
prints two NOTEs whose fixes point in opposite directions, and applying the wrong one
makes the sheet worse. `pdftotext` the failing PDF and look at what actually landed on
a page:
- **2 or more problems per page** — the blocks pack fine and the budget is simply
  under-measuring them (its stem charge is a flat 0.6cm). **Declare `workspace_cm`**
  covering the block's real height. That is the honest move: the declaration is a
  measurement, and it raises the ceiling without adding content.
- **1 problem per page** — the block is taller than half a page, so nothing can share
  with it and the rest of every page is stranded. **Shorten the block** — a smaller
  figure, or the work space *beside* the figure instead of under it. A larger
  `workspace_cm` here raises the ceiling without recovering one centimetre of the
  stranded space, and it is no longer a measurement of anything.

A side-by-side `minipage[t]` figure/question layout is the usual way to recover that
stranded whitespace, and it compresses no work space — but put `\vspace{0pt}` first in
BOTH columns, or a `tikzpicture`'s bottom-sitting baseline makes the columns stack and
doubles the block instead (the tell: shrinking the figure changes the page count by
exactly zero).

**Answer location (spacious worksheets):** `\problem` sheets emit the right-aligned
answer blank automatically whenever the workspace argument is positive — write nothing
extra. On spacious enumerate/`\item` sheets, end every item with `\ansline` (or an inline
`\ansblank` for drill formats: `$7 + 5 =$~\ansblank`). Mark `\noansline` only where the
worked product IS the answer — graph sketches, proofs, constructions (typically the
`manual`-type set). `scripts/checks/check_layout.py` enforces one answer-location macro per item;
answer keys and study guides are unaffected.

**Units are verified data, not decoration:** any problem whose final answer carries a
measurement unit declares `"answer_unit"` in its JSON entry (`"ft"`, `"m"`, `"cm^2"`,
`"square units"` — distinct from the deg/rad angle-mode field `"unit"`) and ends with
`\answerline{<unit>}` on the sheet (write exponents math-wrapped: `\answerline{cm$^2$}`;
`\answerline` replaces `\ansline` there and suppresses `\problem`'s automatic blank).
The key must print the same unit inside `\ans{}`/`\boxed{}` (`\text{ft}`).
Both directions are gated: `scripts/checks/check_answer_line.py` fails a declared unit with no
matching `\answerline` and an `\answerline` unit the JSON never declared;
`scripts/checks/check_answer_key.py` fails a key whose box omits the declared unit or prints a
unit the JSON never declared — a metres problem answered in feet no longer passes any
gate. Prefix currency symbols are out of scope: write "in dollars" in the stem.

**Figure scope**: a figure carrying numbers belongs to one problem, but on the page it
merely sits *near* several. If problem 6 shows a triangle labelled `a=6, b=8` and
problems 7-8 show none, a student reading 7 will apply the nearest figure to it — the
figure is correct and the worksheet is still wrong. So within one problem list, **no
problem may be left with no figure at all while another problem's figure carries
values**. A problem holding its own *value-free* figure — a blank coordinate grid to
plot on, an unlabelled diagram to mark up — is fine, and mixes freely with graphed
problems beside it: the picture inside its block is visibly the one it means, and a
grid's axis numbers are its own scale, not another problem's data.
Shared labelling conventions go in a single value-free reference figure placed with the
directions, captioned so it cannot be mistaken for a problem's givens, e.g. "How every
triangle here is labelled. No values shown: use the numbers given in each problem."
Use the shipped `\refrt` macro for it. Its convention is the renderer's: sides `a/b/c`
opposite vertices `A/B/C`, right angle at `C`, hypotenuse `c` — the reference figure and
the renderer-built `\probfig` figures share one page. Keep the macro and
`render_figures.py` consistent about the right-angle vertex.
`scripts/checks/check_layout.py` enforces the scope rule.

**A data display several problems read from goes ABOVE the first `\problem`.**
The scope rule is all-or-nothing per problem list, and a data display IS its
values, so the rule's usual remedy — make the figure value-free — cannot apply
to it. A bar chart set inside problem 3 of a mixed graph/table/algebra sheet is
a valued figure beside figureless problems, and `check_layout` fails the sheet;
an author who does not know the pattern deletes the chart or fights the gate.
Problem regions run from one `\problem` to the next, so a display placed before
the first one belongs to no region and is scoped to none of them. Caption it
with the problems that use it — "Problems 4-7 refer to this chart" — so a
student is never left guessing which givens are theirs. Five eval batches
arrived at this independently; it is the standard answer for mixed-representation
sheets.

**Know what that costs, because nothing else will tell you.** A display above
problem 1 is outside every problem region, so `figure_label_numbers` never reads
its printed values against the JSON: a drifted axis tick or a mis-plotted point
on a SHARED graph is invisible to the entire gate chain, on the one figure the
most problems depend on. It is also invisible to the page budget — charge its
height to the problems that consume it via `workspace_cm`. So: source the
plotted values from the same `data` array the `read_data` checks use (never
retype them), and read the rendered page yourself before shipping. Hoisting a
figure out of a problem to quiet the scope check, when only that problem uses
it, trades a gate that works for one that cannot run — keep a single problem's
figure inside its own block.

**Triangle figures MUST come from the renderer, never hand-drawn TikZ with values.**
Step 4b generates `\probfig{N}` macros from the verify JSON — every `triangle` problem
automatically, plus `approx` and `eval` problems that declare a `"figure"` object. A
write-the-ratio problem ("write $\tan A$ as a fraction") is verified as `eval` and is
renderer-figured like any other right triangle — the renderer covers it, so the
hand-macro escape hatch never applies to it. Reference the macros
in the worksheet instead of writing TikZ: hand-computed figure coordinates are exactly
the retyping drift the JSON-first pipeline exists to prevent (the reference SSA swing
figure itself shipped with wrong hand-computed constants until the renderer replaced
them). Leave a `\probfig{N}` placeholder while writing the `.tex`; the macro exists
once step 4b's figs file is `\input`. Hand-built TikZ per `references/latex-templates.md`
remains the path only for figure kinds the renderer doesn't cover — circles, sectors,
solids, transversals, coordinate grids. `\includegraphics` in worksheet problems is
rejected as unverifiable (`check_prose_consistency.py` exits 2 — no checker can bind an
external image's values to the JSON): figures come from `scripts/render_figures.py` or
the TikZ templates, never from image files.

### 4. Write and run the verification file

Before compiling, write `/tmp/verify_TOPIC_DATE.json` — a structured data file describing each problem and its expected answer. The bundled `scripts/verify.py` evaluates this using SymPy. No generated code is ever executed. The build driver (step 5) runs it first and fail-fast; to iterate on verification alone, see "Debugging individual gates" below.

**Field reference that cannot go stale:** `python3 "$SKILL_DIR/scripts/verify.py" --schema` prints every type's required/optional fields, the allowed functions/constants/variables, and one working example per type, generated live from the enforced schema (`--schema json` for machine-readable output).

**JSON format** — always set `problem_count` to the number of problems on the worksheet. Two gates enforce coverage, and they are not the same gate:

- `verify.py` hard-fails unless every problem id 1..N has at least one check. This counts **problems**.
- `scripts/checks/check_answer_slots.py` hard-fails unless every id has **one entry per response the problem asks for** — every printed `\ansline`/`\ansblank`/`\answerline`, and every lettered `(a)`/`(b)`/`(c)` sub-part in the stem. This counts **answers**.

**The answer key reads: header, Quick Answers, worked solutions — then a final page of its own.** The generated bank emits the verification and curriculum summaries (and the common-wrong-answers table) via `\AtEndDocument`, so they claim the LAST page automatically; the `ak_` author writes nothing extra and the one-`\input` contract is unchanged. Answer keys also breathe by design: `\akheader` switches on rubber inter-problem space, `\raggedbottom`, and a small stretchable `\parskip` — the key's reader is a grader scanning solutions, and a page set solid reads as a wall. The worksheet keeps its measured fixed layout (work space there is a promise to the student).

**The answer key says what it can and cannot vouch for.** Its Quick Answers bank has three states, and a "What is verified" note names the problems in each: a plain value is machine-checked; `$\spadesuit$` (a spade — chosen because no maths in these documents uses the glyph, where the old `---` sat one glyph from a minus sign) marks an answer only the instructor can judge, with the worked solution stating what a correct response must contain; and **`[unchecked]`** marks a problem printing more responses than the verification covers, where at least one printed answer carries no guarantee. The note is silent on a fully verified sheet — a legend explaining marks that never appear is the noise that makes real warnings invisible. Aim for a key with no `[unchecked]` marks; when one is unavoidable, the instructor at least knows where to look instead of trusting a complete-looking column.

When a problem carries more than one entry, give each a `"slot"` — the name of the response it covers (`"AC"`, `"the ones digit"`, `"(b)"`). No check reads it; the Quick Answers bank prints it, so a grader can tell which value answers which question. Without it the bank joins values in array order, and a sheet asking for "AC and BD" printed `2. 2.83, 8.49` with BD first.

**A slot label is a promise about FORM, and `scripts/checks/check_answer_slots.py` holds you to the narrow cases it can read.** The run-2 judge rejected a sheet whose bank row read `the equation = 6` (the check verified the slope; the student writes `y = 6x`) and another whose `word form` / `colon form` / `fraction form` slots all carried the identical value `3/5`. Three hard-fail rules, each measured 100%-precise on the 2953-slotted-entry corpus: a slot whose head noun is *equation* must have `=` in its value — key the equation itself with `equiv` (`expr "y - 6*x"`, `expected "y = 6*x"`), or rename the slot to what the check verifies ("of the equation", "equation value at 4" and similar part-namings are exempt); a *colon form* or *word form* slot names a transcription the expression grammar cannot hold (`3:5`, words) — declare that response `manual` with the printed form in the desc, and let the fraction-form entry carry the machine check.

The second gate exists because the first was mistaken for it. "At least one check per problem" was read as "a partially-verified answer key can never slip through", and those are different promises: a problem printing three blanks satisfies the per-id rule with one entry. In a 300-case review, **172 shipped a printed answer that nothing verified** — often the very skill the problem was tagged with. If a problem asks the student to write the number word *and* the ones digit, that is two entries. If a blank is working space rather than an answer, print it with `\scratchblank` and it is not counted. Use it for a **scaffolding blank that transcribes a given** — "$y$ of $C$ ___ $-$ $y$ of $B$ ___" where both coordinates are printed in the stem — and for **a value the problem already asked for elsewhere**. A check on either is vacuous, and dressing one up as a verified answer is the same overclaim the gate exists to stop:
```json
{
  "topic": "derivatives and trig",
  "problem_count": 17,
  "problems": [
    {"id": 1, "type": "solve",  "expr": "x**2 - 5*x + 6",      "expected": [2, 3]},
    {"id": 2, "type": "factor", "expr": "x**2 - 7*x + 12",     "expected": "(x-3)*(x-4)"},
    {"id": 3, "type": "eval",   "expr": "(x-1)*(x+2)", "at": {"x": 0}, "expected": -2},
    {"id": 4, "type": "zeros",  "expr": "x*(x-3)**2",           "expected": [0, 3]},
    {"id": 5, "type": "expand", "expr": "(x+2)**2",             "expected": "x**2 + 4*x + 4"},
    {"id": 6, "type": "diff",   "expr": "x**3 - 4*x",           "expected": "3*x**2 - 4"},
    {"id": 7, "type": "integrate", "expr": "6*x**2",            "expected": "2*x**3"},
    {"id": 8, "type": "limit",  "expr": "sin(x)/x", "to": 0,    "expected": 1},
    {"id": 9, "type": "equiv",  "expr": "sin(2*x)",             "expected": "2*sin(x)*cos(x)"},
    {"id": 10, "type": "solve_interval", "expr": "2*sin(t) - 1", "var": "t",
               "interval": [0, 360], "unit": "deg", "expected": [30, 150]},
    {"id": 11, "type": "approx", "expr": "9*tan(35*pi/180)", "expected": 6.30, "tol": 0.01},
    {"id": 12, "type": "distance", "points": [[1, 2], [4, 6]], "expected": 5},
    {"id": 13, "type": "midpoint", "points": [[2, -3], [8, 7]], "expected": [5, 2]},
    {"id": 14, "type": "slope", "points": [[2, 1], [2, 9]], "expected": "undefined"},
    {"id": 15, "type": "polygon_area", "points": [[0, 0], [5, 0], [6, 4], [1, 3]], "expected": 17},
    {"id": 16, "type": "triangle", "given": {"a": 7, "b": 11, "C": 34},
               "solve_for": "c", "expected": 6.51},
    {"id": 17, "type": "manual", "desc": "Graph sketch — verify visually"}
  ]
}
```

**Type reference:**

| Type | Verifiable? | What it checks |
|---|---|---|
| `solve` | ✅ | Roots of expr=0 match expected list (optional `var`, default `x`). An equation with no solution is keyed `"no solution"` and an identity `"all real numbers"` — both are decided from the expression, not from an empty root list, so keying an identity `[]` fails. Free symbols beyond `var` make it a literal equation: it solves for `var` in terms of the others |
| `zeros` | ✅ | Zeros of expr match expected list (duplicates collapse) |
| `factor` | ✅ | Factored form is equivalent to expr |
| `expand` | ✅ | Expanded form is equivalent to expr |
| `eval` | ✅ | expr evaluated at given values matches expected |
| `diff` | ✅ | Derivative of expr matches expected (optional `order`) |
| `integrate` | ✅ | Expected antiderivative differentiates back to expr — omit the `+C` |
| `limit` | ✅ | Limit of expr as var → `to`; optional `dir`: `"+"`, `"-"`, `"+-"` (default) |
| `equiv` | ✅ | expr and expected are the same function (trig identities, simplification). **The only type that accepts an equation:** where the student's answer *is* an equation, write it as one — `"expected": "(x-3)**2 + (y+5)**2 = 25"` — and the check compares `lhs - rhs` exactly as before. Do this whenever the ask is "write it in ⟨form⟩" for a locus (centre-radius, standard form of a conic); leave it an expression when the answer is one (vertex form, a simplified expression, an identity's other side) |
| `solve_interval` | ✅ | Roots of expr=0 on `[a, b)`; `"unit": "deg"` for degree-mode trig equations. Write a radian endpoint exactly — `"2*pi"`, not `6.28318…`: the interval is half-open, so a decimal endpoint decides a root sitting *on* the boundary by rounding. A decimal within 1e-3 of a π multiple is read as that multiple and the detail line says so |
| `approx` | ✅ | Numeric expr recomputed exactly, compared within `tol` (default: scale-aware — accepts what rounds to the written precision) — for rounded answers |
| `distance` | ✅ | Distance between two `points`; exact, or within `tol` if given |
| `midpoint` | ✅ | Midpoint of two `points`; expected is an `[x, y]` pair |
| `slope` | ✅ | Slope through two `points`; expected value or `"undefined"` for vertical |
| `polygon_area` | ✅ | Shoelace area of the ordered `points` (3+) — triangles, quads, composite grid figures |
| `triangle` | ✅ | Solves the triangle from 3 `given` values (sides `a/b/c`, angles `A/B/C`), checks `solve_for` within `tol`; degrees by default; accepts either triangle in the ambiguous SSA case |
| `system` | ✅ | `equations` (each `=0`), `vars`, `expected` `{var: value}` (all vars) or a list of solution dicts. Each listed solution must satisfy every equation; PASS only when the count matches SymPy's full solution set. A dependent system is keyed `"expected": "infinitely many"` and an inconsistent one `[]` — both PASS on the right system and FAIL by name on the wrong one, so neither is a MANUAL any more |
| `series` | ✅ | `summation(term, var, from..to)` vs `expected`; finite or infinite (`"to": "oo"`), incl. geometric and Taylor (`factorial` allowed) |
| `inequality` | ✅ | Solution set of `expr relation 0` (`relation`: `<`, `<=`, `>`, `>=`) vs an interval spec `[lo, hi, openness]` (`openness`: `open`/`closed`/`loopen`/`hiopen`; `lo`/`hi` may be `"oo"`/`"-oo"`) |
| `stats` | ✅ | `measure` of a `data` list: `mean`/`median`/`mode`/`range`/`sum`/`variance`/`stdev`/`q1`/`q3`/`iqr` (school median-of-halves quartiles; non-unique mode → manual) |
| `probability` | ✅ | `favorable`/`total` as an exact fraction |
| `read_data` | ✅ | Read/compute from a chart or table whose `data` is in the JSON. Object data → `query` `value`/`total`/`max_value`/`min_value`/`max_key`/`min_key`/`difference` (with `key`); list data → `total`/`count`/`max_value`/`min_value`. `difference` takes `key` as a **two-element list in subtraction order** — `["Fri","Thu"]` means Fri − Thu. The SAME `data` feeds the pgfplots chart, so figure and check share one source |
| `definite_integral` | ✅ | ∫ from `from` to `to` of `expr`. Uses SymPy's exact integral when available, else convergence-checked mpmath quadrature; returns MANUAL if numerics don't converge rather than trust a wrong value. A divergent integral is an answer, keyed `"oo"` (or `"-oo"`); an `Abs`/`sign` integrand is split at its corners instead of being handed whole to a quadrature that cannot see them |
| `estimate` | ✅ | Rounds each numeric **operand** in `expr` (half-up) to `place` (`ten`/`hundred`/`thousand`/`whole`/`tenth`/`hundredth`), then evaluates — front-end "estimate by rounding". `probability` favorable/total is range-validated (0 ≤ fav ≤ total) |
| `compare` | ✅ | Order `values` (`order`: `asc`/`desc`) or state a `relation` (`<`/`>`/`=`) between the first two |
| `manual` | 👁 | Flagged for human review — never fails automatically |

**Reframe "understanding" topics as checkable tasks** (see `references/problem-library.md` → "Reframing \"understanding\" topics as checkable tasks"): missing-number → `solve`, fact-family → `eval`, estimation → `estimate`, ordering → `compare`.

**A check must exercise the work the problem asks for.** No gate can enforce this — it is a relationship between the printed stem and the JSON that no static rule reads reliably, so it is on you. Two shipped failures show the shape:

- A problem gives `f(x) = (x²−5x−14)/(x−7)` for `x ≠ 7` and asks for the `c` that makes `f` continuous at 7. Its check was `solve(c − 9, c) == [9]` — it asserts that 9 solves `c − 9 = 0` and never touches the function. Green gate, response claiming "machine-verified with SymPy", nothing verified. Check the limit.
- A problem gives midpoint `M(3,5)` and endpoint `A(−1,2)` and asks for `B`. Its check was `midpoint([[−1,2],[7,8]]) == [3,5]` — the answer fed in as an input, a given verified as the output. It cannot fail, and the answer bank printed `6. 3, 5`, so a student with the correct `(7,8)` marks themselves wrong. **For an inverse item, compute the asked value.**

`scripts/checks/check_answer_slots.py` prints an advisory when a check's expected values are all already in the stem, but it is deliberately advisory: measured over 300 cases it is right about one time in seven.

**Error-analysis ("find and fix the mistake") is TWO responses, not one.** The *correction* is a value, so it takes an ordinary type — the planted wrong result is checkably wrong and the corrected one checkably right. The *diagnosis* ("name the error", "say what rule it breaks", "explain what he did wrong") is prose, so it takes a `manual` entry alongside. Declare both. Routing the whole item through an ordinary type leaves the diagnosis unchecked and, worse, makes the sheet claim it is fully machine-verified: in the 300-case review **202 cases** did exactly that, and many then stated "Nothing is flagged for manual review" in the delivered response, two paragraphs from an answer key printing a grading rubric for the explanation they had just called machine-checked. Deciding per *response* rather than per *problem* is what resolves this — the two rules below are not in tension once you stop asking which one the problem belongs to.

**Data charts:** render bar/line/pictogram charts with pgfplots (see `references/latex-templates.md`), sourcing the plotted values from the same `data` array the `read_data` check uses — never retype them. `solve_interval` on a transcendental equation now confirms *completeness* by mpmath root-enumeration (PASS when the key's roots match all numerically-found roots; MANUAL if counts differ)."

**Complex numbers:** `I` is available in expressions, so `eval` handles complex arithmetic (e.g. `(3+2*I)*(1-4*I)` expected `"11 - 10*I"`). For `solve`/`zeros`, non-real roots are no longer dropped silently — set `"domain": "complex"` to require the full root set (e.g. `x**4-1` → `[1, -1, "I", "-I"]`) or `"domain": "real"` to restrict to real roots.

**An INVERSE solved with `solve` usually needs `"domain": "complex"`, on a problem with nothing complex in it.** `"real"` (the default) keeps only the roots SymPy can prove real, and a root written in the *other* variable often cannot be proved real — `sqrt(y-3)` is real only where `y >= 3`, which the solver does not know. The check then reports an empty root list against your answer:
```
❌ solve(x**2 + 3 - y, domain=real) → [] (expected [sqrt(y - 3), -sqrt(y - 3)])
```
That reads as "your expected answer is wrong", and it is not — the same entry with `"domain": "complex"` passes unchanged. Confirmed on `x**2+3-y`, `exp(x)-y` and `x**3-y`. Restrict the domain in the PRINTED problem ("for $y \ge 3$"); do not let the field name talk you out of a correct key.

For geometry, **state the givens and let the script compute**: pass raw coordinates to `distance`/`midpoint`/`slope`/`polygon_area` and raw triangle data to `triangle` rather than doing the formula yourself in `expr`. Angle convention: side `a` is opposite angle `A` (matches the figure templates).

Use `manual` for: graph sketches, sign charts, word problem setups, two-column proofs, constructions, Riemann sum tables, series convergence arguments, drawn or marked representations (circle it, shade it, plot it), a named misconception, and any explanation/reasoning answer — **per response**, so a problem whose (a) is a number and whose (b) is "explain why" gets one ordinary entry and one `manual` entry, not a choice between them.

Two lints in `scripts/checks/check_answer_slots.py` enforce this per response, both measured on the 300-case corpus before shipping:

- **Open-ask lint** (hard fail): a stem containing an open ask — explain, describe, justify, say why/whether/which, name the error, sketch, shade, circle the, prove, construct — must have a `manual` entry on that id. 471 problems in 184 of 300 reviewed cases violated this. Do **not** delete or weaken the ask to quiet the gate: the written reasoning is the pedagogy, and a sheet stripped of its explain-items to build green is a worse sheet. "Sketch it if it helps" is scaffolding and is exempt.
- **Stale-rubric lint** (hard fail): a `manual` desc naming a person or thing that appears nowhere in its problem fails — that is a rubric left over from an earlier draft, and it grades the wrong problem while every other gate stays green. Fires on exactly 1 of the corpus's 299 manual entries: the real defect.

A `manual` entry's `desc` is the rubric a human grader actually reads, so it must describe **the problem as printed**. Nothing binds it automatically: one reviewed case shipped a `desc` grading a scale-spacing argument about a student named "Priya" who appears nowhere in the worksheet — a rubric left over from an earlier draft, green through every gate. Re-read the `desc` against the stem before shipping.

**Optional review aid for `manual` content:** proofs and explanations can't be CAS-verified, but an independent LLM-judge pass can flag likely errors before a human reviews them. See `references/manual-review-aid.md`. This is a review aid, NOT a gate — a `manual` problem stays `manual`; never mark it verified on a judge's say-so.

**Expression syntax** — enforced by a strict allowlist in `verify.py`; anything outside it is rejected as a failure, never executed:
- Explicit operators only: `3*x` (not `3x`), `x**2` or `x^2` for powers
- Functions: `sin cos tan asin acos atan sec csc cot sinh cosh tanh log ln exp sqrt Abs floor ceiling`
- Constants: `pi`, `E` (Euler's number), `oo` (infinity)
- Variables: `x y z t u v w a b c h k m n r s theta phi` (pick from these when writing problems)

**Strict schema:** an unknown `type`, a misspelled field, or a missing required field is a hard failure (exit 1) — never a silent skip. If you need an unverifiable problem, declare it `manual` explicitly.

**Explicit `tol` is capped.** A `tol` wider than max(1% of |expected|, half a unit in the expected value's last written place) is rejected — an unbounded tolerance is a one-field bypass of the whole gate. For genuine estimation problems, add `"tol_reason": "<why>"` to acknowledge the widened tolerance: the run then passes with exit 2 and a visible `⚠` tally, never silently.

**So do not transcribe "round to two decimals" as `"tol": 0.01` — OMIT `tol` instead.** Run the cap on a small answer: with `expected: 0.34` the ceiling is max(0.0034, 0.005) = 0.005, and `"tol": 0.01` is rejected outright. The rule falls out of the arithmetic: **`"tol": 0.01` is illegal whenever |expected| < 1**, so the reflexive transcription passes on `6.30` and fails on `0.34` — the same sheet, two decimals both times. Writing no `tol` at all is not a weaker check but the RIGHT one: the scale-aware default already accepts exactly what rounds to the precision you wrote (`0.005` here), which is what "round to two decimals" means. Reach for an explicit `tol` only when you want something *other* than the written precision, and for a widened one write the `tol_reason` too.

**If verification fails (exit 1):** fix the LaTeX answer key and re-run. Do not compile until the answer key is correct.

**Trust boundary of `approx`:** it confirms the *arithmetic of the formula you wrote* matches `expected` — it cannot confirm the formula is the right one for the stated problem. Keep the `approx` `expr` a faithful transcription of the problem's givens, and rely on the prose/figure/answer-key checkers below to bind the story to the math.

**How values are compared — exact where both sides are exact, scale-aware as soon as a decimal appears.** If your `expr` or your `expected` contains a decimal literal, the comparison is made at the precision the expected value is *written* to (as `approx` has always done), not exactly. This is not a loosening you have to ask for and it is not a bypass: two exact values (integers, `Rational`, `sqrt(2)`, `pi/3`) are still compared exactly, and a genuinely wrong answer still fails at any scale.

State it because the alternative was silently corrupting problem design. Exact comparison on decimal arithmetic fails for reasons that have nothing to do with the mathematics — `9.4 - 0.4x` at `x = 20` is `1.4`, but binary floating point makes it `1.40000000000000` against a JSON `1.4` that parsed to `Rational(7,5)`, and `1.2*6` fails while `1.2*10` passes on luck alone. In the 300-case review **five separate authors changed correct mathematics to get green**: `9.4−0.4x` became `9.5−0.5x`, the physical constant `4.9t²` became `5t²`, `1.2` became `1.25`. Write the numbers the problem actually calls for. When a decimal comparison does fail, the detail line says the comparison was scale-aware, so the failure points at the answer rather than at the tool.

Two things this does **not** cover. A root *list* gets no such tolerance — `x**2 - 2` keyed `[1.41, -1.41]` still fails, because a set has no single written precision and that is an author rounding an irrational, not a representation artefact; key it `["sqrt(2)", "-sqrt(2)"]`. And an interval endpoint is not a value being compared but a boundary deciding membership — see `solve_interval` above and write it exactly.

**Misconception traps (`"traps"`, universal):** declare the result a known wrong method yields:
```json
{"id": 11, "type": "approx", "expr": "9*sin(35*pi/180)", "expected": 5.16,
 "traps": [{"desc": "used cos instead of sin", "expr": "9*cos(35*pi/180)", "value": 7.37}]}
```
Verification computes each trap `expr` and **fails unless the problem's own comparison rejects it** — a trap the check would accept means the problem cannot distinguish the error it targets: change the givens. The optional `value` (the wrong number printed in an error-analysis stem) must round-match its own `expr`, so the planted number is derived, never hand-typed; it then counts as a JSON given for the prose checker. The `desc`↔`expr` correspondence is yours to keep faithful — the same trust boundary as `approx` above.

There are **three shapes**, one per kind of answer, and `--schema` prints all three with the field names:

| Answer shape | Types | Trap fields |
|---|---|---|
| Scalar | `approx eval triangle distance slope polygon_area stats probability limit series definite_integral estimate read_data` | `"expr"` a **string**; optional `"value"` a JSON **number**, or a **string** where a number cannot hold the value (`"3 - 4*I"`, `"sqrt(2)/2"`) |
| Solution set | `solve zeros solve_interval` | `"exprs"` a **list of strings**, one per root the wrong method yields — `["5", "-2"]`, not `[5, -2]`; optional `"value"` the same set as printed, also a **list** |
| Symbolic rewrite | `equiv expand factor` | `"exprs"` a **list of strings** holding the wrong *rewritten form* — `["x**12"]` where the answer is `"x**7"`; optional `"value"` a **list** |

A solution-set trap is distinguishable when its set differs from `expected`, so a dropped root, an extraneous root and finding nothing at all are all declarable. A symbolic trap is distinguishable when its form is **not equivalent** to `expected` — a merely reordered factoring is rejected, because the check would accept it and so the problem cannot distinguish the error. The symbolic shape is what makes error analysis reachable on factoring, expansion and rewrite sheets at all: before it existed, every polynomial and factoring sheet in the run shipped with no "Common wrong answers" block, though `x⁴·x³ = x¹²` is as mechanical a misconception as any in trigonometry.

### 4b. Render figures from the verified JSON

Immediately after `run_verify.sh` succeeds, render the figures **from the same JSON**:

```bash
python3 "$SKILL_DIR/scripts/render_figures.py" /tmp/verify_TOPIC_DATE.json
# → /tmp/figs_TOPIC_DATE.tex, one \probfig{N} macro per figured problem
```

This is the `read_data` chart rule applied to geometry: the `given` dict the verifier
checks is what places every vertex, so the drawing cannot disagree with the answer key.
Figures are to scale (longest side ≈ 4.5cm), label **only** given values plus `?` on
`solve_for`, mark a given 90° angle with a square instead of an arc, and render the
ambiguous SSA case as the two-apex swing figure — both apexes computed, not retyped.

- Every `type: "triangle"` problem renders automatically from its own `given` dict.
- Right-triangle setups on `approx` and `eval` problems opt in with a `"figure"` object:
  `{"kind": "right_triangle", "given": {"b": 9, "A": 35}, "solve_for": "a", "unknown": "x"}`
  (two of `a/b/c/A/B`; the right angle at `C` is implied). Every figure value must
  appear among the numbers the problem's own check used — a literal in `expr`, or one
  of the `at` values on `eval` (the write-the-ratio shape: `"expr": "a/b"` with
  `"at": {"a": 8, "b": 15}`, figure `"given": {"a": 8, "b": 15}`, `"solve_for": "A"`,
  `"unknown": "A"` to mark the asked-about angle) — verification hard-fails otherwise,
  so the figure can only show numbers the arithmetic check actually used. Other problem
  types cannot carry a figure: they have no bindable single answer, and verification
  rejects them with the rewrite (verify as `approx`/`eval`, or drop the figure).
- In the worksheet: `\input{/tmp/figs_TOPIC_DATE.tex}` right after `\begin{document}`,
  then place `\probfig{N}` with problem N inside its minipage (figure-placement rules
  in `references/latex-templates.md`), keeping the work-space `\vspace` outside.
- An impossible figure refuses to render (exit 1) — fix the JSON, don't fight the tool.
- **Re-run this whenever the JSON changes.** A stale figs file is caught by
  `check_prose_consistency.py --figs` in step 4c.

`build.sh` (step 5) runs this render automatically when the JSON has figured problems and passes `--figs` to the checkers; run it by hand only when iterating on the `.tex` outside the driver.

### 4c. Render effort markers (quiz points / difficulty stars)

For timed quizzes (and practice sheets on request), render the per-problem effort
markers **from the same JSON** — generated, never hand-written:

```bash
python3 "$SKILL_DIR/scripts/render_meta.py" /tmp/verify_TOPIC_DATE.json
# → /tmp/meta_TOPIC_DATE.tex — \probpts{N} "(D pts)", \probmeta{N} stars, computed \totalpoints
```

`\input` the meta file right after `\begin{document}` and place the marker at the **end
of each stem, inside the problem's unbreakable block** — all problems or none, ONE mode
per document (points XOR stars). Never hand-type `\bigstar` or "(N pts)": the literal
forms are banned by `check_prose_consistency.py`, which also fails swapped, duplicated,
missing, or unresolved markers (`--meta`; a stale file after a JSON edit is caught the
same way — re-run this renderer). The renderer is the one place difficulty tags become
gating: every problem needs an integer difficulty 1–5 or it refuses to render, naming
the offending ids. `\totalpoints` is computed — never type the sum yourself.
`build.sh` runs this automatically when the sheet uses markers or every problem is
tagged, and passes `--meta` to the checker.

### 5. Run the gate chain and compile — one command

```bash
bash "$SKILL_DIR/scripts/build.sh" /tmp/verify_TOPIC_DATE.json
```

That single command replaces what used to be nine separate steps. It discovers `ws_`/`ak_`/`ss_TOPIC_DATE.tex` and `verify_ss_TOPIC_DATE.json` next to the JSON (student-name prefixes like `leo_ws_` and tier tokens `wsS_`/`wsC_`/`wsX_` included), then runs, fail-fast:

1. `run_verify.sh` on the worksheet JSON, then the study-guide JSON
2. `check_ss_coverage.py` — every worksheet `"skill"` has a tagged study-guide entry (zero/partial worksheet tagging fails)
3. `check_facet_coverage.py` — every worksheet facet must have a study-guide worked example tagged with it, and a declared `"subtitle"` must appear verbatim in the worksheet title block (no-op for sheets without a facet plan)
4. figure rendering (when shipped and the JSON has figure/triangle problems)
5. effort-marker rendering (`render_meta.py`, when the sheet uses `\probmeta`/`\probpts` or every problem is difficulty-tagged)
6. quick-answer bank regeneration (`render_quick_answers.py` on the answer key — every build, with the two preflight teaching failures)
7. `check_layout.py` on the worksheet (figure scope + work space + answer location)
8. `check_answer_line.py` on the worksheet (`answer_unit` ↔ `\answerline`)
9. `compile.sh` for all three documents (nothing compiles after a failed gate). Each compile enforces a **page budget** read from the engine's own `Output written ... (N pages` log line (`check_log.py --max-pages`). The study guide is hard-capped at **2 pages** — it is a reference card and that cap is fixed. The worksheet and answer-key caps are **computed per sheet** by `page_budget.py` from the problem set, the declared `workspace_cm`, the paper size and the type size read off the `.tex` (`--from-tex`, so large-print sheets get their extra pages without anyone remembering a flag): 50 graphing problems that each need a plane are allowed 26, not squeezed into a flat number. `8`/`6` appear in `build.sh` only as the fallback when `page_budget.py` itself cannot run. Over budget means the sheet overran *its own measured* budget — a layout accident, not a bigger worksheet. Fix it by cutting optional sections, declaring the real `workspace_cm`, or reducing the problem count; never by shrinking work space
10. `check_answer_key.py` binding `ak_` and `ss_` to their verified JSONs (values and units; for `ss_`: pairing — every examplebox is followed by its tryitbox — and role/position agreement, then per-box value binding)
11. `check_study_guide.py` — every worked example opens with a `\step` strategy line before any computation
12. `check_prose_consistency.py` on the worksheet AND the study guide (`--figs`/`--meta` passed automatically; examplebox prose givens are bound to the ss JSON; intermediate values that equal a subexpression of the entry's expr at printed precision are auto-matched; story numbers unused by the computation are expected flags)

It ends with a gate-summary table and ONE verdict line. Exit 0 = all green with three PDF paths printed; exit 1 = a gate failed (named — fix and re-run); exit 2 = green with manual-review items. **Missing `ak_`/`ss_` documents are failures, not skips** — the skill mandates three documents (`--worksheet-only` exists for the rare single-document request). Default output directory is `~/Documents/Worksheets/` (`--outdir` to override; see the Prerequisites note about headless environments).

Why the checkers exist (`build.sh` runs them for you):

- `check_answer_key.py` binds **per problem**: it segments the key (`\problem{...}`, one enumerate `\item` per problem, or one `examplebox` per worked example), requires the segment count to equal `problem_count`, and fails unless every verified value appears in **its own problem's** `\boxed{}`/`\ans{}` at the printed precision — `4.52` never satisfies a verified `4.51`, while `5`, `5.0` and `5.00` are the same answer. A swapped key, a wrong boxed value (even with the correct number in the worked steps beside it), or an unsegmentable key all hard-fail; answer-bank keys degrade to a loud whole-document `⚠` check. **Best practice:** render each boxed final answer *from* the JSON `expected` string rather than re-typing it, so the printed answer cannot drift from the verified value by construction.
- `check_prose_consistency.py` checks prose numbers and **figure-label numbers** against the JSON givens — a to-scale triangle labeled with a wrong side is flagged — and hard-stops on effort-marker faults (unresolved/swapped/missing `\probmeta`/`\probpts`, hand-typed stars or "(N pts)"). On the study guide it parses per box, so a worked example whose prose says `c = 12` while the verified expr computes with 10 is caught.
- `check_ss_coverage.py` requires a tagged study-guide entry for every worksheet `"skill"` — a guide that skips a tested skill fails before anything renders.
- `check_study_guide.py` enforces the worked-example shape: ≥2 `\step` lines per examplebox, the first prose-first (the strategy slot), and a boxed final answer for machine-verified examples. It guarantees the slot exists; the quality of the strategy sentence stays with you.
- `check_answer_line.py` binds declared `answer_unit`s to the sheet's `\answerline`s, both directions (step 3).
- `check_layout.py` enforces the figure-scope, work-space, and answer-location rules from step 3.
- `--figs` splices the rendered `\probfig{N}` bodies back into the text so `check_prose_consistency.py` and `check_layout.py` see the figures the student sees; without it, a sheet using `\probfig` exits 2 (an unchecked figure must never read as a pass). A **stale** figs file rendered before a JSON edit is caught the same way — re-run step 4b.
