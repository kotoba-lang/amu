#!/usr/bin/env bash
# bootstrap-boundary.sh -- inventory of every place the PRODUCT path depends on
# nbb / Node / JVM, split from BOOTSTRAP-TOOL scaffolding.
#
# bash + grep + awk only. It needs no nbb, no node, no JVM and no Python, so it
# still runs on the day those are gone. It reads files; it changes nothing.
#
#   scripts/selfhost-wall/bootstrap-boundary.sh [--markdown] [ROOT]
#
# ROOT defaults to the repository root (two levels above this script).
# Default output is plain text; --markdown prints the body of
# docs/selfhost-bootstrap-boundary-<date>.md.
#
# Classes
#   PRODUCT         must be removed (replaced by Kotoba compiled by Amu) for 100%.
#                   bin/ launchers, nbb-only entry points, src/ modules whose Kotoba
#                   reading is nil/refusal, unguarded host-only requires in src/.
#   BOOTSTRAP-TOOL  dev scaffolding that may stay nbb/Node/Python until the
#                   self-built compiler exists: scripts/, test/, bench/, tools/,
#                   wall harness, differential scripts, native-image build,
#                   or any file whose first 5 lines contain
#                   ";; bootstrap-tooling" (the flag AGENTS.md requires for
#                   host-only code).
#
# Static approximation. Reader-conditional guarding is tracked by a small
# S-expression scanner (strings, ; comments, bracket depth, #?( / #?@( frames,
# key/value alternation). A host token inside a #?(:kotoba ...) arm is NOT guarded.

set -u
MD=0
ROOT=""
for a in "$@"; do
  case "$a" in
    --markdown) MD=1 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) ROOT="$a" ;;
  esac
done
if [ -z "$ROOT" ]; then
  ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
fi
cd "$ROOT" || exit 2

HOLLOW_DOC="docs/selfhost-real-vs-hollow-20261001.md"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/bbound.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

is_flagged() { head -5 "$1" 2>/dev/null | grep -q ';; bootstrap-tooling'; }

# ---------------------------------------------------------------- 1. launchers
: > "$TMP/launchers"
for f in bin/*; do
  [ -f "$f" ] || continue
  sh1=$(head -1 "$f")
  dep=""
  case "$sh1" in
    *nbb*) dep="nbb(shebang)" ;;
    *node*) dep="node(shebang)" ;;
  esac
  grep -qE 'require\("node:|spawnSync|nbb' "$f" && dep="${dep:+$dep+}host-calls"
  grep -qE 'python3|graal|native-image' "$f" && dep="${dep:+$dep+}python/graal"
  case "$(basename "$f")" in
    amu|amu.cmd|kotoba|kotoba-compiler) cls=PRODUCT ;;
    *) cls=BOOTSTRAP-TOOL ;;
  esac
  is_flagged "$f" && cls=BOOTSTRAP-TOOL
  [ -n "$dep" ] || dep="(delegates)"
  printf '%s\t%s\t%s\t%s lines\n' "$cls" "$f" "$dep" "$(wc -l < "$f" | tr -d ' ')" >> "$TMP/launchers"
done

# --------------------------------------------- 2. scan src/**/*.cljk (and .kotoba)
# per file: path  unguarded_host  guarded_host  kotoba_nil_forms  kotoba_arms  host_arms
cat > "$TMP/scan.awk" <<'AWK'
function ishost(t) {
  if (t ~ /^"node:/) return 1
  if (t ~ /^"(fs|path|os|child_process|crypto|url|util|process)"$/) return 1
  if (t ~ /^js\//) return 1
  if (t ~ /^java\./ || t ~ /^clojure\.java/) return 1
  if (t ~ /^nbb\.core/ || t == ":import") return 1
  return 0
}
function guarded(   i) {
  for (i = 1; i <= nf; i++) if (fb[i] != "" && fb[i] != ":kotoba") return 1
  return 0
}
function atom_done(tok,   i) {
  if (tok == "") return
  if (tok ~ /^#\?/) return
  if (ishost(tok)) { if (guarded()) gh++; else uh++ }
  if (nf > 0 && depth == fd[nf]) {
    if (fn[nf] % 2 == 0) {
      fb[nf] = tok
      if (tok == ":kotoba") { ka++; kw[nf] = 1 } else if (tok ~ /^:(cljs|clj|default|cljr)$/) ha++
    } else if (kw[nf] == 1) {
      if (tok == "nil") kn++
      kw[nf] = 0
    }
    fn[nf]++
  }
}
function scan(text,   n, i, c, tok, instr, esc, d2) {
  n = length(text); tok = ""; instr = 0
  for (i = 1; i <= n; i++) {
    c = substr(text, i, 1)
    if (instr) {
      tok = tok c
      if (esc) esc = 0
      else if (c == "\\") esc = 1
      else if (c == "\"") { instr = 0; atom_done(tok); tok = "" }
      continue
    }
    if (c == ";") {
      atom_done(tok); tok = ""
      while (i < n && substr(text, i + 1, 1) != "\n") i++
      continue
    }
    if (c == "\"") { atom_done(tok); tok = c; instr = 1; continue }
    if (c == "\\") { tok = tok c substr(text, i + 1, 1); i++; continue }
    if (c ~ /[ \t\r\n,]/) { atom_done(tok); tok = ""; continue }
    if (c ~ /[\(\[\{]/) {
      atom_done(tok); tok = ""
      isrc = (c == "(" && i >= 3 && substr(text, i - 2, 2) == "#?") || (c == "(" && i >= 4 && substr(text, i - 3, 3) == "#?@")
      depth++
      if (isrc) { nf++; fd[nf] = depth; fn[nf] = 0; fb[nf] = ""; kw[nf] = 0 }
      continue
    }
    if (c ~ /[\)\]\}]/) {
      atom_done(tok); tok = ""
      if (nf > 0 && depth == fd[nf]) nf--
      depth--
      if (nf > 0 && depth == fd[nf]) {
        # a child form of the enclosing #?( finished
        if (fn[nf] % 2 == 1 && kw[nf] == 1) kw[nf] = 0
        fn[nf]++
      }
      continue
    }
    tok = tok c
  }
  atom_done(tok)
}
{ buf = buf $0 "\n" }
END { depth = 0; nf = 0; scan(buf); printf "%s\t%d\t%d\t%d\t%d\t%d\n", FILENAME, uh + 0, gh + 0, kn + 0, ka + 0, ha + 0 }
AWK

: > "$TMP/files"
find src -type f \( -name '*.cljk' -o -name '*.kotoba' -o -name '*.cljc' -o -name '*.cljs' \) 2>/dev/null | sort > "$TMP/files"
: > "$TMP/scan.tsv"
while IFS= read -r f; do
  awk -f "$TMP/scan.awk" "$f" >> "$TMP/scan.tsv"
done < "$TMP/files"

# --------------------------------------------------- 3. entry points (nbb-only)
: > "$TMP/entries"
while IFS=$'\t' read -r f uh gh kn ka ha; do
  base=$(basename "$f")
  kind=""
  case "$f" in
    src/kotoba/compiler/nbb/*_cli.cljk|src/kotoba/compiler/nbb/cli.cljk) kind="nbb entry (nbb/*_cli)" ;;
    *_cli.cljk) kind="cli entry (non-nbb twin or shared)" ;;
  esac
  [ -n "$kind" ] || continue
  cls=PRODUCT; is_flagged "$f" && cls=BOOTSTRAP-TOOL
  kreading="has-:kotoba-arm"; [ "$ka" -eq 0 ] && kreading="NO-:kotoba-arm"
  printf '%s\t%s\t%s\t%s\tunguarded-host=%s kotoba-nil=%s\n' "$cls" "$f" "$kind" "$kreading" "$uh" "$kn" >> "$TMP/entries"
done < "$TMP/scan.tsv"

# --------------------------------------------- 4. modules with nil/refusal reading
# (a) from the audit doc: HOLLOW / PARTIAL rows whose path resolves in this repo
# (b) computed here: files with #?(:kotoba nil ...) forms or no :kotoba arm
: > "$TMP/hollow_doc"
if [ -f "$HOLLOW_DOC" ]; then
  grep -E '^\| `' "$HOLLOW_DOC" | grep -E '\| (HOLLOW|PARTIAL)' | while IFS='|' read -r _ file cls _; do
    file=${file//\`/}; file=${file# }; file=${file% }
    cls=$(echo "$cls" | sed -E 's/^ +//; s/ .*//')
    repo=${file%% : *}; ns=${file#* : }
    printf '%s\t%s\t%s\n' "$cls" "$repo" "$ns"
  done > "$TMP/hollow_doc"
fi
: > "$TMP/hollow_here"
while IFS=$'\t' read -r cls repo ns; do
  case "$repo" in wt-A-amu-measure) ;; *) continue ;; esac
  p="src/$ns"
  [ -f "$p" ] || continue
  cl=PRODUCT; is_flagged "$p" && cl=BOOTSTRAP-TOOL
  printf '%s\t%s\t%s\n' "$cl" "$p" "audit:$cls" >> "$TMP/hollow_here"
done < "$TMP/hollow_doc"
awk -F'\t' '$4 > 0 || ($5 == 0 && $3 + $2 > 0) { printf "%s\t%s\t%s\n", "PRODUCT", $1, ($4 > 0 ? "kotoba-nil-forms=" $4 : "no-:kotoba-arm-with-host-refs") }' "$TMP/scan.tsv" > "$TMP/hollow_calc"
# drop flagged files from the computed list
: > "$TMP/hollow_calc2"
while IFS=$'\t' read -r cl p why; do is_flagged "$p" || printf '%s\t%s\t%s\n' "$cl" "$p" "$why" >> "$TMP/hollow_calc2"; done < "$TMP/hollow_calc"

# ---------------------------------------- 5. unguarded host-only requires/calls
awk -F'\t' '$2 > 0 { printf "%s\t%s\t%s\n", "PRODUCT", $1, "unguarded-host-tokens=" $2 " guarded=" $3 }' "$TMP/scan.tsv" > "$TMP/hostonly"
: > "$TMP/hostonly2"
while IFS=$'\t' read -r cl p why; do is_flagged "$p" && cl=BOOTSTRAP-TOOL; printf '%s\t%s\t%s\n' "$cl" "$p" "$why" >> "$TMP/hostonly2"; done < "$TMP/hostonly"

# ------------------------------------------- 6. runtime packaging / bootstrap deps
: > "$TMP/deps"
[ -f package.json ] && printf 'BOOTSTRAP-TOOL\tpackage.json\tnode package manifest (nbb pin, playwright; npm scripts run node/nbb)\n' >> "$TMP/deps"
[ -f nbb.edn ] && printf 'BOOTSTRAP-TOOL\tnbb.edn\tnbb classpath config (read only by nbb)\n' >> "$TMP/deps"
[ -f deps.edn ] && printf 'BOOTSTRAP-TOOL\tdeps.edn\tClojure CLI (JVM) deps; JVM compatibility route only\n' >> "$TMP/deps"
[ -d node_modules ] && printf 'BOOTSTRAP-TOOL\tnode_modules/\tinstalled nbb + playwright (not shipped)\n' >> "$TMP/deps"
[ -f bin/amu ] && printf 'PRODUCT\tbin/amu -> node + nbb\tlauncher resolves classpath and spawns nbb on src/kotoba/compiler/nbb/*_cli.cljk\n' >> "$TMP/deps"

# ----------------------------------------------- 7. bootstrap tooling by area
count_area() { # dir ext-regex
  [ -d "$1" ] || { echo 0; return; }
  find "$1" -type f 2>/dev/null | grep -Ec "$2"
}
tool_total=0
: > "$TMP/tools"
for d in scripts test tests bench tools fuzz; do
  [ -d "$d" ] || continue
  n=$(find "$d" -type f -not -path '*/node_modules/*' | wc -l | tr -d ' ')
  py=$(find "$d" -type f -name '*.py' | wc -l | tr -d ' ')
  mjs=$(find "$d" -type f \( -name '*.mjs' -o -name '*.js' \) | wc -l | tr -d ' ')
  cs=$(find "$d" -type f \( -name '*.cljs' -o -name '*.cljk' -o -name '*.cljc' -o -name '*.clj' \) | wc -l | tr -d ' ')
  sh=$(find "$d" -type f -name '*.sh' | wc -l | tr -d ' ')
  printf 'BOOTSTRAP-TOOL\t%s/\tfiles=%s py=%s mjs/js=%s clj*=%s sh=%s\n' "$d" "$n" "$py" "$mjs" "$cs" "$sh" >> "$TMP/tools"
  tool_total=$((tool_total + n))
done
wall_n=$(find scripts/selfhost-wall -type f 2>/dev/null | wc -l | tr -d ' ')
wall_py=$(find scripts/selfhost-wall -type f -name '*.py' 2>/dev/null | wc -l | tr -d ' ')
wall_cljs=$(find scripts/selfhost-wall -type f -name '*.cljs' 2>/dev/null | wc -l | tr -d ' ')
wall_sh=$(find scripts/selfhost-wall -type f -name '*.sh' 2>/dev/null | wc -l | tr -d ' ')

# ---------------------------------------------------------------- counts
n_src=$(wc -l < "$TMP/files" | tr -d ' ')
n_launch_prod=$(grep -c '^PRODUCT' "$TMP/launchers")
n_launch_boot=$(grep -c '^BOOTSTRAP-TOOL' "$TMP/launchers")
n_entry_prod=$(grep -c '^PRODUCT' "$TMP/entries")
n_entry_nok=$(awk -F'\t' '$1=="PRODUCT" && $4=="NO-:kotoba-arm"' "$TMP/entries" | wc -l | tr -d ' ')
n_hollow_doc=$(wc -l < "$TMP/hollow_here" | tr -d ' ')
n_hollow_calc=$(wc -l < "$TMP/hollow_calc2" | tr -d ' ')
n_host_files=$(grep -c '^PRODUCT' "$TMP/hostonly2")
n_host_tokens=$(awk -F'\t' '$2>0 {s+=$2} END{print s+0}' "$TMP/scan.tsv")
n_guard_tokens=$(awk -F'\t' '{s+=$3} END{print s+0}' "$TMP/scan.tsv")
n_nil_forms=$(awk -F'\t' '{s+=$4} END{print s+0}' "$TMP/scan.tsv")
n_files_nok=$(awk -F'\t' '$5==0' "$TMP/scan.tsv" | wc -l | tr -d ' ')
n_files_ok=$((n_src - n_files_nok))
# product files that need the nbb/node/JVM route to run (union of the sets above)
cat "$TMP/hollow_here" "$TMP/hollow_calc2" "$TMP/hostonly2" "$TMP/entries" 2>/dev/null \
  | awk -F'\t' '{ if ($1=="PRODUCT") { f = ($1=="PRODUCT" && $2 ~ /^src\//) ? $2 : $2; print f } }' | sort -u > "$TMP/union"
n_union=$(grep -c '^src/' "$TMP/union")

emit_list() { # file
  if [ ! -s "$1" ]; then echo "(none)"; return; fi
  awk -F'\t' -v md="$MD" '{ if (md) printf "- `%s` | %s | %s | %s\n", $2, $1, $3, $4; else printf "  %-15s %-62s %s %s\n", $1, $2, $3, $4 }' "$1"
}

if [ "$MD" -eq 1 ]; then
  H2='## '; H3='### '
else
  H2='== '; H3='-- '
fi

echo "${H2}Counts"
echo
echo "scanned root: $ROOT"
echo "src files scanned (.cljk/.kotoba/.cljc/.cljs): $n_src"
echo
printf '%s\n' \
"| area | PRODUCT | BOOTSTRAP-TOOL |" \
"|---|---|---|" \
"| launchers (bin/*) | $n_launch_prod | $n_launch_boot |" \
"| nbb-only entry points (*_cli.cljk) | $n_entry_prod ($n_entry_nok with no :kotoba arm) | 0 |" \
"| modules with a nil/refusal Kotoba reading, from the audit doc ($HOLLOW_DOC, HOLLOW+PARTIAL rows of this repo) | $n_hollow_doc | 0 |" \
"| modules with \`#?(:kotoba nil ...)\` forms or no :kotoba arm, computed from source | $n_hollow_calc | 0 |" \
"| src files with unguarded host tokens (node:*, js/*, java.*, :import, host requires) | $n_host_files ($n_host_tokens tokens; $n_guard_tokens more are guarded) | 0 |" \
"| src files with at least one :kotoba arm | $n_files_ok of $n_src | |" \
"| \`#?(:kotoba nil ...)\` forms in src | $n_nil_forms | |" \
"| distinct PRODUCT src files in any list above (the union) | $n_union | |" \
"| scripts/test/bench/tools files (bootstrap scaffolding) | | $tool_total |" \
"| of which scripts/selfhost-wall (wall harness; $wall_cljs .cljs, $wall_py .py, $wall_sh .sh) | | $wall_n |"
echo
echo "${H2}1. Launchers (bin/*)"
echo
emit_list "$TMP/launchers"
echo
echo "${H2}2. nbb-only entry points"
echo
emit_list "$TMP/entries"
echo
echo "${H2}3. Modules whose Kotoba reading is nil or refusal"
echo
echo "${H3}3a. From $HOLLOW_DOC (HOLLOW / PARTIAL, this repo)"
echo
emit_list "$TMP/hollow_here"
echo
echo "${H3}3b. Computed from source (#?(:kotoba nil ...) or no :kotoba arm with host tokens)"
echo
emit_list "$TMP/hollow_calc2"
echo
echo "${H2}4. Host-only tokens not guarded by #?(:cljs / :clj / :default)"
echo
emit_list "$TMP/hostonly2"
echo
echo "${H2}5. Packaging and dependency manifests"
echo
emit_list "$TMP/deps"
echo
echo "${H2}6. Bootstrap tooling (may stay until the self-built compiler exists)"
echo
emit_list "$TMP/tools"
echo
exit 0
