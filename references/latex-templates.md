# LaTeX Templates Reference

## Paper size

US Letter is the default because that is what the schools this was built for
use. A4 and Legal are supported: pass the paper as a `documentclass` option and
give geometry margins in the matching unit.

```latex
\documentclass[12pt,a4paper]{article}
\usepackage[margin=2cm, top=1.9cm, bottom=1.9cm]{geometry}   % A4 worksheet
\usepackage[margin=1.8cm, top=1.8cm, bottom=1.8cm]{geometry} % A4 study guide
```

Most of the system is already paper-agnostic: the running head derives its title
box from `\headwidth`, and every box sizes from `\linewidth`. Two things do
depend on the paper and are handled explicitly:

- **Page budget.** `scripts/page_budget.py --paper a4` sizes the budget from the
  real page height. A4 is 1.8cm taller than Letter, worth roughly one page saved
  every fourteen on a long set.
- **Header title length.** A4 is 6mm narrower, so each head slot loses about
  four characters. `check_template_use.py` detects `a4paper` and scales the
  budget, so one rule stays honest on both rather than passing on Letter and
  overflowing on A4.

Do not mix units: an A4 document with `margin=1in` wastes 5mm of usable width
against the metric convention its readers expect.

## Accessibility

A student whose IEP or 504 plan entitles them to large-print materials could not
use this tool before these modes existed. Type size must come from the document
class (`article` offers only 10/11/12pt), so a large-print sheet opens with
`extarticle`; everything else adapts from the preamble.

```latex
\documentclass[17pt]{extarticle}     % or 14pt
\usepackage[margin=1in, top=0.75in, bottom=0.75in]{geometry}
\input{worksheet-preamble}
\accessiblemode{both}                % large | dyslexia | both
```

| Mode | Effect |
|---|---|
| `large` | 1.25 line spacing, answer blanks grow to 5cm at 0.8pt |
| `dyslexia` | sans-serif text **and math** (via `sfmath`), 1.5 line spacing, emphasis set bold instead of italic |
| `both` | all of the above |

The dyslexia settings follow the British Dyslexia Association style guide: sans
faces, generous leading, no italics. Math is switched to sans too, which matters
more here than in prose because a worksheet is mostly math.

The page budget needs no adjustment: it is computed from content, so larger type
simply produces more pages, which is the honest outcome. The header-title budget
DOES scale, and `check_template_use.py` scales with it (a 12pt title of 36
characters is 30 at 17pt) — a large-print sheet is exactly the one that must not
carry a shrunken header.

## Locale

Supporting A4 paper without the notation that goes with it is half a job: most
A4 countries write the decimal comma, so a student reading `1.5` parses that
period as a thousands separator. That is a correctness problem, not a cosmetic
one.

```latex
\mwslocale{eu}     % 1,5 and \times    (us is the default: 1.5 and \cdot)
```

The verify JSON stays canonical (period decimals, ASCII operators) so the
verifier and every gate keep one unambiguous number format. Only the printed form
is localised:

| Macro | `us` | `eu` |
|---|---|---|
| `\dec{3.75}` | 3.75 | 3,75 |
| `\mtimes` | `\cdot` | `\times` |

Use `\dec{}` for every decimal in problem text and answer keys when a locale is
set. A bare `3.75` in the source prints a period regardless, and is the one way
to defeat this.

## Design rules

These are the invariants the shipped preamble maintains. They exist because
each one was violated once and shipped a bad-looking sheet. Follow them when
adding anything to the design system.

1. **Every box that shares a line needs a width contract.** Two pieces of
   content on one line (a running head's left and right slots) must each have a
   reserved width and a defined overflow behaviour. Set at natural width they
   silently overprint each other, and a running head repeats that collision on
   every page.
2. **Overflow must degrade visibly, and degradation must be reported.**
   Shrink-to-fit keeps a long title on one line, but a shrunk title is worse
   output that the page never admits to. `check_template_use.py` fails a header
   title longer than its slot so the degradation is caught before compile, not
   discovered in print.
3. **The header's right slot is for information the reader acts on.** The
   Name/Date blanks earn their place. Labels that restate the document type
   ("For instructor/parent use" next to "Answer Key") do not: they cost the
   title the width it needed and add nothing.
4. **Never encode meaning in colour alone.** Worksheets get printed, usually in
   black and white. The four study-guide boxes carry the same colours they
   always did, and are additionally distinguished by frame shape: thick full
   frame (formula), thin full frame (example), left bar only (try-it), top and
   bottom rules only (watch-out). Measured, the four background fills span 5 of
   255 luminance in grayscale, so hue alone made them identical on a mono
   printer.
5. **Space that must survive a page break belongs inside a box.** LaTeX
   discards `\vspace` glue at a break, so workspace outside a minipage vanishes
   exactly when its problem lands at a page bottom. `\problem[5cm]{...}` puts it
   inside; `check_layout.py` fails the stranded form.
6. **A page budget is measured, not assumed.** The study guide's 2-page cap and
   its "2-5 sections" allowance were set independently and contradicted each
   other. See "Page budget" below for the measured cost of every component.


> **Source of truth:** the preamble, header/title macros, study-guide boxes,
> and figure macros ship as `\input`-able files in `templates/`
> (`worksheet-preamble.tex`, `figure-macros.tex`). This page documents how to
> USE them — never re-transcribe macro bodies from a markdown code block;
> transcription drift is exactly the error class the pipeline exists to
> catch. `compile.sh` stages the template files beside your `.tex`
> automatically, so `/tmp` compiles just work.

## Document Shell

```latex
\documentclass[12pt]{article}
\usepackage[margin=1in, top=0.75in, bottom=0.75in]{geometry}
\input{worksheet-preamble}
\input{figure-macros}       % when using the shipped figure macros
\wsheader{TOPIC Practice}

\begin{document}
\wstitleblock{TOPIC Practice Worksheet}{COURSE}{}  % empty 3rd arg = no printed date (reusable)

% [problems here]

\end{document}
```

**Leave the date empty by default.** The header already carries a fill-in
Name/Date blank, so a printed date only stamps the sheet and blocks reuse.
Pass a real date as the third argument only when the user explicitly wants one
dated (e.g. a specific quiz day). Same for `\aktitleblock`.

**Branding (school or teacher name).** To print a school or teacher name in the
footer of every generated document, set `\schoolname` once. Either edit the
default in `templates/worksheet-preamble.tex`:
```latex
\newcommand{\schoolname}{Riverside Middle School}
```
or override per document by placing this line after `\input{worksheet-preamble}`:
```latex
\renewcommand{\schoolname}{Riverside Middle School}
```
Empty by default, so nothing prints unless set. It appears bottom-left on the
worksheet, answer key, and study guide.

Macro reference (defined in `templates/worksheet-preamble.tex`):

| Macro | Purpose |
|---|---|
| `\problem{...}` | numbered problem stem (steps the `prob` counter). With a positive workspace argument (`\problem[5cm]{...}`) it also emits the right-aligned answer line automatically — construction, don't type it |
| `\ansline` | right-aligned "Answer: ____" blank — end every enumerate `\item` with it (`\problem` emits its own); `scripts/checks/check_layout.py` requires one answer-location macro per item |
| `\ansblank` | inline blank for drill formats: `$7 + 5 =$~\ansblank` |
| `\answerline{unit}` | answer blank + measurement unit (`\answerline{ft}`, `\answerline{cm$^2$}`) — the unit must match the problem's `"answer_unit"` in the verify JSON (`scripts/checks/check_answer_line.py`); suppresses `\problem`'s automatic line |
| `\noansline` | explicit opt-out for problems whose worked product IS the answer (sketch, proof, construction) — prints nothing |
| `\fittedtitle{...}` | shrink-to-fit title: `\LARGE` when it fits on one line, otherwise scaled to the text width — never enlarges, never wraps mid-phrase |
| `\wsheader{Short Title}` | worksheet running header: title left, Name/Date blanks right on page 1, "(continued)" on later pages. Keep the title SHORT (under ~28 chars) — `check_template_use.py` fails one that would be shrunk to fit |
| `\akheader{Topic}` | answer-key header ("Topic --- Answer Key"); the right slot is empty so the title gets the full head width |
| `\ssheader{Topic}` | study-guide header ("Skills Summary: Topic"); right slot empty, same reason as `\akheader` |
| `\wstitleblock{Title}{Course}{Date}` | worksheet title block + horizontal rule. **`Date` is optional** — pass an empty `{}` for an undated, reusable sheet (the default); an empty `Course` is dropped too |
| `\aktitleblock{Topic}{Course}{Date}` | topic on its own line, **"Answer Key" as a subtitle beneath it** — never appended to the big title, or a long topic wraps mid-phrase. `Date` optional, same as `\wstitleblock` |
| `\sstitleblock{Topic}` | study-guide title block |
| `formulabox` / `examplebox` / `tryitbox` / `watchoutbox` | study-guide box environments (blue formula / green worked example / violet try-it / orange watch-out) |
| `\step{...}` | auto-numbered worked-example line; the counter resets at each `examplebox`. Step 1 is always the strategy sentence (why this tool), computation starts at step 2 |
| `\skillheading{...}` | study-guide skill-section heading |

## Problem Patterns

### Simple algebraic problem
The workspace is the macro's optional argument — never a trailing `\vspace`,
which is glue outside the unbreakable box and is discarded at a page break.
```latex
\problem[6cm]{Solve for $x$: \quad $2x^2 - 5x - 3 = 0$}
```

### Two-column layout (shorter problems)
Workspace rides inside each item's `minipage[t]`, not in `itemsep`: itemsep
glue is discarded at every column break (twice per page in two columns), so an
itemsep-spaced sheet loses the workspace of the last item in each column.
3.9cm rather than 4cm keeps the last item from overhanging the bottom margin.
```latex
\begin{multicols}{2}
\raggedcolumns
\begin{enumerate}[label=\textbf{\arabic*.}, itemsep=0pt]
  \item \begin{minipage}[t]{\linewidth}$3x + 7 = 22$\par\vspace*{3.6cm}\ansline\end{minipage}
  \item \begin{minipage}[t]{\linewidth}$-2(x - 5) = 14$\par\vspace*{3.6cm}\ansline\end{minipage}
  \item \begin{minipage}[t]{\linewidth}$\dfrac{x}{4} + 3 = 9$\par\vspace*{3.6cm}\ansline\end{minipage}
  \item \begin{minipage}[t]{\linewidth}$5x - 3 = 2x + 9$\par\vspace*{3.6cm}\ansline\end{minipage}
\end{enumerate}
\end{multicols}
```

### Multi-part problem
Each part carries its own blank, and the parent's single answer line is
**suppressed automatically**: `\ansline`/`\ansblank`/`\answerline` clear the
auto-emit flag, and `\problem` typesets its stem before testing that flag, so a
stem that already contains answer locations never also gets a trailing one. One
"Answer: ____" under a problem with three sub-answers is worse than none, and
it no longer depends on the author remembering to pass a zero workspace.
Giving the parent a workspace (`\problem[4cm]{...}`) is therefore safe: the
parts still own the answers.
```latex
\problem{Given $f(x) = 3x^2 - 2x + 1$, find:}
\begin{enumerate}[label=(\alph*), itemsep=3cm, leftmargin=1.5cm]
  \item $f(0) =$~\ansblank
  \item $f(-2) =$~\ansblank
  \item $f(x+1)$ --- expand and simplify \ansline
  \vspace{2cm}
\end{enumerate}
```

### Function table
```latex
\problem{Complete the table for $y = 3x - 2$.}
\vspace{0.3cm}
\begin{center}
\begin{tabular}{|>{\centering\arraybackslash}m{1.5cm}|>{\centering\arraybackslash}m{1.5cm}|}
\hline
\textbf{$x$} & \textbf{$y$} \\
\hline
$-2$ & \rule{1.2cm}{0pt} \\[0.5cm]\hline
$0$  & \\[0.5cm]\hline
$1$  & \\[0.5cm]\hline
$3$  & \\[0.5cm]\hline
\end{tabular}
\end{center}
\vspace{1cm}
```

## Figure house style — use these styles first

Every graph, chart and model below has a preamble STYLE or a shipped MACRO.
Reach for the style before writing raw TikZ: four rendered-page reviews of the
corpus found the raw-snippet route producing grids a student cannot plot on,
labels struck by curves, charts that answer their own questions, and color
semantics that die in a photocopier. The styles encode the fixes once.

**The house rules the styles enforce** (from four category reviews, each
judged on rendered pages):

- **Black ink; semantics by dash pattern, fill pattern, weight and LABEL —
  never hue.** A shipped grade-3 sheet distinguished 3/8 from 5/8 by red vs
  blue dots; photocopied, the problem is unanswerable. Points compared on one
  line are distinguished by LETTER labels or fill style.
- **Line-weight hierarchy**: minor grid 0.25pt < major grid 0.4pt < axis
  0.8pt < curve/data 1.1pt. The data is the darkest thing on the figure.
- **Fixed physical units, generous sizes.** `wsgrid` uses `x=7mm, y=7mm` —
  never `width/height` stretching, which distorted a corpus slope-1 segment
  to ~30 degrees. Space is the accepted cost of legibility: budget for it in
  `workspace_cm` rather than shrinking the figure.
- **A gridline at every integer a student must plot on.** The grid this
  replaces had lines only every 2 units.
- **Tick labels are white-backed** (the styles do this) so a curve can never
  strike a number.

### Graph styles (pgfplots, in the shipped preamble)

| Style | Use | Notes |
|---|---|---|
| `wsgrid` | student plotting grid to about +-6 | 7mm unit squares, line + label every integer |
| `wsgridwide` | ranges to +-10 | 5.5mm units, labels every 2, line still every 1 |
| `wsgridq1` | quadrant-I context grids (rates) | axes start AT origin; unit words go at the arrow tips, never inside the plot |
| `wsfuntall` | tall-range sketches (cubics) | y compressed 2:1, still gridded |
| `wstrig` | trig axes | give width/height and pi-multiple `xtick`/`xticklabels` |

Companion tikz styles: `wscurve` (1.1pt), `wscurvearrow` (both-end arrows),
`wsraya`/`wsrayb` (one-sided, so no arrowhead backs into an endpoint dot),
`wscurvealt` (dashed second curve — the grayscale-safe way to draw an image
beside its parent), `wsasym` (asymptote, label it ON the line with
`node[wslabel, pos=...]`), `wsclosed`/`wsopen` (endpoint dots), `wslabel`
(white-backed label).

```latex
% blank student grid — this is the whole figure
\begin{tikzpicture}\begin{axis}[wsgrid, xmin=-6, xmax=6, ymin=-6, ymax=6]
\end{axis}\end{tikzpicture}

% answer-key model graph with asymmetric features labeled
\begin{tikzpicture}\begin{axis}[wsgrid, xmin=-6, xmax=6, ymin=-6, ymax=6]
  \draw[wsasym] (axis cs:2,-6) -- (axis cs:2,6)
      node[wslabel, pos=0.10, right] {$x = 2$};
  \addplot[wscurvearrow, domain=-0.9:4.9, samples=100] {x^2 - 4*x + 3}
      node[wslabel, pos=0.85, right] {$y = x^2 - 4x + 3$};
  \draw[wsclosed] (axis cs:1,0) circle (2pt);
  \draw[wsopen]   (axis cs:3,0) circle (2pt);   % open dot: excluded point
\end{axis}\end{tikzpicture}
```

**Answer keys print the model graph.** A "sketch the graph" problem whose key
answers in prose leaves the grader checking a drawing against a sentence; in
the reviewed corpus exactly 1 of 86 axis-bearing documents put a graph in its
key. Use the same `wsgrid` the worksheet printed.

### Chart styles (data displays)

| Style / macro | Use |
|---|---|
| `wsbar` | single-series bar chart the student READS — no value labels; countable gridlines do that work. Pick the ytick step from {1,2,5,10} so every bar top lands ON a gridline, and set `ymax` one step above the tallest bar |
| `wsbar labeled` | bars WITH printed values — only for charts feeding computation (means, fraction-of-total). Never on a sheet whose `read_data` query is value/max_key/min_key/difference: the label answers the question |
| `wsline` | line chart over ordered categories/time |
| `wshist` | a TRUE histogram: touching bars, ticks at BIN EDGES (feed n+1 coordinates). A gapped ybar with interval labels is a bar chart of intervals, not a histogram |
| `wsboxplot` | one box plot; feed `boxplot prepared` the verify `stats` five-number summary, never raw data |
| `wsboxplot pair` | two summaries on ONE shared axis for compare items — one axis cannot mis-scale |
| `\wsdotplot{v/c, ...}{caption}` | K-8 line plots / dot plots; zero-count values keep their tick. `\renewcommand{\wsplotmark}{\wsdotmark}` switches X marks to dots for grade 6+ |
| `wsstemleaf` env + `\wsstemkey` | stem-and-leaf; the key line is REQUIRED |
| `\wspictorow{n}{Name}{half}` | scaled pictograms with a half symbol (3.MD.B.3) |

```latex
% compare two distributions: ONE axis, two prepared summaries
\begin{tikzpicture}\begin{axis}[wsboxplot pair, xmin=0, xmax=20,
                                yticklabels={Class A, Class B}]
  \addplot+[boxplot prepared={draw position=1, lower whisker=4,
    lower quartile=6, median=9, upper quartile=12, upper whisker=18}] coordinates {};
  \addplot+[boxplot prepared={draw position=2, lower whisker=2,
    lower quartile=5, median=8, upper quartile=11, upper whisker=16}] coordinates {};
\end{axis}\end{tikzpicture}
```

### Geometry additions (figure-macros.tex)

`\congtick{P}{Q}` / `\congtickk{P}{Q}` (congruence ticks), `\parallelmark{P}{Q}`
/ `\parallelmarkk{P}{Q}` (chevrons) — CCSS congruence notation, drawn `thick`
because marks are semantics, not auxiliary lines. `\gridtrifig{xA}{yA}{xB}{yB}{xC}{yC}`
— the CCSS-8 transformation grid: every-integer gridlines, gray preimage
triangle ABC, student draws the image.

### Solids (figure-macros.tex) — use these, not raw TikZ

`\cylfig{$r$-label}{$h$-label}`, `\conefig{r}{h}{slant}`, `\prismfig{l}{w}{h}`,
`\pyrfig{base}{h}`, `\cylnetfig{r}{h}{$2\pi r$}` (the surface-area net).
About 4cm tall at scale 1 — that IS the intended print size. The raw snippets
these replace overprinted their own labels (a cylinder's `r = 3` struck its
rim ellipse) and were habitually scaled down to ~2cm in the corpus; if one of
these does not fit, give the problem more `workspace_cm`, do not shrink the
figure below ~0.8 scale.

### Elementary models (figure-macros.tex) — K-4 credibility set

| Macro | Model |
|---|---|
| `\tenframefig{7}` / `\fiveframefig{3}` | ten/five frames, 1.1cm cells (pencil-sized), top-row-first fill |
| `\numbondfig{8}{3}{?}` | number bond, circles sized for a written digit |
| `\fracbarfig{3}{8}` | hatched fraction bar; the whole is FIXED at 9cm so stacked bars share one whole |
| `\fraccircfig{5}{6}` | fraction circle, sectors from 12 o'clock |
| `\arrayfig{3}{5}` | multiplication array (3.OA.A.1), countable 0.85cm pitch |
| `\basetenfig{2}{3}{7}` | base-ten blocks, proportional BY CONSTRUCTION from one unit |
| `\clockfig{3}{30}` | clock; the hour hand advances with the minutes (3:30 renders between 3 and 4) |
| `\elemlinefig{0}{10}` | elementary number line |
| `\fraclinefig{6}{1}` / `\fracptlinefig{8}{1}{5}{$P$}` | fractions on a number line; marked points are labeled by LETTER, never color |
| `\hoplinefig{-5}{5}{-3}{2}` | integer-operation hop arcs |
| `\ineqlinefig{-6}{6}{-1}{geq}` | inequality: open/closed dot + heavy ray |
| `\blanklinefig{-10}{10}{2}` | blank line students mark |
| `\roundlinefig{80}{90}{85}` | rounding line with the MIDPOINT labeled (the tick the decision hinges on) |
| `\tapefig{4}{$6$}{$24$}` / `\tapecmpfig` | tape/bar models with brace totals |
| `\coinfig{25}` / `\coinrowfig{2}{1}{1}{2}` | coins at true relative sizes |

### TikZ pitfalls (each cost a compile-debug cycle; do not rediscover them)

- A single-entry `cycle list` inside a `.style` needs a trailing comma
  (`cycle list={{...},}`) or pgfkeys brace-stripping splits it per token and
  the style silently keeps the default blue.
- `\ifnum` in tikz macros needs `\relax` before `\foreach`/`\draw`, or number
  scanning expands them.
- `\foreach {a, a+step, ..., b}` needs the second element precomputed with
  `\pgfmathtruncatemacro` — the literal form loops to memory exhaustion.
- Do not name pgfmath macros `\u` or `\r` (they shadow LaTeX accents).
- `enlarge x limits={abs=0.75cm}` needs the braced dimension form — plain
  `abs=` errors on symbolic x coords.

## Coordinate Planes

### Blank grid (student fills in)

Use the preamble styles — see "Figure house style" above. The raw snippet this
section used to print had gridlines only every 2 units (no line at any odd
integer, on the figure whose whole job is plotting integer points) and 3.7mm
unit squares on the wide form; `wsgrid`/`wsgridwide` fix both.

```latex
\begin{tikzpicture}\begin{axis}[wsgrid, xmin=-6, xmax=6, ymin=-6, ymax=6]
\end{axis}\end{tikzpicture}
% wide range: wsgridwide (labels every 2, a line still at EVERY integer)
% quadrant-I rates: wsgridq1 (axes from the origin, units at the arrow tips)
```

### Completed graph (answer key — plot a function)
```latex
\addplot[blue, thick, domain=-1:5, samples=100] {x^2 - 4*x + 3};
% Mark points with \fill, NOT a second \addplot[only marks]. Layering a marks
% plot on a function plot made the engine typeset a stray 0.1pt in nullfont —
% five "Missing character" faults, which check_log treats as fatal. The trigger
% is erratic in `samples` (60 and 100 fail; 25, 40 and 200 pass), so it survives
% casual testing and then fails someone else's sheet. Found by an eval agent who
% bisected it; \fill has none of that behaviour.
\fill[red] (axis cs:1,0) circle (1.7pt);   % x-intercepts
\fill[red] (axis cs:3,0) circle (1.7pt);
\fill[green!60!black] (axis cs:2,-1) circle (2pt);   % vertex
\draw[dashed, gray] (axis cs:2,-6) -- (axis cs:2,8) node[above] {$x=2$};
```

## Geometric Figures

**Figure conventions** (apply to every figure):
- **Triangle figures are generated, not hand-drawn**: `scripts/render_figures.py` renders every `triangle`-type problem (and `right_triangle` figure specs on `approx` problems) from the verify JSON as `\probfig{N}` macros — see authoring.md step 4b. The triangle templates below document what the renderer emits; hand-built TikZ remains the pattern only for shapes the renderer doesn't cover (circles, sectors, solids, transversals).
- **Effort markers are generated the same way**: `scripts/render_meta.py` renders `\probpts{N}` point values and `\probmeta{N}` difficulty stars (plus a computed `\totalpoints`) from the verified difficulty tags — see authoring.md step 4c. Never hand-type `\bigstar` or "(N pts)"; the literal forms are banned by `check_prose_consistency.py`, exactly like hand-drawn valued figures.
- **Draw to scale from the problem's actual values** whenever possible — a to-scale figure is a free visual sanity check on the answer. Only distort deliberately (e.g. to make a cramped angle readable), and then add *"(not to scale)"* below the figure.
- Label triangle vertices $A, B, C$ with sides $a, b, c$ opposite them — the same convention the `triangle` verification type uses. In right triangles the right angle sits at $C$, so $c$ is the hypotenuse — the same convention `scripts/render_figures.py` constructs (its `right_triangle` figures imply the right angle at `C`); Keep the macro and renderer consistent with that convention.
- **Every number printed in a figure must come from the problem statement / verify JSON.** Never invent display values; a verified answer key with a mismatched figure is still a wrong worksheet.
- Wrap each figure in `\begin{center}...\end{center}`.

**Avoiding label collisions** (the most common figure defect — check every figure against these):
- Put side labels on the *outside* of the triangle: choose the `above/below/left/right` anchor by edge orientation — `below` for the bottom edge, `above left`/`above right` for the two upper edges of an upward-pointing triangle, mirrored for other orientations. Never leave the default anchor on a midpoint node.
- When an angle-arc label would crowd a vertex label, push it inward with a larger `angle eccentricity` (1.6–2.2) **or** shrink `angle radius` — don't move the vertex label instead, or it will detach from its vertex.
- In thin or small triangles (any angle < 25° or any side rendered < 2cm), move that side's label fully outside with an explicit shift, e.g. `\node[below=2pt] at ...`, and prefer `font=\small` for all labels in the figure.
- Vertex labels take anchors pointing *away* from the triangle interior (e.g. `below left` for a bottom-left vertex).
- After composing a figure, mentally trace each label's bounding box against every drawn line; if in doubt, add a 2pt shift. A worksheet with an unreadable figure fails the student even when the math is right.
- **Keep a problem, its figure, AND its workspace on the same page**: wrap all three in `\noindent\begin{minipage}{\linewidth} \problem{...} \begin{center}\begin{tikzpicture}...\end{tikzpicture}\end{center} \par\vspace*{5cm} \end{minipage}` — LaTeX won't break inside a minipage, so a figure can never be orphaned from its problem across a page break. Put the work-space `\vspace*` *inside* the minipage too: `\vspace` glue outside the box is silently discarded when it falls at a page break, which is exactly when a bottom-of-page problem needs its room. Pages fill less tightly this way — that is the honest cost of not stealing the student's workspace.
- **ASCII only in templates**: pdflatex (the fallback engine) cannot typeset literal Unicode symbols like ⚠ or →. Use LaTeX macros or ASCII markers — `(!)`, `$\rightarrow$`, `$^\circ$` — so documents compile identically under both engines.

### Shipped figure macros — use these before hand-writing TikZ

`templates/figure-macros.tex` (staged beside your `.tex` by `compile.sh`)
covers the two most common figures plus the mandatory reference figure. The
mandatory arguments take flat braces only (no nested `{}`); scale/styling
goes in the optional `[..]` argument — that contract is what lets
`check_layout.py` and `check_prose_consistency.py` see macro figures.

```latex
% right triangle (right angle at C, hypotenuse c — the renderer's convention);
% args = bottom-leg (b), right-leg (a), hypotenuse (c) labels
\rtfig{$8$}{$6$}{$x$}
\rtfig[0.9]{$b = 8$}{$a = 6$}{$c$}

% general triangle, TO SCALE by construction (SAS): numeric args are the
% ACTUAL givens c, b, A(deg); label args are what gets printed
\trifig{7}{5}{34}{$c = 7$}{$b = 5$}{$a = ?$}{$34^\circ$}

% the value-free reference figure (SKILL.md figure-scope rule): vertices
% A/B/C, sides a/b/c opposite, right angle at C (hypotenuse c), caption baked
% in, zero numerals by construction
\refrt
```

The raw TikZ patterns below remain the documented path for figure kinds the
macros do not cover (parallel lines, circles, solids, charts) and show what
the macros do internally.

### Right triangle
Right angle at $C$, hypotenuse $c = AB$ — the same labelling `render_figures.py`
constructs and `\refrt` teaches, so a hand-built figure never contradicts them.
```latex
\begin{center}
\begin{tikzpicture}[scale=1.2]
  \coordinate (A) at (0,0);
  \coordinate (B) at (4,3);
  \coordinate (C) at (4,0);
  \draw[thick] (A) -- (C) -- (B) -- cycle;
  \draw (C) ++(-.25,0) -- ++(0,.25) -- ++(.25,0);  % right angle mark
  \node[below left] at (A) {$A$};
  \node[above right] at (B) {$B$};
  \node[below right] at (C) {$C$};
  \node[below] at (2,0) {$8$};
  \node[right] at (4,1.5) {$6$};
  \node[above left] at (2,1.5) {$x$};
\end{tikzpicture}
\end{center}
```

### General triangle, to scale (SAS setup)
Place $A$ at the origin, $B$ on the x-axis at distance $c$, and compute $C$ from side $b$ and angle $A$ — the figure is automatically to scale. TikZ trig functions take degrees.
```latex
\begin{center}
\begin{tikzpicture}[scale=0.6]
  \coordinate (A) at (0,0);
  \coordinate (B) at (7,0);                        % c = AB = 7
  \coordinate (C) at ({5*cos(34)},{5*sin(34)});    % b = AC = 5, angle A = 34$^\circ$
  \draw[thick] (A) -- (B) -- (C) -- cycle;
  \node[below left]  at (A) {$A$};
  \node[below right] at (B) {$B$};
  \node[above]       at (C) {$C$};
  \node[below]       at ($(A)!0.5!(B)$) {$c = 7$};
  \node[above left]  at ($(A)!0.5!(C)$) {$b = 5$};
  \node[above right] at ($(B)!0.5!(C)$) {$a = ?$};
  \pic [draw, angle radius=7mm, angle eccentricity=1.6, "$34^\circ$"] {angle = B--A--C};
\end{tikzpicture}
\end{center}
```

### Parallel lines cut by a transversal
Intersections at $(1,1)$ and $(-1,-1)$; angle numbers sit in the four quadrants around each.
```latex
\begin{center}
\begin{tikzpicture}[scale=1.1]
  \draw[thick, <->] (-3,1) -- (3,1) node[right] {$\ell_1$};
  \draw[thick, <->] (-3,-1) -- (3,-1) node[right] {$\ell_2$};
  \draw[thick, <->] (-2.2,-2.2) -- (2.2,2.2) node[above right] {$t$};
  % arrowhead-style parallel marks
  \draw (1.9,0.9) -- (2.1,1.1);  \draw (2.1,0.9) -- (2.3,1.1);
  \draw (1.9,-1.1) -- (2.1,-0.9);  \draw (2.1,-1.1) -- (2.3,-0.9);
  \node[font=\small] at (1.55,1.3)   {$1$};
  \node[font=\small] at (0.7,1.3)    {$2$};
  \node[font=\small] at (0.45,0.7)   {$3$};
  \node[font=\small] at (1.3,0.7)    {$4$};
  \node[font=\small] at (-0.45,-0.7) {$5$};
  \node[font=\small] at (-1.3,-0.7)  {$6$};
  \node[font=\small] at (-1.55,-1.3) {$7$};
  \node[font=\small] at (-0.7,-1.3)  {$8$};
\end{tikzpicture}
\end{center}
```

### Circle: central and inscribed angle on the same arc
Keep the geometry honest: the inscribed angle must be half the central angle (here $120^\circ$ and $60^\circ$).
```latex
\begin{center}
\begin{tikzpicture}[scale=0.9]
  \draw[thick] (0,0) circle (2);
  \coordinate (O) at (0,0);
  \coordinate (P) at (150:2);
  \coordinate (Q) at (30:2);
  \coordinate (R) at (270:2);
  \draw[thick] (P) -- (O) -- (Q);
  \draw[thick] (P) -- (R) -- (Q);
  \fill (O) circle (1.2pt);
  \node[below]      at (O) {$O$};
  \node[above left] at (P) {$P$};
  \node[above right] at (Q) {$Q$};
  \node[below]      at (R) {$R$};
  \pic [draw, angle radius=5mm, angle eccentricity=1.9, "$120^\circ$"] {angle = Q--O--P};
  \pic [draw, angle radius=7mm, angle eccentricity=1.6, "$60^\circ$"]  {angle = Q--R--P};
\end{tikzpicture}
\end{center}
```

### Circle: shaded sector
```latex
\begin{center}
\begin{tikzpicture}[scale=0.8]
  \coordinate (O) at (0,0);
  \coordinate (A) at (0:2);
  \coordinate (B) at (115:2);
  \draw[thick] (O) circle (2);
  \draw[thick, fill=blue!12] (O) -- (A) arc (0:115:2) -- cycle;
  \fill (O) circle (1.2pt);
  \node[below left] at (O) {$O$};
  \node[below] at (1,0) {$r = 6$};
  \pic [draw, angle radius=5mm, angle eccentricity=1.9, "$115^\circ$"] {angle = A--O--B};
\end{tikzpicture}
\end{center}
```

### Ambiguous SSA case — two-triangle "swing" figure
Both possible triangles from the same SSA data (here $a=6$, $b=8$, $A=40^\circ$): the swinging side $a$ is drawn solid to $C_1$ (acute $B_1$) and dashed to $C_2$ (obtuse $B_2$). Compute both apex points from the actual solutions so the figure is to scale; keep the shared-side label below and each swing label on its own side of the apex to avoid collisions.

**Don't hand-compute this figure** — `scripts/render_figures.py` emits exactly
this construction as `\probfig{N}`, with both apexes computed by the same
`solve_triangle` that verifies the problem (authoring.md step 4b). That is the
point: an earlier revision of this very example shipped hand-computed constants
`9.24`/`3.05` where the true values are `9.220`/`3.037` — transcription drift
in the skill's own reference figure. The template below documents what the
renderer emits.
```latex
\begin{center}
\begin{tikzpicture}[scale=0.55]
  \coordinate (A) at (0,0);
  % B1 = 58.99$^\circ$, B2 = 121.01$^\circ$, C = 180 - 40 - B. Place base along x-axis:
  % c1 = a·sin(C1)/sin(A) = 9.220, c2 = a·sin(C2)/sin(A) = 3.037
  \coordinate (B1) at (9.220,0);
  \coordinate (B2) at (3.037,0);
  \coordinate (C)  at ({8*cos(40)},{8*sin(40)});   % b = 8 from A at 40$^\circ$
  \draw[thick] (A) -- (B1) -- (C) -- cycle;
  \draw[thick, dashed] (C) -- (B2);
  \node[below left]  at (A)  {$A$};
  \node[below right] at (B1) {$B_1$};
  \node[below=2pt]   at (B2) {$B_2$};
  \node[above]       at (C)  {$C$};
  \node[above left]  at ($(A)!0.35!(C)$)  {$b = 8$};
  \node[above right] at ($(B1)!0.45!(C)$) {$a = 6$};
  \node[right=3pt]   at ($(B2)!0.3!(C)$)  {$a = 6$};
  \pic [draw, angle radius=8mm, angle eccentricity=1.5, "$40^\circ$"] {angle = B1--A--C};
\end{tikzpicture}
\end{center}
```

### Unit circle (skills summary)
Compact version with degree labels; swap the labels for radians ($\frac{\pi}{6}$, …) or exact coordinate pairs depending on the unit being taught.
```latex
\begin{center}
\begin{tikzpicture}[scale=1.8]
  \draw[->] (-1.3,0) -- (1.3,0) node[right] {$x$};
  \draw[->] (0,-1.3) -- (0,1.3) node[above] {$y$};
  \draw[thick] (0,0) circle (1);
  % cardinal angles use offset anchors so labels clear the axes
  \foreach \ang/\lab/\pos in {
      0/{0^\circ}/below right, 30/{30^\circ}/above right, 45/{45^\circ}/above right,
      60/{60^\circ}/above right, 90/{90^\circ}/above right, 120/{120^\circ}/above left,
      135/{135^\circ}/above left, 150/{150^\circ}/above left, 180/{180^\circ}/below left,
      210/{210^\circ}/below left, 225/{225^\circ}/below left, 240/{240^\circ}/below left,
      270/{270^\circ}/below right, 300/{300^\circ}/below right, 315/{315^\circ}/below right,
      330/{330^\circ}/below right}{
    \fill (\ang:1) circle (0.6pt);
    \node[\pos, font=\tiny] at (\ang:1) {$\lab$};
  }
\end{tikzpicture}
\end{center}
```

### Trig function graph (radian axis)
```latex
\begin{center}
\begin{tikzpicture}
\begin{axis}[width=12cm, height=5cm,
  xmin=-0.3, xmax=6.6, ymin=-1.5, ymax=1.5,
  xtick={0, 1.5708, 3.1416, 4.7124, 6.2832},
  xticklabels={$0$, $\frac{\pi}{2}$, $\pi$, $\frac{3\pi}{2}$, $2\pi$},
  ytick={-1, 0, 1}, axis lines=middle, samples=200, domain=0:6.2832]
  \addplot[thick, blue] {sin(deg(x))};
\end{axis}
\end{tikzpicture}
\end{center}
```
For a degree axis (Geometry level): `domain=0:360`, `xtick={0,90,...,360}`, and plot `{sin(x)}` (pgfplots trig defaults to degrees).

### Data charts (bar / line) — data-driven, matches `read_data`
Source the plotted values from the SAME array the `read_data` verify check uses, so the chart and the answer can't disagree.
```latex
% Bar chart of category counts (Mon..Thu = 12,8,15,6)
\begin{center}
\begin{tikzpicture}
\begin{axis}[ybar, width=10cm, height=5cm, bar width=18pt,
  ymin=0, enlarge x limits=0.15, ylabel={Count},
  symbolic x coords={Mon,Tue,Wed,Thu}, xtick=data,
  nodes near coords, axis lines=left]
  \addplot coordinates {(Mon,12) (Tue,8) (Wed,15) (Thu,6)};
\end{axis}
\end{tikzpicture}
\end{center}
```
For a line plot swap `ybar`→(remove) and use `\addplot[mark=*] coordinates {(1,3)(2,7)(3,2)(4,8)}`. For a pictogram, print a row of repeated symbols per category (e.g. `\faStar`×count) instead of an axis.

#### Shared display bank — one chart or table several problems read from
A display carrying values is scoped to the problem it sits in, and the figure-scope
rule is all-or-nothing per problem list (SKILL.md → "Figure scope"), so a chart inside
problem 3 of a sheet whose other problems are figureless fails `check_layout`. The
rule's usual remedy — a *value-free* reference figure — cannot apply here, because a
data display IS its values. Hoist it: problem regions run from one `\problem` to the
next, so a display placed **above the first `\problem`** belongs to no region.
Caption it with the problem numbers that use it.
```latex
\begin{center}
{\bfseries Problems 4--7 refer to this chart.}\par\vspace{2pt}
\begin{tikzpicture}
\begin{axis}[ybar, width=10cm, height=5cm, bar width=18pt,
  ymin=0, enlarge x limits=0.15, ylabel={Books read},
  symbolic x coords={Mon,Tue,Wed,Thu}, xtick=data,
  nodes near coords, axis lines=left]
  \addplot coordinates {(Mon,12) (Tue,8) (Wed,15) (Thu,6)};
\end{axis}
\end{tikzpicture}
\end{center}

\problem[5cm]{...}   % problem 1 — no figure, and now legal beside the chart
```
Two costs, both silent:
- **Nothing verifies its printed values.** `figure_label_numbers` reads inside problem
  regions only, so a drifted tick or a mis-plotted bar on a shared display passes every
  gate. Source the coordinates from the same `data` array the `read_data` entries use,
  and read the rendered page.
- **Nothing charges its height.** The page budget starts at problem 1 too. Add the
  display's height to the `workspace_cm` of the problems that consume it.

Use it only for a display genuinely shared by several problems. A figure one problem
owns stays inside that problem's block, where both checks still run.

### Box plot — `boxplot prepared`, matching `stats`

**Never hand pgfplots the raw data and let it compute the quartiles.** It uses an
interpolating convention; `verify.py`'s `stats` type uses school median-of-halves. On
`[4, 6, 7, 9, 11, 12, 18]` they disagree — verify says median 9, q1 6, q3 12, while
pgfplots draws median 8 and a box from 5 to 11.5. A sheet asking "find the median"
would print a figure contradicting its own answer key, and no gate reads inside a
plot. Declare the five-number summary as `stats` entries and pass those SAME numbers:

```latex
% median/q1/q3 below are the values the stats entries verify -- not retyped by eye
\begin{center}\begin{tikzpicture}
\begin{axis}[width=9cm, height=3.2cm, xmin=0, xmax=20, ytick=\empty,
             axis lines=left, xlabel={Minutes}]
  \addplot+[boxplot prepared={lower whisker=4, lower quartile=6, median=9,
                              upper quartile=12, upper whisker=18},
            black, fill=gray!20] coordinates {};
\end{axis}\end{tikzpicture}\end{center}
```

### Area between two curves — matches `definite_integral`
`name path` + `fill between`. Keep the plotted functions the same expressions the
`definite_integral` entry integrates, and the `domain` its `from`/`to`.
```latex
\begin{center}\begin{tikzpicture}
\begin{axis}[width=8cm, height=5cm, domain=0:2, samples=60,
             axis lines=middle, xlabel={$x$}, ylabel={$y$}, ymin=0, ymax=4.5]
  \addplot[thick, name path=f]{x^2};
  \addplot[thick, name path=g]{2*x};
  \addplot[gray, opacity=0.35] fill between[of=f and g, soft clip={domain=0:2}];
\end{axis}\end{tikzpicture}\end{center}
```

### Shaded area model (fractions, percent, probability)
`patterns` rather than a solid fill: hatching survives photocopying and greyscale
printing, which a light `fill=gray!30` does not. Shade the numerator's parts.
```latex
% 3/8 shaded
\begin{center}\begin{tikzpicture}[scale=0.7]
  \foreach \i in {0,...,7}{\draw (\i,0) rectangle (\i+1,1);}
  \foreach \i in {0,1,2}{\fill[pattern=north east lines] (\i,0) rectangle (\i+1,1);}
\end{tikzpicture}\end{center}
```

### Number line — matches `inequality` / `compare`
`arrows.meta` gives a real arrowhead (`-{Stealth}`); a bare `->` is thin and reads as
a tick at small sizes. Closed dot for `<=`/`>=`, open (`draw, fill=white`) for strict.
```latex
% x >= -1
\begin{center}\begin{tikzpicture}[scale=0.9]
  \draw[-{Stealth}] (-4.4,0) -- (4.4,0);
  \foreach \x in {-4,...,4}{\draw (\x,0.12) -- (\x,-0.12) node[below]{\scriptsize$\x$};}
  \draw[very thick] (-1,0) -- (4.3,0);
  \fill (-1,0) circle (2.5pt);
  \draw[-{Stealth}, very thick] (4.0,0) -- (4.4,0);
\end{tikzpicture}\end{center}
```

### Brace annotating a part — bar models, ratio and part-whole problems
`decorations.pathreplacing`. This is how a "twice as long as" relation is shown
rather than asserted, and the labels are the same symbols the check uses.
```latex
\begin{center}\begin{tikzpicture}
  \draw[thick] (0,0) -- (6,0);
  \foreach \x in {0,2,6}{\draw (\x,0.1)--(\x,-0.1);}
  \draw[decorate, decoration={brace, amplitude=6pt}] (0,0.25) -- (2,0.25)
        node[midway, above=6pt]{\small $x$};
  \draw[decorate, decoration={brace, amplitude=6pt}] (2,0.25) -- (6,0.25)
        node[midway, above=6pt]{\small $3x$};
\end{tikzpicture}\end{center}
```

### Two displays for a compare item

The two-panel `groupplot` template that used to live here auto-scaled each
panel independently — equal-height bars for different values, on a
compare-the-distributions task. Prefer ONE shared axis, which cannot
mis-scale: `wsboxplot pair` for five-number summaries (see "Figure house
style"), or grouped bars distinguished by fill pattern for two categorical
series:

```latex
\begin{tikzpicture}\begin{axis}[wsbar, symbolic x coords={A,B,C}, xtick=data,
    ymax=10, ytick={0,2,...,10}, legend style={font=\small}]
  \addplot[fill=gray!55, draw=black] coordinates {(A,4) (B,7) (C,2)};
  \addplot[pattern=north east lines, draw=black] coordinates {(A,6) (B,3) (C,8)};
  \legend{Class A, Class B}
\end{axis}\end{tikzpicture}
```

If side-by-side panels are genuinely needed, `groupplot` must be given shared
explicit `ymin`/`ymax` and `enlarge x limits` on both panels.

### Fitting an oversized figure — `adjustbox`
When a figure is genuinely wider than the column, scale it; do not redraw it smaller
by hand and do not drop detail to make it fit.
```latex
\begin{adjustbox}{max width=\linewidth}
\begin{tikzpicture} ... \end{tikzpicture}
\end{adjustbox}
```
`max width` only shrinks — a figure already narrower is untouched, so this is safe to
wrap around anything wide. It scales the FONT too, so a figure shrunk far enough stops
being legible: if `adjustbox` is doing more than about 15%, the figure wants fewer
labels, not more scaling.

### 3D solids (volume & surface area problems)

Use the shipped macros — `\cylfig`, `\conefig`, `\prismfig`, `\pyrfig`,
`\cylnetfig` (see "Figure house style"). The raw snippets that used to live
here overprinted their own labels when rendered (`r = 3` struck the cylinder's
rim ellipse; `h = 8` was bisected by its wall) and were habitually scaled down
to ~2cm in the corpus, where hidden-edge dashes degrade to 2-3 coarse marks.
The macros are ~4cm tall at scale 1 with every label outside the silhouette or
leader-lined — that IS the intended print size; give the problem more
`workspace_cm` rather than shrinking below ~0.8. Composite solids: compose the
macro bodies (they are plain TikZ inside), keeping `thick` outlines and dashed
hidden edges.

## Answer Key Patterns

### Answer key header and title block
Use the shipped macros (defined in `templates/worksheet-preamble.tex`):
```latex
\akheader{TOPIC}                       % keep TOPIC short (under ~28 chars)
...
\aktitleblock{TOPIC}{COURSE}{}         % empty 3rd arg = no printed date (reusable)
\input{qa_TOPIC_DATE}                  % the generated quick-answer bank (DATE here is the filename token, not printed)
```
`\aktitleblock` puts the topic on its own line (shrink-to-fit) and **"Answer
Key" as a subtitle beneath it** — never append "--- Answer Key" to the big
title, or a long topic wraps mid-phrase. The skills summary uses
`\ssheader`/`\sstitleblock` the same way.

`\ans` differs between the two shells and the difference is deliberate.
`\akheader` replaces it with a compact same-line `\fbox`; a study guide keeps
the base definition, a bold symbol, so the answer reads as emphasis inside a
worked example rather than as a second box inside a box. Both forms work in
text and in math — the exemplars below write `$\ans{...}$` and that is still
the house style, but `\ans{x = 3}` in prose is legal and prints the same thing.
It was not always: the base definition was a bare `\boldsymbol`, math-only, and
a study guide written from authoring.md's prose rather than copied from a template
failed the `compile-ss` gate with `! Missing $ inserted` pointing at a line two
away from the cause. Check the compiled PDF, because source-only checks cannot see this.

### Quick-answer bank (generated, never hand-edited)

The generated file also carries the key's FINAL page: a "Verification &
Curriculum Summary" (what-is-verified note, curriculum block, common wrong
answers) emitted through `\AtEndDocument{\clearpage ...}` — so the reading
order is header, Quick Answers, worked solutions, then the summary on a page
of its own, with no extra `\input` and no author action. The hand-judged mark
in the bank is `$\spadesuit$`; the summary's legend explains it wherever it
appears.
`scripts/render_quick_answers.py` regenerates `qa_<stem>.tex` from the verify
JSON on every build — a compact multi-column "answers at a glance" block for
fast grading, placed by the one `\input{qa_<stem>}` line directly under
`\aktitleblock`. The build gate fails a key that hand-rolls its preamble or
never `\input`s the bank; the bank's entries are plain text (never
`\ans`/`\boxed`), so `check_answer_key.py`'s strict per-problem binding is
untouched.

### Step-by-step solution
`\akheader` switches `\ans{...}` to a compact form that keeps the `\fbox` on
the same line as the last worked step when it fits (flush-right on the next
line when it does not), roughly halving the key's vertical space. Prefer it
for single-value answers; keep the display `\[ \boxed{...} \]` form for long
or multi-value answers.
```latex
\problem{[Repeat full problem statement]}

\textbf{Solution:} \quad $3x = 15$, so $x = 5$. \ans{x = 5.00}
```
```latex
\problem{[Repeat full problem statement]}

\textbf{Solution:}
\begin{align*}
  2x^2 - 5x - 3 &= 0 \\
  \intertext{Factor --- find factors of $2(-3)=-6$ summing to $-5$: use $-6,+1$:}
  2x^2 - 6x + x - 3 &= 0 \\
  2x(x - 3) + 1(x - 3) &= 0 \\
  (2x + 1)(x - 3) &= 0 \\
  \intertext{Zero product property:}
  2x + 1 = 0 \quad &\text{or} \quad x - 3 = 0 \\
\end{align*}
\[ \boxed{x = -\tfrac{1}{2} \quad \text{or} \quad x = 3} \]

\vspace{0.3cm}\noindent\rule{\linewidth}{0.2pt}\vspace{0.3cm}
```

### Sign chart (for polynomial graphing)
```latex
\[
\underbrace{+}_{x<-2}\ \Bigl|_{-2}\ \underbrace{-}_{-2<x<0}\ \Bigl|_{0}\ \underbrace{-}_{0<x<2}\ \Bigl|_{2}\ \underbrace{+}_{x>2}
\]
```

### Two-column proof (geometry answer keys)
Proofs are always `manual` in the verify JSON, but the answer key should still show a complete model proof for the student to compare against.
```latex
{\renewcommand{\arraystretch}{1.5}
\noindent
\begin{tabular}{|p{0.47\textwidth}|p{0.43\textwidth}|}
\hline
\multicolumn{1}{|c|}{\textbf{Statements}} & \multicolumn{1}{c|}{\textbf{Reasons}} \\ \hline
1.\ $\overline{AB} \cong \overline{DE}$;\ $\angle A \cong \angle D$ & 1.\ Given \\
2.\ $\angle ABC \cong \angle DEF$ & 2.\ Vertical angles are congruent \\
3.\ $\triangle ABC \cong \triangle DEF$ & 3.\ ASA \\
4.\ $\overline{BC} \cong \overline{EF}$ & 4.\ CPCTC \\ \hline
\end{tabular}}
```
On the student worksheet, print the same table with empty rows (use `\rule{0pt}{1.1cm}` in the first cell of each blank row for writing space).

---

## Skills Summary / Study Guide Template

This is the **third document** generated alongside every worksheet — or the ONLY document, via `build.sh <verify_ss_...json> --study-guide-only`. It is a reference card: 2 pages by default, extensible to a declared `"pages"` (1–6) in the verify_ss JSON when diagrams need the room or the user asks for a longer guide.

### The design system, and the evidence each piece rides on

Every box opens with a printed title tab — RULE (blue), EXAMPLE (green), TRY IT (violet), WATCH OUT (orange) — so a student scanning for the formula finds it without reading a word. The tab is generated by the environment; never add your own headings inside a box. The palette is signaling, not decoration: the tab TEXT carries the meaning after a grayscale photocopy.

Two optional macros implement the two best-supported upgrades from the worked-example literature:

```latex
egin{examplebox}
\step{Strategy: legs known, hypotenuse wanted --- that is the Pythagorean theorem.}
\step{$c = \sqrt{9 + 16} = \sqrt{25}$}
\why{squaring makes both legs positive contributions, so orientation cannot flip a sign.}
\step{So $ns{c = 5}$}
\end{examplebox}
egin{tryitbox}
Legs 6 and 8. What is the hypotenuse?
adestep{$c = \sqrt{36 + 64}$}
\hfill
otatebox{180}{ootnotesize check: $ns{c = 10}$}
\end{tryitbox}
```

- `\why{...}` — a one-line self-explanation aside, small and indented under its step. Write the *reason the move is legal*, never a restatement ("dividing keeps the equality because both sides change together", not "we divide by 3"). At most one per example: a why on a routine move buries the one that matters. Keep it number-free — the prose checker reads any numbers against the JSON entry.
- `adestep{...}` — turns the try-it into a **completion problem**: prints "Started for you: ⟨setup⟩ / Finish it:". Backwards-fading (example → partly-worked → bare problem) beats the straight jump on multi-step skills; skip it on one-move skills. The shown setup's numbers must come from the entry's expr, like any printed intermediate.
- **Dual coding**: when the skill is spatial, put a small **value-free** diagram in the formulabox beside the rule — `
efrt` for trig ratios, a mini `wsgridq1` axis for graphing vocabulary, `raclinefig` for fraction placement. A rule the student can see beats the same rule in symbols alone. Two or more diagrams usually justify `"pages": 3`.

### Grade level: answer key only

`\wstitleblock{Title}{Course}{Date}` accepts the course/level and does **not**
print it. Nothing a student holds carries a grade label — a child working a grade
below or above reads it before the mathematics. The answer key keeps it, in
`\aktitleblock` and in the generated **Curriculum** section, which
`render_quick_answers.py` builds from the verify JSON and the key's own title
block: level, each standards code with the problems it covers, and the difficulty
range. Built, never typed, so it cannot disagree with the verified tags.

Keep passing the course argument to `\wstitleblock`. It is the single place the
level is declared, and the curriculum section reads it from there.

## Page budget (measured, not guessed)

**The worksheet budget cannot see the stem.** It charges a flat 0.6 cm per
problem, so a stem carrying a table, a counter drawing, or a displayed equation
runs 1.5–2 cm over its charge — on a twelve-problem sheet that is most of a
page. Declare the difference as `workspace_cm`. Raising the printed
`\problem[Ncm]` argument instead moves the budget and the real page count
together and cannot close the gap.

**Study-guide section cost is quantised, not additive.** `\skillheading` carries
`\needspace{4\baselineskip}` and the boxes are unbreakable `mdframed`
environments, so a section whose formula box will not fit in the page remainder
moves *entirely* to the next page. The per-section figure below is an average,
not a ceiling: a `formulabox` holding displayed math or a bulleted list runs 2–3×
the quoted cost. Budget four sections when any section carries a figure or
displayed math, and five only when every section is prose-and-formula.

The guide is hard-capped at 2 pages by the `compile-ss` gate. These are the
real typeset heights at `margin=0.85in, top/bottom=0.7in`:

| Item | Height |
|---|---|
| One page of text | 691pt (2 pages = 1382pt) |
| `\sstitleblock` | ~80pt (one-time) |
| `\skillheading` | 24pt |
| `formulabox` | ~45pt |
| `examplebox` (2 steps + answer) | ~82pt |
| `tryitbox` | ~45pt |
| `watchoutbox` | ~38pt |

A full skill section (heading + all four boxes) costs **~234pt**, so the budget
is `(1382 - 80) / 234` ≈ **5 full skill sections**. Five fit; a sixth spills
onto page 3 and fails the gate.

Sizing rules:
- **5 full sections is the ceiling, not a target.** Prefer 3-4 with room to
  breathe over 5 crammed sections.
- A long worked example (4+ `\step` lines, displayed fractions, a figure) can
  double an `examplebox`. Budget 2 long examples as 3 short ones.
- **Drop in this order when over budget:** `watchoutbox` first (it is the only
  optional box), then merge two thin skills into one section, then shorten
  worked examples. Never drop the `tryitbox` — retrieval practice is the point.
- Do **not** add `\vspace` between boxes. The box environments carry their own
  `skipabove`/`skipbelow`; hand-added glue is what pushed guides onto page 3.

### Document shell

The colors, box environments (`formulabox`/`examplebox`/`watchoutbox`), and
`\skillheading` all live in `templates/worksheet-preamble.tex` — the same
file the worksheet inputs. Only the geometry margins differ:

```latex
\documentclass[12pt]{article}
\usepackage[margin=0.85in, top=0.7in, bottom=0.7in]{geometry}
\input{worksheet-preamble}
\ssheader{TOPIC}

\begin{document}

\sstitleblock{TOPIC}

% =================== SKILL 1 ===================
\skillheading{Skill 1 Name --- e.g. Factoring Trinomials (a = 1)}

\begin{formulabox}
\textbf{Rule / Formula:}\\[4pt]
$x^2 + bx + c = (x + p)(x + q)$ \quad where $p + q = b$ and $p \cdot q = c$
\end{formulabox}

\begin{examplebox}
\textbf{Example:} \quad Factor $x^2 - 7x + 12$
\step{Product $+12$ with sum $-7$: both numbers are negative --- hunt for a negative factor pair of $12$.}
\step{$-3$ and $-4$: \ $(-3)+(-4) = -7$, \ $(-3)(-4) = 12$ $\checkmark$}
$\Rightarrow\quad x^2 - 7x + 12 = \ans{(x-3)(x-4)}$
\end{examplebox}

\begin{tryitbox}
\textbf{Try it:} \quad Factor $x^2 - 9x + 20$\\[2pt]
\rotatebox{180}{\footnotesize check: $\ans{(x-4)(x-5)}$}
\end{tryitbox}

\begin{watchoutbox}
% Engine-neutral warning marker: pdflatex cannot typeset a literal Unicode (!),
% so use a bold exclamation badge that works under both tectonic and pdflatex.
\textbf{(!) Watch out:} Signs matter! If $c > 0$, both factors have the \textit{same sign} as $b$.\par
If $c < 0$, the factors have \textit{opposite signs}.
\end{watchoutbox}

% =================== SKILL 2 ===================
\skillheading{Skill 2 Name --- e.g. Quadratic Formula}

\begin{formulabox}
\textbf{Formula:}\\[4pt]
\[
  x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
\]
\textbf{Discriminant:}\quad $\Delta = b^2 - 4ac$\par
\begin{itemize}[leftmargin=1.5cm, itemsep=1pt, topsep=2pt]
  \item $\Delta > 0$: two real solutions
  \item $\Delta = 0$: one real solution (double root)
  \item $\Delta < 0$: no real solutions (complex roots)
\end{itemize}
\end{formulabox}

\begin{examplebox}
\textbf{Example:} \quad Solve $2x^2 - 3x - 5 = 0$
\step{No obvious factor pair and $a \neq 1$ --- go straight to the quadratic formula.}
\step{$a = 2,\ b = -3,\ c = -5$: \quad $\Delta = 9 + 40 = 49$, \quad $x = \dfrac{3 \pm 7}{4}$}
$\Rightarrow\quad\ans{x = \tfrac{5}{2}}$ \quad or \quad $\ans{x = -1}$
\end{examplebox}

\begin{tryitbox}
\textbf{Try it:} \quad Solve $3x^2 - 5x - 2 = 0$\\[2pt]
\rotatebox{180}{\footnotesize check: $\ans{x = 2}$ or $\ans{x = -\tfrac{1}{3}}$}
\end{tryitbox}

% =================== KEY VOCABULARY ===================
\vspace{0.3cm}
\skillheading{Key Vocabulary}

\begin{multicols}{2}
\begin{description}[leftmargin=0.5cm, itemsep=2pt, font=\normalfont\bfseries]
  \item[Term 1:] Definition here
  \item[Term 2:] Definition here
  \item[Term 3:] Definition here
  \item[Term 4:] Definition here
\end{description}
\end{multicols}

\end{document}
```

### Usage guidance

- Generate **one skill section per distinct skill** tested in the worksheet (typically 2–5 sections)
- Each section should have: a formula/rule box + 1 mini example + 1 try-it + optional watch-out. Formula-only reference sections (no example) are legal and need no try-it
- Keep the whole document to **1–2 pages max** — it's a reference card, not a lesson
- Vocabulary section is optional — include only when there are ≥3 important terms
- The mini examples have **fewer steps than worksheet problems, but the choose-the-tool step is always written out** — one sentence, before any computation, never a bare answer chain. `\step` 1 names what you want, what you know, and why that picks this tool/ratio/method; the computation starts in `\step` 2 and the result prints in `\ans{...}`. Two more exemplars:
  - trig: `\step{Want the side opposite $A$, know the hypotenuse --- that is SOH: $\sin A = \text{opp}/\text{hyp}$.} \step{$a = 10\sin 40^\circ = 6.4279\ldots$}` then `$\ans{a \approx 6.43}$`
  - definition recall (when the example just applies a definition, SAY so — don't pad): `\step{Want $\sin A$ --- sine is opposite over hypotenuse by definition.}`
- The try-it re-parameterizes its section's worked example (same skeleton, new givens) and prints ONLY the stem plus the verified answer upside down INSIDE the box: `\rotatebox{180}{\footnotesize check: $\ans{...}$}`. No worked steps — solving it is the student's retrieval practice. The answer must stay inside the box: an `\ans` outside every box degrades the whole document's per-example binding
- The watch-out box is optional per skill — only add if there's a genuinely common mistake worth flagging
