#!/usr/bin/env bash
# Exercise native project namespace attributes; output directory must be new.
set -euo pipefail
compiler="${1:?native Amu CLI path required}"
out="${2:?new output directory required}"
mkdir "$out"
run_ok() {
  local name="$1" attrs="$2"
  printf '(ns %s {%s})\n(defn main [] :i64 7)\n' "$name" "$attrs" > "$out/$name.kotoba"
  "$compiler" check "$out/$name.kotoba" --source-path "$out" > "$out/$name.out" 2>&1
  [[ "$(cat "$out/$name.out")" == 'ok' ]]
}
run_refusal() {
  local name="$1" attrs="$2" code="${3:-E6021}"
  printf '(ns %s {%s})\n(defn main [] :i64 7)\n' "$name" "$attrs" > "$out/$name.kotoba"
  if "$compiler" check "$out/$name.kotoba" --source-path "$out" > "$out/$name.out" 2>&1; then
    printf '%s unexpectedly accepted\n' "$name" >&2; return 1
  fi
  [[ "$(<"$out/$name.out")" == *"$code"* ]]
}
run_ok plain ':kotoba/export [main] :kotoba/capabilities #{} :kotoba/schemas {} :kotoba/params [elem :i64]'
run_ok quoted ':kotoba/export (quote [main]) :kotoba/capabilities (quote #{}) :kotoba/schemas (quote {}) :kotoba/params (quote [elem :i64])'
run_refusal noarg ':kotoba/export (quote)'
run_refusal multiarg ':kotoba/export (quote [main] [other])'
run_refusal nested ':kotoba/export (quote (quote [main]))'
run_refusal call ':kotoba/export (identity [main])'
run_refusal capcall ':kotoba/export [main] :kotoba/capabilities (identity #{})'
run_refusal schemacall ':kotoba/export [main] :kotoba/schemas (identity {})'
run_refusal paramscall ':kotoba/export [main] :kotoba/params (identity [elem :i64])' E6023
printf 'PASS_QUOTED_NAMESPACE_ATTRS\n'
