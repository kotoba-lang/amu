#!/bin/zsh
# scripts/seed/g2.sh [seed.bin [offset]] -- gate G2 on native code: every seed/tests/corpus program compiled by the
# seed (default build/seed/seed-0.bin), its first export run by the C loader (arity 0), must give the same result as
# stage-0 (seed/tests/unit/30-lower-corpus.oracle: `<stem> <result>` | `<stem> trap` | `<stem> refused`).
# A program refused by the seed's front end is reported as `front` (21-check's refusal text). BOOTSTRAP-TOOL (zsh).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
bin=${1:-$SEED_BUILD/seed-0.bin}; off=${2:-$(cat ${bin%.bin}.offset)}
R=$SEED_REPO; O=$R/seed/tests/unit/30-lower-corpus.oracle
W=$SEED_BUILD/g2-${bin:t:r}; mkdir -p $W
L=$(seed_loader) || exit 2
n=0; ok=0; fe=0; bad=0
for p in $R/seed/tests/corpus/*.kotoba; do
  stem=${p:t:r}; n=$((n+1))
  want=$(grep "^$stem " $O | cut -d' ' -f2)
  sym=$(sed -n 's/.*(:export \[\([^] ]*\).*/\1/p' $p | head -1)
  if ! zsh $R/scripts/seed/seed-cc.sh compile $bin $off $p $W/$stem.kseed 2> $W/$stem.err; then
    fe=$((fe+1)); echo "front $stem stage-0=$want seed: $(head -1 $W/$stem.err)"; continue; fi
  x=$(zsh $R/scripts/seed/seed-cc.sh extract $W/$stem.kseed $sym $W/$stem.bin) || { bad=$((bad+1)); echo "BAD   $stem extract: $x"; continue; }
  o=$(echo "$x" | sed -n 's/.*:offset \([0-9]*\).*/\1/p')
  got=$(cd $W; KEXE_CPU_SECONDS=20 KEXE_WALL_SECONDS=20 $L $W/$stem.bin $o 0 aarch64 - 2> $W/$stem.run.err | tail -1)
  grep -q KEXE_TRAP $W/$stem.run.err && got=trap
  if [ "$got" = "$want" ]; then ok=$((ok+1)); else bad=$((bad+1)); echo "BAD   $stem stage-0=$want seed=$got $(head -c 100 $W/$stem.run.err | tr '\n' ' ')"; fi
done
echo "G2: $ok/$n equal to stage-0, $fe refused by the seed front end, $bad different"
[ $bad -eq 0 ]
