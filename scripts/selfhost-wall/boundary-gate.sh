#!/usr/bin/env bash
# boundary-gate.sh -- rule 10 as a gate (docs/selfhost-priority.md; ADR 0366). BOOTSTRAP-TOOL.
#
#   scripts/selfhost-wall/boundary-gate.sh [CLASSPATH_FILE]
#
# EFFECTIVE union = bootstrap-boundary.sh's PRODUCT union + the src files flagged `;; bootstrap-tooling`
# that a launcher route nevertheless reaches: the host require closure (every reader branch) of every
# src/kotoba/compiler/nbb/*_cli.cljk -- the files bin/amu and bin/kotoba hand to nbb -- computed by
# reach-minimal.py --full --host over the launcher's locked classpath. A flag on a reachable file does
# not take it off the product path, so it is counted back; that is what makes the flag a measured
# claim rather than a label. Each such file is listed.
# PASS needs both of:
#   1. EFFECTIVE union                        <= UNION_CEIL   (default 55, recorded by ADR 0366)
#   2. nbb-only entry points (*_cli.cljk)     <= ENTRY_CEIL   (default 16)
# A ceiling only moves down: lower it in the same commit that lowers the count.
#
# CLASSPATH_FILE: a file holding the nbb classpath (colon separated). Default: the cache bin/amu
# publishes in the temp directory (sha256 of deps.edn, NUL, the gitlibs root, NUL, no alias). A
# missing classpath is a FAIL, not a skip.
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT" || exit 2
UNION_CEIL=${UNION_CEIL:-55}
ENTRY_CEIL=${ENTRY_CEIL:-16}
fail=0

out=$(bash scripts/selfhost-wall/bootstrap-boundary.sh)
union=$(printf '%s\n' "$out" | sed -n 's/^| distinct PRODUCT src files in any list above (the union) | \([0-9]*\) .*/\1/p')
entries=$(printf '%s\n' "$out" | sed -n 's/^| nbb-only entry points (\*_cli.cljk) | \([0-9]*\) .*/\1/p')
if [ -z "$union" ] || [ -z "$entries" ]; then echo "FAIL could not read the counts from bootstrap-boundary.sh"; exit 1; fi
if [ "$entries" -le "$ENTRY_CEIL" ]; then echo "PASS nbb entries $entries <= $ENTRY_CEIL"; else echo "FAIL nbb entries $entries > $ENTRY_CEIL"; fail=1; fi

cpf=${1:-}
if [ -z "$cpf" ]; then
  gl=${GITLIBS:-$HOME/.gitlibs}
  d=$( { cat deps.edn; printf '\0%s\0' "$gl"; } | shasum -a 256 | cut -c1-64)
  tmp=${TMPDIR:-/tmp}; tmp=${tmp%/}
  cpf=$tmp/amu-security-classpath-$d.txt
fi
if [ ! -s "$cpf" ]; then
  echo "FAIL no classpath file ($cpf): run any bin/amu compile once, or pass one"; exit 1
fi
K=${WALL_K:-/nonexistent}
work=$(mktemp -d "${TMPDIR:-/tmp}/bgate.XXXXXX"); trap 'rm -rf "$work"' EXIT
python3 scripts/selfhost-wall/reach-minimal.py "$ROOT" "$cpf" "$K" --full --host > "$work/reach" 2> "$work/reach.err" \
  || { echo "FAIL reach-minimal.py: $(tail -1 "$work/reach.err")"; exit 1; }
sed "s#^$ROOT/##" "$work/reach" | grep '^src/' | sort -u > "$work/reached"
find src -type f \( -name '*.cljk' -o -name '*.kotoba' -o -name '*.cljc' -o -name '*.cljs' \) | sort | while IFS= read -r f; do
  head -5 "$f" | grep -q ';; bootstrap-tooling' && echo "$f"
done > "$work/flagged"
bad=$(comm -12 "$work/flagged" "$work/reached")
nflag=$(wc -l < "$work/flagged" | tr -d ' '); nreach=$(wc -l < "$work/reached" | tr -d ' ')
nbad=0; [ -n "$bad" ] && nbad=$(printf '%s\n' $bad | wc -l | tr -d ' ')
echo "flagged src files: $nflag; reached from a launcher route: $nbad ($nreach src files reached; $(tail -1 "$work/reach.err"))"
[ -n "$bad" ] && printf '  flagged but REACHED (counted as PRODUCT): %s\n' $bad
eff=$((union + nbad))
if [ "$eff" -le "$UNION_CEIL" ]; then echo "PASS effective union $eff (= $union + $nbad) <= $UNION_CEIL"; else echo "FAIL effective union $eff (= $union + $nbad) > $UNION_CEIL"; fail=1; fi
[ $fail -eq 0 ] && echo "boundary-gate: PASS" || echo "boundary-gate: FAIL"
exit $fail
