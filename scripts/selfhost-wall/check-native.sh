#!/bin/zsh
# BOOTSTRAP-REFERENCE (JVM-built, GraalVM native-image). Dev feedback loop only.
#
# Same interface and output as check-one.sh / /private/tmp/wall-one.sh: prints
# "<file>\tOK" or the first `amu check` refusal message. The difference is the
# engine: a GraalVM native image of the JVM-compiled sources instead of nbb/SCI
# interpreting the compiler. Not a product artifact and not a selfhost claim --
# see docs/selfhost-fast-checker-20261001.md for what has to exist before the
# fast checker can be built by amu itself.
#
# Env: WALL_CP (classpath file), WALL_K (kotoba-lang checkout holding lang/compat
#      and the grant policy), WALL_AMU_SRC (this repo's src; default <repo>/src),
#      AMU_NATIVE (the binary; default build/native-image/amu-native under the
#      repo, then /private/tmp/amu-native-build/amu-native),
#      CHECK_NATIVE_DEFINITIONS=1 also computes the per-definition CIDs
#      (ADR 0300), as nbb `check` always does. They are most of the time of a
#      check and no refusal of the wall has ever come from them, so the default
#      skips them (--no-definitions).
#
# Build:  scripts/selfhost-wall/build-native.sh  (see that file)
f=$1
AMU=${WALL_AMU_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}
K=${WALL_K:?set WALL_K to the kotoba-lang checkout}
CP=$(cat ${WALL_CP:?set WALL_CP})
N=${AMU_NATIVE:-}
if [ -z "$N" ]; then
  for c in "$AMU/build/native-image/amu-native" /private/tmp/amu-native-build/amu-native; do
    [ -x "$c" ] && N=$c && break
  done
fi
# A reach list may still name a ~/.gitlibs pin or a stale wt-<letter>-<repo> copy; the
# classpath (make-classpath.py) resolves the newest worktree, so measure THAT file
# (remap-reach.py), else kotoba-io-* report 'Reader is not exported' on a stale pin.
if [ -z "$CHECK_NATIVE_NO_REMAP" ] && [ -f "$f" ]; then
  rf=$(printf '%s\n' "$f" | python3 "$AMU/scripts/selfhost-wall/remap-reach.py" /dev/stdin 2>/dev/null | head -1)
  [ -n "$rf" ] && [ -f "$rf" ] && f=$rf
fi
[ -x "$N" ] || { echo "no native checker: build it with scripts/selfhost-wall/build-native.sh" >&2; exit 2; }
SP="$(echo "$CP" | tr ':' '\n' | grep '/src$' | sed 's/^/--source-path /' | tr '\n' ' ') --source-path ${WALL_AMU_SRC:-$AMU/src} --source-path $K/lang/compat"
# The compiler recurses deeply (nbb is run with --stack-size=4096 for the same
# reason); a native main thread takes the shell's stack limit.
ulimit -s 65500 2>/dev/null || ulimit -s unlimited 2>/dev/null
DEFARG=--no-definitions
[ -n "$CHECK_NATIVE_DEFINITIONS" ] && DEFARG=
r=$($N check $f --policy $K/lang/selfhost-compiler-grant.edn ${=SP} --json ${=DEFARG} 2>&1)
if echo "$r" | grep -q ':ok true\|:format :kotoba.check/v1'; then m="OK"; else m=$(echo "$r" | grep -o ':message "[^"]*' | head -1 | cut -c11-170); fi
printf "%s\t%s\n" "$f" "$m"
