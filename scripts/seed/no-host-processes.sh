#!/bin/zsh
# scripts/seed/no-host-processes.sh [SEED_COMMAND] -- gate G5 on macOS without root: no node/java/nbb/python (or ANY
# other program) is started while the seed compiles. BOOTSTRAP-TOOL (zsh + cc).
#
# scripts/selfhost-wall/no-host-processes.sh traces execs with dtruss, which needs sudo and SIP off. This Mac has
# neither, so G5 is measured here with an exec INTERPOSER instead:
#   build/seed/noproc/noproc.dylib (C source below, built with the system cc) interposes execve, execv, execvp,
#   execvP, posix_spawn, posix_spawnp, fork, vfork, system and popen (dyld __interpose), logs every call with its path
#   to $NOPROC_LOG and then performs it unchanged. Its constructor logs "<pid> loaded" so a run that did NOT load the
#   interposer (hardened runtime, SIP-protected binary) fails closed instead of passing silently.
#   1. canary: a cc-built probe that posix_spawns /usr/bin/true and execs /usr/bin/true must be caught (2 lines),
#      proving the interposer sees spawns in a cc-built Mach-O like the packaged seed.
#   2. the packaged seed (default build/seed/seed, scripts/seed/package.sh) runs, under the interposer and with
#      an EMPTY PATH (like the qualification runner):
#        seed check <unity>, seed compile <unity> --output X (the self-compile), seed extract-native X --symbol main,
#        and seed check / compile / extract-native for each of the 19 Embench ports.
#      PASS = every command exits 0, every process logged "loaded", NO exec/posix_spawn/system/popen call was logged
#      at all (stronger than the denylist of the selfhost-wall script: the seed starts no program whatsoever), and the
#      only fork is the loader's own supervisor fork (tools/kexe_loader.c: the guest runs in a forked child of the same
#      image, the parent enforces the cpu/wall budgets): exactly one fork per seed command, never followed by an exec.
#   3. static facts printed alongside: otool -L (only /usr/lib), and the baked capability allow list (no wire 20 =
#      spawn; package.sh refuses to grant it), so a spawn attempt by the guest would trap rather than run.
# Exit 0 pass, 1 fail, 2 the interposer could not be verified (fail closed).
emulate -L zsh
setopt pipefail
source "$(dirname "$0")/lib.sh"
R=$SEED_REPO; B=$SEED_BUILD; W=$B/noproc; mkdir -p $W
seed=${1:-$B/seed}
[ -x $seed ] || { echo "no-host-processes: no packaged seed at $seed (run scripts/seed/package.sh)" >&2; exit 2; }
seed=${seed:A}

cat > $W/noproc.c <<'EOF'
#include <fcntl.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static void np_log(const char *what, const char *path) {
  const char *f = getenv("NOPROC_LOG");
  if (!f) return;
  int fd = open(f, O_WRONLY | O_APPEND | O_CREAT, 0644);
  if (fd < 0) return;
  char b[1200];
  int n = snprintf(b, sizeof b, "%d %s %s\n", (int)getpid(), what, path ? path : "-");
  if (n > 0) write(fd, b, (size_t)(n < (int)sizeof b ? n : (int)sizeof b - 1));
  close(fd);
}
__attribute__((constructor)) static void np_init(void) { np_log("loaded", getprogname()); }
static int np_execve(const char *p, char *const a[], char *const e[]) { np_log("execve", p); return execve(p, a, e); }
static int np_execv(const char *p, char *const a[]) { np_log("execv", p); return execv(p, a); }
static int np_execvp(const char *p, char *const a[]) { np_log("execvp", p); return execvp(p, a); }
static int np_execvP(const char *p, const char *s, char *const a[]) { np_log("execvP", p); return execvP(p, s, a); }
static int np_spawn(pid_t *pid, const char *p, const posix_spawn_file_actions_t *fa, const posix_spawnattr_t *at,
                    char *const a[], char *const e[]) { np_log("posix_spawn", p); return posix_spawn(pid, p, fa, at, a, e); }
static int np_spawnp(pid_t *pid, const char *p, const posix_spawn_file_actions_t *fa, const posix_spawnattr_t *at,
                     char *const a[], char *const e[]) { np_log("posix_spawnp", p); return posix_spawnp(pid, p, fa, at, a, e); }
static pid_t np_fork(void) { np_log("fork", "-"); return fork(); }
static pid_t np_vfork(void) { np_log("vfork", "-"); return fork(); }
static int np_system(const char *c) { np_log("system", c); return system(c); }
static FILE *np_popen(const char *c, const char *m) { np_log("popen", c); return popen(c, m); }
#define NP(n, o) __attribute__((used)) static struct { const void *r; const void *o; } np_i_##o \
  __attribute__((section("__DATA,__interpose"))) = { (const void *)(n), (const void *)(o) };
NP(np_execve, execve) NP(np_execv, execv) NP(np_execvp, execvp) NP(np_execvP, execvP)
NP(np_spawn, posix_spawn) NP(np_spawnp, posix_spawnp) NP(np_fork, fork) NP(np_vfork, vfork)
NP(np_system, system) NP(np_popen, popen)
EOF
cat > $W/canary.c <<'EOF'
#include <spawn.h>
#include <sys/wait.h>
#include <unistd.h>
extern char **environ;
int main(void) {
  pid_t p; int st; char *a[] = {"true", 0};
  if (posix_spawn(&p, "/usr/bin/true", 0, 0, a, environ) == 0) waitpid(p, &st, 0);
  pid_t c = fork();
  if (c == 0) { execve("/usr/bin/true", a, environ); _exit(1); }
  waitpid(c, &st, 0);
  return 0;
}
EOF
cc -O1 -dynamiclib $W/noproc.c -o $W/noproc.dylib 2> $W/cc.log && cc -O1 $W/canary.c -o $W/canary 2>> $W/cc.log \
  || { echo "no-host-processes: cc failed (see $W/cc.log)" >&2; exit 2; }

L=$W/canary.log; rm -f $L
NOPROC_LOG=$L DYLD_INSERT_LIBRARIES=$W/noproc.dylib $W/canary
cpid=$(awk '$2 == "loaded" && $3 == "canary" {print $1; exit}' $L 2>/dev/null)
ccalls=$(awk '$2 != "loaded"' $L 2>/dev/null | wc -l | tr -d ' ')   # the execve is logged by the forked child
if [ -z "$cpid" ] || [ "$ccalls" -lt 3 ]; then
  echo "no-host-processes: the interposer did not catch the canary's spawn/fork/exec (calls=$ccalls); cannot verify (fail closed)" >&2
  cat $L 2>/dev/null >&2; exit 2
fi
echo "G5 canary: interposer caught $ccalls calls of the canary ($(awk '$2 != "loaded" {printf "%s ", $2}' $L))"

[ -f $B/seed-unity.kotoba ] || zsh $R/scripts/seed/build.sh unity > /dev/null || exit 2
U=${B:A}/seed-unity.kotoba; X=$W/x; rm -rf $X; mkdir -p $X
L=$W/seed.log; rm -f $L
ncmd=0; nfail=0
run() {   # run <args...> : the seed under the interposer, empty PATH, minimal environment
  ncmd=$((ncmd + 1))
  env -i PATH=$W/empty-path HOME=$HOME TMPDIR=/tmp NOPROC_LOG=$L DYLD_INSERT_LIBRARIES=$W/noproc.dylib $seed "$@" > $X/out.$ncmd 2>&1 \
    || { nfail=$((nfail + 1)); echo "G5: command failed: seed $*"; head -3 $X/out.$ncmd; }
}
run check $U --jvm-free
run compile $U --target aarch64-macos --jvm-free --output $X/self.kseed
run extract-native $X/self.kseed --symbol main --output $X/self.bin
for f in $R/bench/embench/ports/*.kotoba; do
  s=$(head -1 $f | grep -o 'test-[A-Za-z0-9_-]*' | head -1)
  run check $f --jvm-free
  run compile $f --target aarch64-macos --jvm-free --output $X/${f:t:r}.kexe
  run extract-native $X/${f:t:r}.kexe --symbol $s --output $X/${f:t:r}.bin
done
loaded=$(awk '$2 == "loaded"' $L | wc -l | tr -d ' ')
calls=$(awk '$2 != "loaded" && $2 != "fork"' $L | wc -l | tr -d ' ')
forks=$(awk '$2 == "fork"' $L | wc -l | tr -d ' ')
same=no; [ -s $B/seed-1.bin ] && cmp -s $X/self.bin $B/seed-1.bin && same=yes
echo "G5 static: $(otool -L $seed | tail -n +2 | awk '{printf "%s ", $1}')| allow $(sed -n 's/^allow //p' $B/seed-package.info 2>/dev/null) (no wire 20 = spawn)"
echo "G5: $ncmd seed commands ($nfail failed), interposer loaded in $loaded processes, program starts (exec/spawn/system/popen) logged: $calls, forks: $forks (loader supervisor, one per command); self-compiled main == seed-1.bin: $same"
[ $calls -gt 0 ] && { echo "G5: calls:"; awk '$2 != "loaded" && $2 != "fork"' $L | head -20; }
[ $loaded -eq $ncmd ] || { echo "G5: the interposer was not loaded in every seed process ($loaded of $ncmd): not verified" >&2; exit 2; }
[ $nfail -eq 0 ] && [ $calls -eq 0 ] && [ $forks -eq $ncmd ] && { echo "G5: PASS (no program of any kind was started by the seed)"; exit 0; }
echo "G5: FAIL"; exit 1
