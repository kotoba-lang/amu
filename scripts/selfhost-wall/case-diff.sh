#!/bin/zsh
# case-diff.sh [--native|--wasm|--interp] [--limit N] [--batch-lines B]
# Differential for kotoba.string.case/upper-case-root (lang/compat, the Kotoba reading) against the host's
# String.prototype.toUpperCase, over the corpus: every Unicode scalar value one per line (surrogates excluded), then
# folding-heavy words. The Kotoba side runs as COMPILED code through guest-run.sh (default native). The host side is node
# (bootstrap reference: it is only the oracle). Prints agree/total and cases per second for the mode that ran.
# Env: as guest-run.sh.
HERE="$(cd "$(dirname "$0")" && pwd)"
mode=--native; limit=1114111; batch=2000
while [ $# -gt 0 ]; do case $1 in
  --native|--wasm|--interp|--native-only|--wasm-only) mode=$1;;
  --limit) limit=$2; shift;; --batch-lines) batch=$2; shift;; esac; shift; done
work=$(mktemp -d /tmp/case-diff.XXXXXX); trap 'rm -rf $work' EXIT
node -e '
const n = +process.argv[1], out = [];
for (let c = 0; c <= 0x10ffff && out.length < n; c++) { if (c === 10 || (c >= 0xd800 && c <= 0xdfff)) continue; out.push(String.fromCodePoint(c)); }
for (const w of ["straße", "ǆ", "ŉ", "ΐ", "ﬃ", "İ", "ı", "ǰ", "ᾳ", "ὒ"]) if (out.length < n) out.push(w);
process.stdout.write(out.join("\n") + "\n");' $limit > $work/corpus.txt
total=$(wc -l < $work/corpus.txt)
split -l $batch $work/corpus.txt $work/part.
# one compile/resolve up front, then the batches reuse the product without re-scanning the sources
$HERE/guest-run.sh $mode --resolve $HERE/guests/case.cljk up > $work/resolved 2>$work/resolve.err || { cat $work/resolve.err >&2; exit 3; }
used=$(cat $work/resolved); cat $work/resolve.err >&2
now() { node -e 'console.log(Date.now()/1000)'; }
t0=$(now)
bad=0
for p in $work/part.*; do
  GUEST_NOFRESH=1 $HERE/guest-run.sh $mode $HERE/guests/case.cljk up < $p > $p.got 2>/dev/null || { echo "case-diff: guest failed on $(basename $p)"; bad=$((bad+1000000)); }
  node -e 'process.stdout.write(require("fs").readFileSync(process.argv[1],"utf8").toUpperCase())' $p > $p.want
  cmp -s $p.got $p.want || { n=$(diff $p.got $p.want | grep -c '^<'); bad=$((bad+n)); diff $p.got $p.want | head -4; }
done
t1=$(now)
awk -v t=$total -v b=$bad -v a=$t0 -v z=$t1 -v m=$used 'BEGIN { s=z-a; printf "mode=%s agree=%d/%d seconds=%.2f cases/second=%.0f\n", m, t-b, t, s, t/s }'
[ $bad -eq 0 ]
