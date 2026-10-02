#!/bin/zsh
# hashcons-ab.sh: A/B of the loader's pair hash-consing (KEXE_HASHCONS, docs/selfhost-memory-plan-20261002.md) on one
# native guest. Runs the guest's code twice on the same input, off and on, and prints the arena high-water marks of
# each and whether the two outputs are byte-identical (they must be: hash-consing is unobservable by design).
#
#   hashcons-ab.sh <guest.native.bin> <input>       (the .native.offset file next to the .bin, as guest-run.sh leaves it)
#
# Env: AB_LOADER (default: tools/kexe_loader.c built into $TMPDIR), KEXE_HASHCONS value for the B run (default 1),
#      GUEST_POOL / GUEST_PAIRS / GUEST_VECTORS / GUEST_VECTOR_ITEMS as in guest-run.sh. BOOTSTRAP-TOOL (zsh).
AMU=${0:A:h:h:h}
bin=${1:?usage: hashcons-ab.sh <guest.native.bin> <input>}; input=${2:?input}
off=$(cat ${bin%.bin}.offset)
loader=${AB_LOADER:-${TMPDIR:-/tmp}/kexe-loader-ab}
if [ -z "$AB_LOADER" ] && { [ ! -x $loader ] || [ $AMU/tools/kexe_loader.c -nt $loader ]; }; then
  cc $AMU/tools/kexe_loader.c -std=c11 -O2 -o $loader || exit 2
fi
out=$(mktemp -d)
for side in off on; do
  if [ $side = on ]; then hc=${KEXE_HASHCONS:-1}; else hc=0; fi
  KEXE_HASHCONS=$hc KEXE_ARENA_USE=1 KEXE_COMMAND=1 KEXE_STRING_POOL=${GUEST_POOL:-268435456} \
    KEXE_PAIRS=${GUEST_PAIRS:-33554432} KEXE_VECTORS=${GUEST_VECTORS:-4194304} \
    KEXE_VECTOR_ITEMS=${GUEST_VECTOR_ITEMS:-134217728} KEXE_CPU_SECONDS=600 KEXE_WALL_SECONDS=600 \
    /usr/bin/time -p $loader $bin $off 0 aarch64 ${GUEST_GRANT:-3,37,41} < $input > $out/$side.out 2> $out/$side.err
  echo "$side: $(grep -o ':pairs [0-9]*\|:vectors [0-9]*\|:vector-items [0-9]*\|:heap-bytes [0-9]*' $out/$side.err | tr '\n' ' ')$(grep -o 'KEXE_HASHCONS {.*}' $out/$side.err) $(grep '^user' $out/$side.err)"
done
if cmp -s $out/off.out $out/on.out; then echo "outputs identical ($(wc -c < $out/on.out | tr -d ' ') bytes)"; rm -rf $out; exit 0; fi
echo "OUTPUTS DIFFER: $out"; exit 1
