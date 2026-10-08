#!/bin/zsh
# seed/tests/kgraph-capacity/loader-variant.sh <capacity> <out-binary> -- an INVESTIGATION build of tools/kexe_loader.c with
# KEXE_KGRAPH_CAPACITY = <capacity> and a census of the kgraph printed by the supervisor after every guest run (success
# or trap) when KEXE_KGRAPH_REPORT is set:
#   KGRAPH {:used N :capacity C :kw-entities E :kw-static S :kw-chunks K :other O}
# kw-entities = datoms with the seed's keyword-registry attribute A0 (1897424841649887629; one per keyword registered),
# kw-static = those whose value is -1 (the keyword is in the module's static __r6-kwtab), kw-chunks = datoms with an
# attribute in A0+1 .. A0+64 (21-bit packed code points, three per datom), other = everything else (user `rel`).
# On a completed run the guest side also prints KGRAPH-GET {:calls N :datoms-scanned M} (kgraph_get is a linear scan).
# KEXE_KGRAPH_DUMP=<file> also writes one line per registered keyword: datom index, code point count (-1 = static),
# the decoded text.
# A third argument `indexed` answers kgraph_get through an (e, a) hash kept by the guest process (same answers, no
# linear scan): the cost model of option (c) in docs/selfhost-kgraph-capacity-20261008.md.
# Never install the result: the decided capacity lives in tools/kexe_loader_decisions.kotoba.
emulate -L zsh; setopt pipefail
H=${0:A:h}; R=${H:h:h:h}
[ $# -ge 2 ] || { echo "usage: loader-variant.sh <capacity> <out> [indexed]" >&2; exit 2; }
cap=$1; out=${2:A}; src=$out.c
python3 - $R/tools/kexe_loader.c $src $cap ${3:-} <<'PY'
import sys
s = open(sys.argv[1]).read(); cap = int(sys.argv[3])
def sub(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)
sub("#define KEXE_KGRAPH_CAPACITY 4096u", "#define KEXE_KGRAPH_CAPACITY %du" % cap)
sub("_Static_assert(sizeof(((struct kexe_shared_v11 *)0)->datoms) == 98304,",
    "_Static_assert(sizeof(((struct kexe_shared_v11 *)0)->datoms) == %d * 24," % cap)
sub("static void report_budget_trap(const struct kexe_shared_v11 *shared, int child_status) {\n",
    """static void report_budget_trap(const struct kexe_shared_v11 *shared, int child_status) {
  if (getenv("KEXE_KGRAPH_REPORT") != NULL) {
    const int64_t a0 = 1897424841649887629LL;
    unsigned long long ent = 0, st = 0, ch = 0, other = 0;
    for (uint64_t i = 0; i < shared->kgraph_used; i++) {
      int64_t a = shared->datoms[i].a;
      if (a == a0) { ent++; if (shared->datoms[i].v == -1) st++; }
      else if (a > a0 && a <= a0 + 64) ch++;
      else other++;
    }
    fprintf(stderr, "KGRAPH {:used %llu :capacity %u :kw-entities %llu :kw-static %llu :kw-chunks %llu :other %llu}\\n",
            (unsigned long long)shared->kgraph_used, (unsigned)KEXE_KGRAPH_CAPACITY, ent, st, ch, other);
    const char *dump = getenv("KEXE_KGRAPH_DUMP");
    FILE *df = dump != NULL ? fopen(dump, "w") : NULL;
    for (uint64_t i = 0; df != NULL && i < shared->kgraph_used; i++) {
      if (shared->datoms[i].a != a0) continue;
      int64_t e = shared->datoms[i].e, n = shared->datoms[i].v;
      fprintf(df, "%llu\\t%lld\\t", (unsigned long long)i, (long long)n);
      for (int64_t j = 0; j < n; j++) {
        int64_t w = INT64_MIN;
        for (uint64_t m = 0; m < shared->kgraph_used; m++)
          if (shared->datoms[m].e == e && shared->datoms[m].a == a0 + 1 + j / 3) w = shared->datoms[m].v;
        uint32_t c = (uint32_t)(((uint64_t)w >> (21 * (j % 3))) & 0x1fffff);
        if (c < 0x80) fputc((int)c, df);
        else if (c < 0x800) { fputc(0xc0 | (c >> 6), df); fputc(0x80 | (c & 63), df); }
        else if (c < 0x10000) { fputc(0xe0 | (c >> 12), df); fputc(0x80 | ((c >> 6) & 63), df); fputc(0x80 | (c & 63), df); }
        else { fputc(0xf0 | (c >> 18), df); fputc(0x80 | ((c >> 12) & 63), df); fputc(0x80 | ((c >> 6) & 63), df); fputc(0x80 | (c & 63), df); }
      }
      fputc('\\n', df);
    }
    if (df != NULL) fclose(df);
  }
""")
sub("""static int64_t checked_kgraph_assert(struct kexe_context_v11 *context,""",
    """static unsigned long long kexe_kg_get_calls, kexe_kg_get_scanned;
static int64_t checked_kgraph_assert(struct kexe_context_v11 *context,""")
sub("""  int64_t result = INT64_MIN;
  for (uint64_t i = 0; i < shared->kgraph_used; i++) {""",
    """  int64_t result = INT64_MIN;
  kexe_kg_get_calls++; kexe_kg_get_scanned += shared->kgraph_used;
  for (uint64_t i = 0; i < shared->kgraph_used; i++) {""")
sub("""  if (munmap(memory, mapped) != 0) fail("munmap");
  if (munmap(shared, sizeof(*shared)) != 0) fail("shared munmap");
  _exit(command_mode""",
    """  if (getenv("KEXE_KGRAPH_REPORT") != NULL)
    fprintf(stderr, "KGRAPH-GET {:calls %llu :datoms-scanned %llu}\\n", kexe_kg_get_calls, kexe_kg_get_scanned);
  if (munmap(memory, mapped) != 0) fail("munmap");
  if (munmap(shared, sizeof(*shared)) != 0) fail("shared munmap");
  _exit(command_mode""")
if len(sys.argv) > 4 and sys.argv[4] == "indexed":
    # point lookups through an (e, a) -> latest-datom-index hash in the guest process; same last-write-wins answer
    sub("""static unsigned long long kexe_kg_get_calls, kexe_kg_get_scanned;""",
        """static unsigned long long kexe_kg_get_calls, kexe_kg_get_scanned;
#define KEXE_KG_INDEX_SLOTS (2u * KEXE_KGRAPH_CAPACITY)
static uint32_t kexe_kg_index[KEXE_KG_INDEX_SLOTS]; /* datom index + 1, 0 = empty */
static uint64_t kexe_kg_slot(const struct kexe_shared_v11 *shared, int64_t e, int64_t a) {
  uint64_t h = ((uint64_t)e * 0x9E3779B97F4A7C15ull) ^ ((uint64_t)a * 0xC2B2AE3D27D4EB4Full);
  uint64_t i = (h ^ (h >> 29)) % KEXE_KG_INDEX_SLOTS;
  while (kexe_kg_index[i] != 0) {
    const struct kexe_datom_v1 *d = &shared->datoms[kexe_kg_index[i] - 1];
    if (d->e == e && d->a == a) break;
    i = (i + 1) % KEXE_KG_INDEX_SLOTS;
  }
  return i;
}""")
    sub("""  uint64_t index = shared->kgraph_used++;
  shared->datoms[index].e = e;
  shared->datoms[index].a = a;
  shared->datoms[index].v = v;
  return 1;""", """  uint64_t index = shared->kgraph_used++;
  shared->datoms[index].e = e;
  shared->datoms[index].a = a;
  shared->datoms[index].v = v;
  kexe_kg_index[kexe_kg_slot(shared, e, a)] = (uint32_t)index + 1u;
  return 1;""")
    sub("""  kexe_kg_get_calls++; kexe_kg_get_scanned += shared->kgraph_used;
  for (uint64_t i = 0; i < shared->kgraph_used; i++) {""",
        """  kexe_kg_get_calls++;
  { uint32_t x = kexe_kg_index[kexe_kg_slot(shared, e, a)]; return x == 0 ? INT64_MIN : shared->datoms[x - 1].v; }
  for (uint64_t i = 0; i < shared->kgraph_used; i++) {""")
open(sys.argv[2], "w").write(s)
PY
cc $src -std=c11 -O2 -o $out
