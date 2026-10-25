# Mathematical figure patterns

Load only for the figure type needed. Examples are components, not complete worksheet templates.
Do not add a blank plotting area unless requested.

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
