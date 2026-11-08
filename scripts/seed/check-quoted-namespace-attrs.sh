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
run_refusal unknown ':kotoba/export [main] :author "unrecognized"'

run_header() {
  local name="$1" header="$2" expected="$3"
  printf '(ns %s %s)\n(defn main [] :i64 7)\n' "$name" "$header" > "$out/$name.kotoba"
  if "$compiler" check "$out/$name.kotoba" --source-path "$out" > "$out/$name.out" 2>&1; then
    [[ "$expected" == ok ]] || { printf '%s unexpectedly accepted\n' "$name" >&2; return 1; }
  else
    [[ "$expected" == E6021 ]] && [[ "$(<"$out/$name.out")" == *E6021* ]] || return 1
  fi
}
run_header docfirst '"document" {:kotoba/export [main]} (:capabilities #{})' ok
run_header mapafter '(:export [main]) {:kotoba/capabilities #{}}' E6021
run_header maps ' {:kotoba/export [main]} {:kotoba/capabilities #{}}' E6021
run_header docafter '(:export [main]) "late doc"' E6021
run_header doubleschemas '{:kotoba/export [main] :kotoba/schemas {}} (:schemas {})' E6021
run_header doublecaps '{:kotoba/export [main] :kotoba/capabilities #{}} (:capabilities #{})' E6021
run_header doubleparams '{:kotoba/export [main] :kotoba/params [elem :i64]} (:params [elem :i64])' E6021
run_header doubleexport '{:kotoba/export [main]} (:export [main])' E6021
run_header duplicates '{:kotoba/export [main] :kotoba/schemas {} :kotoba/schemas {}}' E6021

# Compile and execute the same exported function through both surface forms.
# A meaning-changing control ensures this comparison is sensitive to behavior.
for variant in plain quoted changed; do
  mkdir "$out/$variant-project"
  attrs=':kotoba/export [main]'
  value=7
  if [[ "$variant" == quoted ]]; then attrs=':kotoba/export (quote [main])'; fi
  if [[ "$variant" == changed ]]; then value=8; fi
  printf '(ns demo {%s})\n(defn main [] :i64 %s)\n' "$attrs" "$value" > "$out/$variant-project/demo.kotoba"
  "$compiler" compile "$out/$variant-project/demo.kotoba" --source-path "$out/$variant-project" -o "$out/$variant-program" > "$out/$variant-build.out" 2>&1
  "$out/$variant-program" > "$out/$variant-result.out"
done
[[ "$(<"$out/plain-result.out")" == 7 ]]
cmp -s "$out/plain-result.out" "$out/quoted-result.out"
[[ "$(<"$out/changed-result.out")" == 8 ]]
! cmp -s "$out/plain-result.out" "$out/changed-result.out"
printf 'PASS_QUOTED_NAMESPACE_ATTRS\n'
