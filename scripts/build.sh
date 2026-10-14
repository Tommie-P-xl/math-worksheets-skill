#!/usr/bin/env bash
# build.sh <verify_STEM.json> [--outdir DIR] [--worksheet-only]
#   [--no-study-guide] [--reproduce --sources FILE] [--study-guide-only]
# Reproduction defaults to worksheet + concise answer key; no study guide.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CHECKS="$SCRIPT_DIR/checks"
JSON=""; OUT="$HOME/Documents/Worksheets"; WS_ONLY=0; NO_SS=0; SS_ONLY=0
REPRODUCE=0; SOURCES=""
WS_OVERRIDE=""; AK_OVERRIDE=""; SS_OVERRIDE=""; VSS_OVERRIDE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) head -4 "${BASH_SOURCE[0]}"; exit 0 ;;
    --outdir) OUT="${2:?missing output directory}"; shift 2 ;;
    --worksheet-only) WS_ONLY=1; NO_SS=1; shift ;;
    --no-study-guide) NO_SS=1; shift ;;
    --study-guide-only) SS_ONLY=1; shift ;;
    --reproduce) REPRODUCE=1; NO_SS=1; shift ;;
    --sources) SOURCES="${2:?missing source manifest}"; shift 2 ;;
    --ws) WS_OVERRIDE="${2:?missing worksheet}"; shift 2 ;;
    --ak) AK_OVERRIDE="${2:?missing answer key}"; shift 2 ;;
    --ss) SS_OVERRIDE="${2:?missing study guide}"; shift 2 ;;
    --verify-ss) VSS_OVERRIDE="${2:?missing guide JSON}"; shift 2 ;;
    -*) echo "Unknown option: $1" >&2; exit 1 ;;
    *) [[ -z "$JSON" ]] || { echo 'Only one verification JSON is allowed' >&2; exit 1; }; JSON="$1"; shift ;;
  esac
done
[[ -f "$JSON" ]] || { echo 'Provide verify_STEM.json' >&2; exit 1; }
[[ "$SS_ONLY" -eq 0 || "$NO_SS" -eq 0 ]] || { echo 'Conflicting output modes' >&2; exit 1; }
[[ -z "$SOURCES" || "$REPRODUCE" -eq 1 ]] || { echo '--sources requires --reproduce' >&2; exit 1; }
BASE="$(basename "$JSON")"; STEM="${BASE#verify_}"; STEM="${STEM%.json}"
[[ "$BASE" == verify_*.json ]] || { echo 'Expected verify_STEM.json' >&2; exit 1; }
DIR="$(cd "$(dirname "$JSON")" && pwd)"; JSON="$DIR/$BASE"
if [[ "$SS_ONLY" -eq 1 ]]; then
  [[ "$STEM" == ss_* ]] || { echo 'Guide-only expects verify_ss_STEM.json' >&2; exit 1; }
  STEM="${STEM#ss_}"; VSS_OVERRIDE="$JSON"
elif [[ "$STEM" == ss_* ]]; then
  echo 'Pass worksheet JSON, or use --study-guide-only' >&2; exit 1
fi
source "$SCRIPT_DIR/find_python.sh"
PY="$(find_sympy_python)" || exit 1
export MWS_PYTHON="$PY"
export PYTHONUTF8=1
GATE=""; MANUAL=0; PDFS=()
fail() { echo "BUILD FAILED — gate: $GATE" >&2; exit 1; }
run() {
  GATE="$1"; shift; echo "── $GATE"
  "$@" || fail
}
verify() {
  GATE="$1"; echo "── $GATE"
  "$PY" "$SCRIPT_DIR/verify.py" "$2"; local rc=$?
  case "$rc" in 0) ;; 2) MANUAL=1 ;; *) fail ;; esac
}
discover() {
  local role="$1" override="$2" p f matches=()
  if [[ -n "$override" ]]; then
    [[ -f "$override" ]] || { echo "Missing $role: $override" >&2; return 1; }
    printf '%s\n' "$override"; return
  fi
  for p in "$role" "${role}S" "${role}C" "${role}X"; do
    for f in "$DIR/${p}_${STEM}.tex" "$DIR"/*"_${p}_${STEM}.tex"; do
      [[ -f "$f" ]] && matches+=("$f")
    done
  done
  [[ ${#matches[@]} -eq 1 ]] || { echo "Need exactly one ${role}_${STEM}.tex; found ${#matches[@]}" >&2; return 1; }
  printf '%s\n' "${matches[0]}"
}
GATE=discover; WS=""; AK=""; SS=""; VSS=""
if [[ "$SS_ONLY" -eq 0 ]]; then
  WS="$(discover ws "$WS_OVERRIDE")" || fail
  [[ "$WS_ONLY" -eq 1 ]] || { AK="$(discover ak "$AK_OVERRIDE")" || fail; }
fi
if [[ "$NO_SS" -eq 0 ]]; then
  SS="$(discover ss "$SS_OVERRIDE")" || fail
  VSS="${VSS_OVERRIDE:-$DIR/verify_ss_${STEM}.json}"
  [[ -f "$VSS" ]] || fail
fi
PROSE_ARGS=(); LAYOUT_ARGS=(); FIGS=""; META=""
if [[ "$REPRODUCE" -eq 1 ]]; then
  SOURCES="${SOURCES:-$DIR/sources_${STEM}.json}"
  run sources-ws "$PY" "$CHECKS/check_sources.py" "$WS" "$SOURCES"
  if [[ -n "$AK" ]]; then
    run sources-ak "$PY" "$CHECKS/check_sources.py" "$AK" "$SOURCES" --role answer-key
  fi
  PROSE_ARGS=(--sources "$SOURCES")
  LAYOUT_ARGS=(--sources "$SOURCES")
  # Opaque assets are reviewed visually, never represented as CAS-verified.
  if "$PY" -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1], encoding="utf-8")).get("assets") else 1)' "$SOURCES"; then MANUAL=1; fi
fi
[[ -z "$WS" ]] || run template-ws "$PY" "$CHECKS/check_template_use.py" "$WS"
[[ -z "$AK" ]] || run template-ak "$PY" "$CHECKS/check_template_use.py" "$AK"
[[ -z "$SS" ]] || run template-ss "$PY" "$CHECKS/check_template_use.py" "$SS"
[[ "$SS_ONLY" -eq 1 ]] || verify verify-ws "$JSON"
[[ -z "$VSS" ]] || verify verify-ss "$VSS"
if [[ -n "$WS" && -n "$SS" ]]; then
  run coverage-ss "$PY" "$CHECKS/check_ss_coverage.py" "$JSON" "$VSS"
fi
if [[ -n "$WS" ]]; then
  FACETS=("$WS" "$JSON"); [[ -z "$VSS" ]] || FACETS+=("$VSS")
  run facet-coverage "$PY" "$CHECKS/check_facet_coverage.py" "${FACETS[@]}"
  if grep -Eq '"type"[[:space:]]*:[[:space:]]*"triangle"|"figure"[[:space:]]*:' "$JSON"; then
    run render-figures "$PY" "$SCRIPT_DIR/render_figures.py" "$JSON"
    FIGS="$DIR/figs_${STEM}.tex"; PROSE_ARGS+=(--figs "$FIGS"); LAYOUT_ARGS+=(--figs "$FIGS")
  fi
  if grep -Eq '\\probmeta\{|\\probpts\{' "$WS"; then
    run render-meta "$PY" "$SCRIPT_DIR/render_meta.py" "$JSON"
    META="$DIR/meta_${STEM}.tex"; PROSE_ARGS+=(--meta "$META")
  fi
  [[ -z "$AK" ]] || run quick-answers "$PY" "$SCRIPT_DIR/render_quick_answers.py" "$JSON" "$AK" --ws="$WS"
  run layout-ws "$PY" "$CHECKS/check_layout.py" "$WS" "${LAYOUT_ARGS[@]}"
  run answer-line-ws "$PY" "$CHECKS/check_answer_line.py" "$WS" "$JSON"
  run answer-slots-ws "$PY" "$CHECKS/check_answer_slots.py" "$WS" "$JSON"
  run prose-ws "$PY" "$CHECKS/check_prose_consistency.py" "$WS" "$JSON" "${PROSE_ARGS[@]}"
fi
if [[ -n "$AK" ]]; then
  run answer-key-ak "$PY" "$CHECKS/check_answer_key.py" "$AK" "$JSON"
fi
if [[ -n "$SS" ]]; then
  run answer-key-ss "$PY" "$CHECKS/check_answer_key.py" "$SS" "$VSS"
  run ss-structure "$PY" "$CHECKS/check_study_guide.py" "$SS" "$VSS"
  run prose-ss "$PY" "$CHECKS/check_prose_consistency.py" "$SS" "$VSS"
fi
compile() {
  local role="$1" tex="$2" cap="$3"
  run "compile-$role" env MAX_PAGES="$cap" bash "$SCRIPT_DIR/compile.sh" "$tex" "$OUT"
  PDFS+=("$OUT/$(basename "${tex%.tex}").pdf")
}
if [[ -n "$WS" ]]; then
  GATE=page-budget-ws
  CAP="$("$PY" "$SCRIPT_DIR/page_budget.py" "$JSON" --from-tex "$WS" --max-pages)" || fail
  compile ws "$WS" "$CAP"
fi
if [[ -n "$AK" ]]; then
  GATE=page-budget-ak
  CAP="$("$PY" "$SCRIPT_DIR/page_budget.py" "$JSON" --doc ak --from-tex "$AK" --max-pages)" || fail
  compile ak "$AK" "$CAP"
fi
if [[ -n "$SS" ]]; then
  CAP="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8")).get("pages",2))' "$VSS")" || fail
  compile ss "$SS" "$CAP"
fi
run overprint "$PY" "$CHECKS/check_overprint.py" --quiet "${PDFS[@]}"
printf 'PDF: %s\n' "${PDFS[@]}"
if [[ "$MANUAL" -eq 1 ]]; then
  echo 'BUILD PASSED — manual review items / visually reviewed external assets (exit 2)'; exit 2
fi
echo 'BUILD PASSED — all gates green'
