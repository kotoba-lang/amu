#!/bin/zsh
# scripts/seed-backend/build-wrapper.sh [OUTDIR] -- BOOTSTRAP-TOOL (ADR 0365). Builds, in OUTDIR (default build/seed-backend):
#   classpath.txt   the closure bin/amu resolves from deps-lock.edn (its private cache in $TMPDIR, keyed like bin/amu's), with
#                   amu's src + resources first and the kotoba-verifier gitlib entries replaced by the worktree
#                   $SB_VERIFIER (default /private/tmp/wt-D-kotoba-verifier): the verifier with the emitter registry
#                   (kotoba-verifier ADR 0052). No pin moves.
#   seed            the packaged seed (scripts/seed/package.sh of $SB_SEED_BIN, default build/seedfix-g/seed-1.bin =
#                   be8898af, the r6c-kir rung's fixed point), scope = repo, OUTDIR, /private/tmp, /tmp
#   amu-seed        the Mach-O wrapper (amu-seed-wrapper.c) the qualification runner is given as --compiler
#   wrapper.info    sha256 of each, node version, the verifier worktree HEAD
emulate -L zsh
setopt pipefail errexit
R=${0:A:h:h:h}
O=${1:-$R/build/seed-backend}; O=${O:A}; mkdir -p $O
V=${SB_VERIFIER:-/private/tmp/wt-D-kotoba-verifier}
BIN=${SB_SEED_BIN:-$R/build/seedfix-g/seed-1.bin}
NODE=${SB_NODE:-$(command -v node)}
# bin/amu's own cache of the lock closure (securityClasspath: sha256(deps.edn \0 gitlibs \0 alias)); run bin/amu once to fill it
digest=$(cd $R && $NODE -e 'const c=require("crypto"),fs=require("fs"),os=require("os"),p=require("path");const g=p.resolve(process.env.GITLIBS||p.join(os.homedir(),".gitlibs"));process.stdout.write(c.createHash("sha256").update(fs.readFileSync("deps.edn")).update("\0").update(g).update("\0").update("").digest("hex"))')
cache=${TMPDIR:-/tmp}/amu-security-classpath-$digest.txt
[ -f $cache ] || { echo "build-wrapper: no lock classpath cache $cache; run 'bin/amu compile <any .kotoba> --target aarch64-macos --output /tmp/x.kexe' once" >&2; exit 2; }
grep -q 'kotoba-verifier/[0-9a-f]*/src' $cache || { echo "build-wrapper: the lock closure has no kotoba-verifier entry" >&2; exit 2; }
{ echo $R/src; echo $R/resources; tr ':' '\n' < $cache | sed "s#^.*/io.github.kotoba-lang/kotoba-verifier/[0-9a-f]*/#$V/#"; } | paste -sd: - > $O/classpath.txt
# the packaged seed
mkdir -p $O/seed-build; cp $BIN $O/seed-build/seed-1.bin; cp ${BIN:r}.offset $O/seed-build/seed-1.offset
SEED_BUILD=$O/seed-build zsh $R/scripts/seed/package.sh 1 --scope "$R:$O:/private/tmp:/tmp" --out $O/seed > $O/package.log
cc -O2 -std=c11 -Wall \
  -DAMU_NODE="\"$NODE\"" -DAMU_NBB="\"$R/node_modules/nbb/cli.js\"" -DAMU_ROOT="\"$R\"" \
  -DAMU_CLASSPATH="\"$(cat $O/classpath.txt)\"" -DAMU_SEED="\"$O/seed\"" \
  $R/scripts/seed-backend/amu-seed-wrapper.c -o $O/amu-seed
sha() { shasum -a 256 $1 | cut -c1-64; }
{
  echo "wrapper $O/amu-seed sha256 $(sha $O/amu-seed) (BOOTSTRAP-TOOL: execs node + nbb; not a product compiler)"
  echo "seed-command $O/seed sha256 $(sha $O/seed)"
  echo "seed-code $BIN sha256 $(sha $BIN) bytes $(wc -c < $BIN | tr -d ' ')"
  echo "node $NODE $($NODE --version)"
  echo "verifier-worktree $V HEAD $(git -C $V rev-parse HEAD) dirty $(git -C $V status --porcelain -- src | wc -l | tr -d ' ')"
  echo "amu HEAD $(git -C $R rev-parse HEAD) dirty $(git -C $R status --porcelain -- src | wc -l | tr -d ' ')"
  echo "classpath $O/classpath.txt sha256 $(sha $O/classpath.txt) entries $(tr ':' '\n' < $O/classpath.txt | wc -l | tr -d ' ')"
} > $O/wrapper.info
cat $O/wrapper.info
