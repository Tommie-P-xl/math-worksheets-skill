# Global bank and exam-style authoring

This mode improves new/similar question design. It does not require archiving the
uploaded example, and it does not replace the existing math/PDF verification gates.

## Fast path for an agent

1. Recover the source faithfully. Separate givens from handwriting/solutions.
   Identify stage, grade/semester or exam, subject and taught prerequisites. Ask
   when the missing grade or taught scope changes permissible methods. A grade is
   a proposal until confirmed; CN, CCSS and AP grade mappings are not interchangeable.
2. Extract the seven demand fields below. Distinguish estimated difficulty from
   measured outcomes for a specified student group. Do not equate a Bloom/DOK label
   or many computations with measured difficulty.
3. Run ONE `context` query with stage/subject and relevant tags/text. Default 5,
   maximum `reference_limit` references TOTAL (default 10; read `config` first), including the single stage-subject guide. Across
   follow-up queries/show calls, track distinct IDs and guide keys; never exceed
   the configured limit in one authoring request. A longer solution/figure read for an already chosen
   ID does not count twice. Read only needed fields; do not dump the database.
4. Use relevant local examples and guide sections directly. If inadequate, make
   a short lookup with the agent's available web tools: prefer the education
   authority's curriculum, the requested region/year's official requirements, and
   an assessment body's documented authoring process. Research process guidance
   does not make a foreign curriculum apply to a Chinese student. Save URL, title,
   checked date and applicable scope in a LOCAL guide proposal. Do not browse again
   just because a reusable, applicable reference is old; recheck time-sensitive
   requirements when the requested year/scope differs or the user asks to verify.
   Without web access, use established methods and state what was not checked.
5. Draft a blueprint: target skill, question family, decisive inference, subpart
   progression, difficulty levers, expected time and marking points. Solve first,
   then word the question. Preserve demand and exam style, not just numbers or
   scenery. Check all admissible cases, parameter ranges and degenerate figures.
6. Solve independently of the proposed key. Use `verify.py` on supported numeric/
   symbolic responses, mark proof obligations for review, and inspect figures.
   Check correctness, taught scope, demand and style separately. Do not claim that
   bank retrieval or a passed calculation proves educational quality.
7. Deliver the requested work. Offer EACH uploaded/generated question for optional
   archival, displaying its proposed tags and demand summary. Separately show the
   exact guide addition/replacement and ask whether to save it. No reply/decline
   means no save; “use these as references” is not archival approval. Revisions to
   a proposal invalidate its earlier approval; show changes and obtain approval
   for the final content. A clear reply selecting specific unchanged proposals is
   sufficient; do not ask for the same approval again.

## Teacher process and reusable guide content

Use curriculum and actually taught scope to define a blueprint before writing.
Write a solution and scoring points alongside the question. Review language,
diagrams, alternate solutions, case completeness and time burden. After use,
record feedback and revise difficulty estimates rather than declaring them facts.
These principles follow the public [Cambridge quality process](https://www.cambridgeinternational.org/about-us/our-standards/assessment-standards/)
and [paper-development explanation](https://www.cambridgeinternational.org/Images/595715-how-we-create-an-exam-paper-video-transcript.pdf).
They are process references, not a default curriculum. Consult the applicable
official standard when grade/content alignment matters.

The one guide for each stage-subject should contain compact general authoring
rules and topic sections. A topic section says: taught prerequisites; suitable
families/recognition signals; expected solution chain and scoring points; ways to
raise/lower demand; pitfalls/invalid variants; evidence IDs/URLs and user overrides.
For example, a similarity section can distinguish an explicit AA warm-up from
finding hidden angle correspondences, then a ratio application. A folding section
must distinguish reflection invariants from visual guesses and check which
isosceles cases are geometrically possible. A shortest-path section should say
when reflection is valid and verify that the optimum lies on the allowed segment.

Summaries inferred from one example remain tentative. Generated questions are
not independent evidence for their own quality. Clearly separate user preferences,
official scope and inferred heuristics. Update an existing section rather than
adding repetitive sections. If a topic makes the guide too long, propose a concise
rewrite for user approval; never silently truncate rules or create a second guide.
The editable guide is authoritative text; SQL stores its identity/provenance and
revisions. A valid direct user edit is read immediately without a re-import. The
tool rejects overlength files with their path so the user can shorten or adjust
the configured cap; it does not discard the end.

## Storage and commands

For visual browsing and selecting references by short numbers (`Q1`, `Q3`),
see [bank-browser.md](bank-browser.md). `show` and `select` accept either a short
number or the existing full ID. Short numbers are local to one bank home and
remain fixed across revisions, filtering, new inserts and backup/restore.

Resolve home identically in every project: explicit `--home` for tests/migration,
then `MWS_DATA_HOME`, then `%LOCALAPPDATA%/MathWorksheets` on Windows,
`~/Library/Application Support/MathWorksheets` on macOS or
`${XDG_DATA_HOME:-~/.local/share}/math-worksheets` on Linux. Never place it in a
skill installation. Reading a missing bank returns empty and creates nothing.
All commands print compact UTF-8 JSON. Use absolute paths in real invocations.

```text
python SKILL_DIR/scripts/question_bank.py schema
python SKILL_DIR/scripts/question_bank.py context --stage 初中 --subject 数学 --topic 相似三角形 --query "AA 比例" --limit 5
python SKILL_DIR/scripts/question_bank.py preview --file WORK/question.json
python SKILL_DIR/scripts/question_bank.py commit --file WORK/question.json --approved PREVIEW_SHA256 --approval-note "user's explicit reply or message reference"
python SKILL_DIR/scripts/question_bank.py guide-preview --stage 初中 --subject 数学 --file WORK/proposed.md --sources WORK/research.json
python SKILL_DIR/scripts/question_bank.py guide-commit --stage 初中 --subject 数学 --file WORK/proposed.md --sources WORK/research.json --approved PREVIEW_SHA256 --approval-note "user's explicit reply or message reference"
python SKILL_DIR/scripts/question_bank.py guide-show --stage 初中 --subject 数学
python SKILL_DIR/scripts/question_bank.py show QUESTION_ID --fields stem,answer,solution,diagram,verification
python SKILL_DIR/scripts/question_bank.py browse --out WORK/bank.html --open
python SKILL_DIR/scripts/question_bank.py select Q1 Q3 --fields title,stem,answer,solution,alternative_solutions,tags,demand,diagram,verification
python SKILL_DIR/scripts/question_bank.py config
python SKILL_DIR/scripts/question_bank.py guide-status --stage 初中 --subject 数学
python SKILL_DIR/scripts/question_bank.py guide-review --stage 初中 --subject 数学 --id QUESTION_ID --note "Reviewed this solution; existing topic section already covers its method."
python SKILL_DIR/scripts/question_bank.py migrate
python SKILL_DIR/scripts/question_bank.py migrate --apply --backup-keep 1
python SKILL_DIR/scripts/question_bank.py stats
python SKILL_DIR/scripts/question_bank.py doctor
python SKILL_DIR/scripts/question_bank.py backup --out USER_SELECTED_BACKUP.zip
python SKILL_DIR/scripts/question_bank.py restore --file BACKUP.zip --home NEW_EMPTY_HOME
python SKILL_DIR/scripts/question_bank.py export --out WORK/bank.jsonl
```

`preview` never writes personal storage. The approval digest binds the whole
proposal, source hash metadata, policy settings and current target revision; edits/concurrent
changes require a fresh preview. `--approval-note` is an audit record, not proof
of human consent: the agent MUST obtain an actual reply and must never fabricate
it. There is no blanket `--yes`/auto-save switch or persistent pending inbox.
Exact duplicates merge approved metadata and sources into one record. Possible
duplicates appear in preview; set `duplicate_decision` to `{"action":"same","id":"..."}`
or `{"action":"distinct"}` only after review. To intentionally revise a saved
question's answer/text, specify its `id`; preview binds the previous revision.
Merged tag sets over five are rejected: propose broader accurate labels and ask
the user to approve the replacement. The tool never drops tags silently.

`context` returns snippets with explicit truncation flags, a character budget
(configured default 10000, not a tokenizer-exact token count) and the number of references.
Read full fields only for selected IDs if needed. Empty/inadequate matches do not
block authoring. Prefer relevant quality to filling the reference limit.

## Question JSON

Run `schema` for a compact example. Required fields:

- `title`, `summary`, `stem`, `answer`, `solution` as UTF-8 text; formulas use LaTeX.
- Optional `alternative_solutions`: a list of `{title, solution}` objects for
  additional complete methods under the same question. `solution` remains the
  primary method, so old records remain valid. Each method has a nonempty title
  (at most 120 characters) and complete text/code (at most 40000 characters),
  subject to the same no-image-dependencies rule. Follow the paragraph/display
  layout in [solutions.md](solutions.md); check each method independently.
  Use explicit-ID revision proposals to add methods to an existing record.
  `show` includes all methods by default; `select` can request
  `alternative_solutions`. Bounded `context` lists extra-method titles; retrieve
  full text only for selected questions. Backups and JSONL exports retain methods.
- `tags`: categories `stages`, `subjects`, `grades`, `exams`, `topics`, `types`,
  `methods`; each category has 0–5 distinct concise strings (each at most 32 chars).
  Stage and subject are required; stage values are only 小学/初中/高中. Multiple
  grade/exam tags belong to one record, not separate copies. Use unknown grade
  explicitly in the conversation rather than inventing a label. Resolve the grade
  when needed before authoring. Additional categories are rejected.
- `demand`: `knowledge_span`, integer `reasoning_steps` (estimated count),
  `method_visibility`, `calculation_load`, `case_burden`, `scaffolding`,
  `difficulty` (`estimate` 1–5, `basis` estimated/observed, `reason`). An observed
  rating needs `evidence` describing cohort/sample size/results; do not invent data.
- `origin`: uploaded/generated; `verification`: `status` unverified/mixed/
  machine-checked/reviewed, `notes`, optional `checks` matching `verify.py` entries.
  This status is recorded, not certified by the bank; run the actual math checks.
  A mixed proof/calculation item must not be labeled entirely machine-checked.
- Optional `diagram`: `givens` (semantic relationships), `format` tikz/pgfplots/svg,
  `code`, `layout_coordinates`, `answer_overlay`. Display coordinates are not
  givens; answer-only constructions stay out of the question figure. Retrieval
  loads semantic givens first, code only on demand. Stored code is never executed
  by this bank tool.
- Optional `sources`: list of `{file, locator, label}` at intake (hash only, no copy), or `{name, locator, label, sha256, size}` for portable provenance, or
  `{url, title, checked_at}` for web references. Files are hashed at preview for provenance and never copied into the bank. File sources require a nonempty page/question
  `locator` so different questions on one scanned page are not merged as one.
  Keep personal handwriting out of the typed stem.
- Optional `family` to link structural variants (not a claim of duplication),
  `uncertainties` (nonempty blocks commit), and `id` for an explicit revision.

Unknown fields, duplicate tags, unbounded labels and malformed demands are
rejected. Identity normalizes harmless text/LaTeX whitespace and includes semantic
diagram givens; it never uses grade tags or an answer as a second question identity.
Renamed/rephrased mathematical equivalents require review: automatic similarity
matching is best-effort and cannot prove general mathematical equivalence.

## Guides, maintenance, backup

There is one `guides/STAGE/SUBJECT.md` per stage-subject, enforced in SQL and by
deterministic filenames. Default max length is **6000 Unicode characters including
headings/links**, configurable using `config.json` `guide_max_chars` (500–12000).
The same cap applies to CLI writes and direct-edit reads; overflow is an explicit
error. Sources JSON is a list of `{url,title,checked_at,scope}`. Official facts must
retain scope/date/source; unverified teaching heuristics must be labeled as such.

`stats` reports actual paths, counts, tag inventories, and separate bytes for
database/guides/backups/config (sources must be zero after migration). `doctor` checks SQL integrity, payloads,
tag indexes, invalid source metadata or remaining legacy attachments and overlength/externally edited guides.
`export` writes portable text question/guide records (including complete text/code solutions, without original bytes). To import a text question, extract its `item` object, retain filename/locator/hash provenance, then preview and approve it individually; never bulk-save
an unreviewed export. Backups contain a consistent SQLite snapshot, guide text, config and a SHA-256 manifest; no original attachments. Restore validates in an isolated staging
directory and only targets an absent/empty directory, leaving the old bank intact.
Each write snapshots the previously committed state of an existing bank; retention is
`backup_keep` in config (default 1). Retention only removes tool-owned `auto-*.zip`.
For disk-loss protection choose another disk for a backup copy. Reinstallation
does not initialize over existing data. A newer incompatible schema is refused.
No background process, extra API subscription, vector service or model training
is required. Agents with shell/file access share this home; cloud/other-device
agents need an explicit transfer or a separate synchronization design.


## Schema 2 migration and text/code completeness

The bank stores no attachment bytes. Every question must contain its full stem,
answer and complete worked solution (all parts/cases). Inline drawing code and
semantic diagram givens must let an agent understand it without loading a picture.
Use `diagram.code` for the student figure, `diagram.answer_overlay` or inline
solution code for auxiliary constructions, and `layout_coordinates` only for
layout. Coordinates are not mathematical givens. No `includegraphics`, embedded
raster SVG images, data-image URLs or Markdown image dependencies are allowed.
A nonempty solution field is structurally checked; the agent must still review
mathematical completeness rather than calling storage validation a proof.

`migrate` is a read-only legacy-to-current-schema plan. `migrate --apply` preserves question IDs,
revisions, stem/answer/solution/drawing code/tags and provenance names/hashes;
it removes source blob references from current records and audit history,
creates a text-only recoverable snapshot, then removes managed source files.
Unresolved visual-only solutions block migration. Automatic backups are pruned
using `backup_keep`; manual backups remain user-owned. Migration does not invent
missing solutions or erase the user's external source files. Legacy-schema backup ZIPs
must be restored with a schema-compatible earlier skill into an isolated home and then
migrated; never mix schemas or overwrite an existing bank.

## Guide coverage after every question change

After each approved insert/revision, read the returned `guide_reviews` or run
`guide-status`. Pending records are keyed by question ID and revision, so a
changed solution is reviewed again. Inspect each pending solution, then either:

- Propose a concise topic update with evidence IDs. Obtain the user's actual
  approval unless the current request already authorizes this exact maintenance;
  run guide-preview/guide-commit. The digest binds the guide, its prior version
  and all pending question revisions covered by the review.
- If existing guidance suffices, use guide-review with the inspected IDs and a
  concrete assessment note. This records a review without changing guide text.

Do not mechanically append one section per question or mark unseen records
reviewed. A stored draft heading is not evidence of approval; retain audit
provenance and remove stale draft wording only during an authorized update.
Numeric limits and switches are documented in [configuration.md](configuration.md).
