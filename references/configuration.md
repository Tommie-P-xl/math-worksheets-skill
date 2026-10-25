# Live configuration

All common numeric controls and switches live in one UTF-8 JSON file:
`DATA_HOME/config.json`. Commands reload it each time. Reads of a missing bank
create nothing; `python scripts/question_bank.py config --init` materializes all
settings without creating a database. `config` prints the effective settings and
absolute path. Edit the file in a text editor; JSON booleans are `true`/`false`.
Unknown fields, invalid types and invalid ranges are rejected without truncation.
Keep `reference_default <= reference_limit` when changing the retrieval cap.

`config.json` is standard JSON with a reserved `_comments` object containing
short Chinese descriptions and defaults keyed by parameter name. Notes do not
change the corresponding values. Missing notes are supported for older files;
`config --init` fills defaults and regenerates all notes while preserving valid
settings. Each note must be text for a known parameter. Regular JSON tools can
read the file, and backup/restore retains its notes.

```json
{
  "backup_keep": 1,
  "reference_limit": 10,
  "_comments": {
    "backup_keep": "自动备份保留代数；手动备份不自动删除。默认：1。",
    "reference_limit": "每次命题可参考的不同题目和指南总上限。默认：10。"
  }
}
```

| Setting | Default | Meaning |
| --- | --- | --- |
| `backup_keep` | 1 | Automatic snapshot generations, 1–100; manual backups are untouched |
| `auto_backup_enabled` | true | Snapshot the committed previous state before each successful write |
| `reference_limit` | 10 | Maximum distinct question + guide references for one authoring request, 1–100 |
| `reference_default` | 5 | Default retrieval packet size, including its guide |
| `context_max_chars` | 10000 | Default packet character budget |
| `context_max_chars_limit` | 50000 | Largest permitted packet budget, at most 1000000 |
| `guide_max_chars` | 6000 | Guide length including headings and links, 500–12000 |
| `guide_excerpt_chars` | 2400 | Retrieved guide excerpt budget |
| `stem_excerpt_chars` | 1600 | Stem snippet budget |
| `answer_excerpt_chars` | 500 | Answer snippet budget |
| `solution_excerpt_chars` | 900 | Solution snippet budget; use `show` for the complete solution |
| `givens_excerpt_chars` | 1200 | Semantic diagram snippet budget |
| `duplicate_threshold` | 0.82 | Similarity review threshold, greater than 0 and at most 1 |
| `duplicate_scan_limit` | 300 | Recent questions compared for possible duplicates |
| `duplicate_candidate_limit` | 5 | Maximum possible duplicate candidates shown |
| `guide_review_on_commit` | true | Require the agent to inspect guide coverage after inserts/revisions |
| `default_question_count` | 10 | Agent's default practice quantity when unspecified |
| `page_margin_left_mm`, `page_margin_right_mm` | 12 | PDF horizontal margins, 5–50 mm |
| `page_margin_top_mm`, `page_margin_bottom_mm` | 12 | PDF text margins, 5–50 mm; allow room for optional running heads |
| `problem_gap_mm` | 1.5 | Compact question spacing |
| `answer_problem_gap_mm` | 2 | Answer-key question spacing |
| `page_numbers` | true | Page numbers in shared running-header modes |
| `name_date_fields` | false | Optional first-page name/date blanks; document supplies localized labels |
| `header_rule` | false | Optional running-header separator |
| `quick_answers` | false | Optional generated answer table; no automatic report appendix |

`compile.sh` refreshes `mws-settings.tex` beside the working TeX file every run.
The settings affect the next build, not an already generated PDF. The storage
rule (text/code only), archival approval, verification requirements and schema
invariants are not optional switches. Retrieval caps also apply across repeated
queries: the agent must count distinct question IDs and guide keys per request.

Use Python 3.10+ for bank commands. PDF builds need Bash, SymPy 1.12+, a supported
LaTeX engine and Poppler. Windows should use MSYS2 or Git Bash with Windows tools,
or a complete Linux environment in WSL; do not mix a WSL launcher with Windows
paths/toolchains. `MWS_PYTHON` accepts a single interpreter path with spaces.
`MWS_DATA_HOME` selects the same personal data directory from any project.
