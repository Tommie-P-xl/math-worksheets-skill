#!/usr/bin/env bash
# compile.sh — Compile LaTeX with Tectonic, pdflatex, or XeLaTeX.
# Usage: compile.sh <input.tex> [output-dir]
#        MAX_PAGES=<n> to enforce a page budget on the compiled PDF (read from
#        the log's "Output written ... (N pages" line by check_log.py; same
#        env-var interface as OVERFULL_PT). build.sh sets role-appropriate
#        caps — ss 2 (SKILL.md's hard cap), ws 8 / ak 6 (sanity ceilings).
#
# Requirements: tectonic (brew install tectonic)
# Tectonic auto-downloads any missing LaTeX packages on first use.

set -euo pipefail

# MWS_LATEX_ENGINE=auto|tectonic|pdflatex|xelatex. Unicode/CJK documents
# prefer XeLaTeX when available; ordinary documents retain the original route.
ENGINE="${MWS_LATEX_ENGINE:-auto}"
case "$ENGINE" in auto|tectonic|pdflatex|xelatex) ;; *)
  echo "Error: MWS_LATEX_ENGINE must be auto, tectonic, pdflatex, or xelatex" >&2; exit 1 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TEX_FILE="${1:-}"
OUT_DIR="${2:-$(dirname "$TEX_FILE")}"

# Gate the real TeX log before declaring success: an engine can exit 0 while
# the PDF prints '??' for a broken \ref, silently drops glyphs ("Missing
# character"), or runs text 10cm off the page (Overfull \hbox). Those signals
# exist ONLY in the .log — tectonic even deletes it without --keep-logs — so
# check_log.py scans the kept log (same format from both engines) and this
# script refuses to ship on failure. The outdir is a deliverable, so the log
# is always removed afterwards, pass or fail (faults are echoed first).
scan_log() {
  local LOGFILE="$1"
  if [[ ! -f "$LOGFILE" ]]; then
    echo "⚠ expected LaTeX log not found at $LOGFILE — log hygiene not checked" >&2
    echo "  (tectonic too old for --keep-logs? upgrade tectonic)" >&2
    return 0
  fi
  local PY
  PY="${MWS_PYTHON:-$(command -v python3 2>/dev/null || true)}"
  if [[ -z "$PY" ]]; then
    echo "⚠ python3 not found — log hygiene not checked (install python3;" >&2
    echo "  it is already required for answer verification, see SKILL.md)" >&2
    rm -f "$LOGFILE"
    return 0
  fi
  # MAX_PAGES rides through as --max-pages: the page count lives ONLY in the
  # log too, so the budget gate belongs to the same scan (and check_log is
  # LOUD — exit 2 — if the cap is set but the log hides the count).
  if ! "$PY" "$SCRIPT_DIR/check_log.py" "$LOGFILE" ${MAX_PAGES:+--max-pages "$MAX_PAGES"}; then
    # keep the log on failure: the gate names line numbers, and deleting the
    # file it names forces a manual recompile just to read the fault
    echo "❌ The PDF compiled but would ship broken — fix the log faults above and recompile." >&2
    echo "   (full log kept at $LOGFILE)" >&2
    exit 1
  fi
  rm -f "$LOGFILE"
}

if [[ -z "$TEX_FILE" ]]; then
  echo "Usage: compile.sh <input.tex> [output-dir]" >&2
  exit 1
fi

if [[ ! -f "$TEX_FILE" ]]; then
  echo "Error: File not found: $TEX_FILE" >&2
  exit 1
fi

# Locate a LaTeX engine: tectonic preferred (auto-downloads packages);
# pdflatex fallback for systems with a classic TeX install (packages must
# already be present — needs texlive-latex-base + texlive-pictures or similar).
TECTONIC=""
for candidate in "$(command -v tectonic 2>/dev/null || true)" \
                 "/opt/homebrew/bin/tectonic" \
                 "/usr/local/bin/tectonic" \
                 "${HOME}/.cargo/bin/tectonic" \
                 "/home/linuxbrew/.linuxbrew/bin/tectonic"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    TECTONIC="$candidate"
    break
  fi
done
PDFLATEX="$(command -v pdflatex 2>/dev/null || true)"
XELATEX="$(command -v xelatex 2>/dev/null || true)"
CLASSIC_NAME=pdflatex
if [[ "$ENGINE" == xelatex ]] || { [[ "$ENGINE" == auto ]] && grep -Eq 'xeCJK|ctex|fontspec|setCJK' "$TEX_FILE"; }; then
  if [[ -n "$XELATEX" ]]; then
    PDFLATEX="$XELATEX"; CLASSIC_NAME=xelatex; TECTONIC=""
  elif [[ "$ENGINE" == xelatex || -z "$TECTONIC" ]]; then
    echo "Error: this Unicode/CJK document needs xelatex (or Tectonic in auto mode). Install XeLaTeX and CJK fonts." >&2; exit 1
  fi
elif [[ "$ENGINE" == pdflatex ]]; then
  TECTONIC=""
elif [[ "$ENGINE" == tectonic ]]; then
  PDFLATEX=""
  [[ -n "$TECTONIC" ]] || { echo 'Error: requested tectonic is unavailable' >&2; exit 1; }
fi

if [[ -z "$TECTONIC" && -z "$PDFLATEX" ]]; then
  echo "Error: no LaTeX engine found. Install tectonic (brew/cargo install tectonic)" >&2
  echo "or a TeX distribution providing pdflatex." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

# ── Stage shipped templates beside the target ─────────────────────────────────
# Generated documents \input the shipped templates (templates/*.tex) instead of
# re-transcribing the preamble each run. Neither engine knows about $SKILL_DIR:
# tectonic resolves \input against the source file's directory, pdflatex
# (kpathsea) against the process cwd. Copying the templates next to the .tex
# satisfies both, so a /tmp compile just works.
TEX_DIR="$(cd "$(dirname "$TEX_FILE")" && pwd)"
TPL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/templates"
if grep -qE '\\input\{(worksheet-preamble|figure-macros)(\.tex)?\}' "$TEX_FILE"; then
  if [[ ! -d "$TPL_DIR" ]]; then
    echo "Error: $(basename "$TEX_FILE") \\inputs a shipped template, but" >&2
    echo "$TPL_DIR does not exist (partial checkout?). Restore the skill's" >&2
    echo "templates/ directory, or inline the preamble following" >&2
    echo "references/latex-templates.md." >&2
    exit 1
  fi
  # skip the copy when compiling inside templates/ itself (cp same-file error)
  if [[ "$TPL_DIR" != "$TEX_DIR" ]]; then
    cp -f "$TPL_DIR"/*.tex "$TEX_DIR/"
  fi
fi

SELECTED_ENGINE="$CLASSIC_NAME"
[[ -z "$TECTONIC" ]] || SELECTED_ENGINE=tectonic
echo "Compiling: $(basename "$TEX_FILE") → $OUT_DIR/ (engine: $SELECTED_ENGINE)"
if [[ -n "$TECTONIC" ]]; then
  "$TECTONIC" "$TEX_FILE" --outdir "$OUT_DIR" --keep-logs 2>&1 | grep -v "^note: downloading"
  # tectonic reruns internally until stable, so the kept log is the FINAL
  # pass — valid \ref documents scan clean, real drift scans dirty
  scan_log "${OUT_DIR}/$(basename "${TEX_FILE%.tex}").log"
else
  LOG="$(mktemp)"
  # Run pdflatex FROM the source's directory: kpathsea resolves \input against
  # the process cwd, so a staged template beside the .tex would be invisible
  # when compile.sh is invoked from anywhere else. (tectonic resolves against
  # the input file's directory and needs no such help.)
  OUT_DIR_ABS="$(cd "$OUT_DIR" && pwd)"
  pdflatex_pass() {
    (cd "$TEX_DIR" && "$PDFLATEX" -interaction=nonstopmode -halt-on-error \
      -output-directory "$OUT_DIR_ABS" "$(basename "$TEX_FILE")") > "$LOG" 2>&1
  }
  if ! pdflatex_pass; then
    echo "$CLASSIC_NAME failed — last lines of log:" >&2
    tail -25 "$LOG" >&2
    if grep -q "\.sty' not found" "$LOG"; then
      echo "Hint: classic TeX engines need installed packages — install texlive-latex-extra" >&2
      echo "(plus texlive-pictures for TikZ/pgfplots) or use tectonic instead." >&2
    fi
    rm -f "$LOG"
    exit 1
  fi
  rm -f "$LOG"
  JOB="$(basename "${TEX_FILE%.tex}")"
  # \ref numbers resolve from the .aux of a PREVIOUS pass, and the aux is
  # deleted below — so a single pass always logs a valid \ref as undefined.
  # Rerun once, exactly when the log says references are unresolved, so the
  # scan below fails only on genuine \ref/\label drift.
  if grep -qE 'Rerun to get cross-references|There were undefined references' \
       "${OUT_DIR}/${JOB}.log" 2>/dev/null; then
    pdflatex_pass || true   # pass 1 compiled; the scan + PDF check still gate
  fi
  scan_log "${OUT_DIR}/${JOB}.log"
  # pdflatex (unlike tectonic) drops .aux next to the PDF — the output
  # directory is a deliverable, keep only the PDF
  rm -f "${OUT_DIR}/${JOB}.aux" "${OUT_DIR}/${JOB}.out"
fi

PDF="${OUT_DIR}/$(basename "${TEX_FILE%.tex}").pdf"
if [[ -f "$PDF" ]]; then
  echo "✅ PDF ready: $PDF"
  echo "$PDF"
else
  echo "❌ Compilation failed — check LaTeX errors above" >&2
  exit 1
fi
