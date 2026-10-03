/* scripts/seed-backend/amu-seed-wrapper.c -- BOOTSTRAP-TOOL (ADR 0365). NOT a product compiler.
 *
 * The `--compiler` command that bench/embench/run_native_qualification.py is given for the
 * `--backend seed` qualification. The runner insists on a Mach-O compiler (it runs `otool -L`) and
 * on a clean environment (empty PATH), so this tiny program execs the amu nbb route with absolute
 * paths baked in at build time (build-wrapper.sh):
 *
 *   check ...          -> node --stack-size=4096 <nbb> --classpath <cp> <root>/src/.../check_cli.cljk check ...
 *   compile ...        -> ... aarch64_cli.cljk compile ... --backend seed --seed <seed>
 *   extract-native ... -> ... x86_64_cli.cljk  extract-native ... --seed <seed>
 *
 * which is what bin/amu routes to for these commands, with the one difference that the classpath is
 * the lock's closure with kotoba-verifier taken from its worktree (the verifier with the emitter
 * registry, kotoba-verifier ADR 0052; no pin is bumped). The process tree therefore DOES contain
 * node + nbb (the bootstrap host of the big compiler) and the seed: the runner's report fields
 * "javascript_node_dependency": false / "jvm_dependency": false describe the otool output of THIS
 * file only and are not true of the run; scripts/seed-backend/embench.sh writes the correct
 * labels next to the runner's report.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef AMU_NODE
#error "build with build-wrapper.sh"
#endif

static char *dup2s(const char *a, const char *b) {
  size_t n = strlen(a) + strlen(b) + 1;
  char *r = malloc(n);
  if (!r) exit(70);
  snprintf(r, n, "%s%s", a, b);
  return r;
}

int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "amu-seed-wrapper: usage: <check|compile|extract-native> ...\n"); return 64; }
  const char *cmd = argv[1];
  const char *entry;
  int add_backend = 0, add_seed = 0;
  if (strcmp(cmd, "check") == 0) entry = "/src/kotoba/compiler/nbb/check_cli.cljk";
  else if (strcmp(cmd, "compile") == 0) { entry = "/src/kotoba/compiler/nbb/aarch64_cli.cljk"; add_backend = 1; add_seed = 1; }
  else if (strcmp(cmd, "extract-native") == 0) { entry = "/src/kotoba/compiler/nbb/x86_64_cli.cljk"; add_seed = 1; }
  else { fprintf(stderr, "amu-seed-wrapper: only check, compile and extract-native are routed\n"); return 64; }
  if (chdir(AMU_ROOT) != 0) { perror("amu-seed-wrapper: chdir"); return 70; }
  char **v = calloc((size_t)argc + 12, sizeof(char *));
  if (!v) return 70;
  int k = 0;
  v[k++] = AMU_NODE;
  v[k++] = "--stack-size=4096";
  v[k++] = AMU_NBB;
  v[k++] = "--classpath";
  v[k++] = AMU_CLASSPATH;
  v[k++] = dup2s(AMU_ROOT, entry);
  for (int i = 1; i < argc; i++) v[k++] = argv[i];
  if (add_backend) { v[k++] = "--backend"; v[k++] = "seed"; }
  if (add_seed) { v[k++] = "--seed"; v[k++] = AMU_SEED; }
  v[k] = NULL;
  execv(AMU_NODE, v);
  perror("amu-seed-wrapper: execv");
  return 70;
}
