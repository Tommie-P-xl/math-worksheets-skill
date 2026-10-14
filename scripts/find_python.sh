# find_python.sh — single source of truth for "which python runs the sympy
# tools". Sourced (not executed) by run_verify.sh and build.sh so every
# entry point resolves the interpreter identically.
#
# WHY not just `command -v python3`: machines routinely carry several pythons
# and the first one found often lacks sympy. The old finder took the first
# EXECUTABLE candidate and then gave up (audit D1b: it chose Homebrew's
# python3, printed "pip3 install sympy", and never tried /usr/bin/python3,
# which had sympy — worse, that pip3 belonged to a third interpreter, so the
# printed fix would not even have fixed it). This finder prefers the first
# candidate that can actually `import sympy`.
#
# MWS_PYTHON_CANDIDATES (space-separated paths) REPLACES the built-in list:
# users pin an interpreter with it, and the test suite uses it to prove both
# directions (a sympy-less python is skipped; no sympy anywhere fails with
# the exact install command for the interpreter that exists).

find_sympy_python() {
  local candidates=() tried=() first_existing="" p repo_root
  if [[ -n "${MWS_PYTHON:-}" ]]; then
    candidates=("$MWS_PYTHON")
  elif [[ -n "${MWS_PYTHON_CANDIDATES:-}" ]]; then
    read -r -a candidates <<< "$MWS_PYTHON_CANDIDATES"
  else
    repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    candidates=(
      "$repo_root/.venv/bin/python3"
      "$repo_root/.venv/Scripts/python.exe"
      "$(command -v python3 2>/dev/null || true)"
      "$(command -v python 2>/dev/null || true)"
      "/opt/homebrew/bin/python3"
      "/usr/local/bin/python3"
      "/usr/bin/python3"
    )
  fi

  for p in "${candidates[@]}"; do
    [[ -n "$p" && -x "$p" ]] || continue
    [[ -z "$first_existing" ]] && first_existing="$p"
    tried+=("$p")
    if "$p" -c "import sympy" 2>/dev/null; then
      echo "$p"
      return 0
    fi
  done

  # Teach the fix: name every python tried, and give the install command for
  # a SPECIFIC interpreter — bare `pip3` may belong to a different python.
  if [[ -n "$first_existing" ]]; then
    echo "Error: no python3 with sympy found. Tried:" >&2
    printf '  %s\n' "${tried[@]}" >&2
    echo "Fix: \"$first_existing\" -m pip install sympy" >&2
    echo "(or point MWS_PYTHON_CANDIDATES at a python that has sympy)" >&2
  else
    echo "Error: python3 not found. Install Python 3 to use verification." >&2
  fi
  return 1
}
