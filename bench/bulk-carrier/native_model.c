/* Models three lowerings of `vector-at` over the arena layout the kexe loader
 * already has (kexe_vector_v1{offset,length} indexing flat int64_t
 * vector_items[]).  Only HOW the element is reached varies.
 *
 *   plain    : acc += a[i]                                (ADR 0284's C -O3 row)
 *   inline   : the loader's own checked_vector_at body, INLINED  <-- new number
 *   indirect : the same body reached through a function pointer  (ADR 0284 row)
 *
 * Every arm carries the same `+r` compiler barrier on the accumulator, so no
 * arm is vectorised or strength-reduced while another is.  Without it clang
 * folds the plain arm to 0.0013 ns/element -- a measurement of nothing.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <signal.h>

#define ITEM_CAPACITY 65536u
#define VECTOR_CAPACITY 4096u

struct kvec { uint64_t offset; uint64_t length; };
struct ctx { uint64_t version; };
struct shared { struct ctx context; uint64_t vector_used;
                struct kvec vectors[VECTOR_CAPACITY];
                int64_t vector_items[ITEM_CAPACITY]; };
static struct shared S;

/* byte-for-byte the loader's resolve_vector + checked_vector_at guards */
static inline struct kvec *resolve_vector(struct shared *s, int64_t handle) {
  if (handle < 0 || (uint64_t)handle >= s->vector_used) return NULL;
  return &s->vectors[handle];
}
static int64_t checked_vector_at(struct shared *s, int64_t handle, int64_t index) {
  if (s == NULL || s->context.version != 3) { raise(SIGILL); return 0; }
  struct kvec *v = resolve_vector(s, handle);
  if (v == NULL || index < 0 || (uint64_t)index >= v->length) { raise(SIGILL); return 0; }
  return s->vector_items[v->offset + (uint64_t)index];
}
static int64_t (*volatile indirect)(struct shared *, int64_t, int64_t) = checked_vector_at;

static double cpu_ns(void) {
  struct timespec ts; clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts);
  return (double)ts.tv_sec * 1e9 + (double)ts.tv_nsec;
}
#define BARRIER(x) __asm__ volatile("" : "+r"(x))
static volatile int64_t sink;

int main(int argc, char **argv) {
  long reps = atol(argv[1]);
  int rounds = atoi(argv[2]);
  const int64_t N = 64;                       /* ADR 0284's L1-resident vector */
  S.context.version = 3;
  for (int64_t i = 0; i < N; i++) S.vector_items[i] = i + 1;
  S.vectors[0].offset = 0; S.vectors[0].length = (uint64_t)N;
  S.vector_used = 1;
  int64_t *a = S.vector_items;

  printf("{\"plain\":[");
  double *sp=malloc(rounds*sizeof(double)),*si=malloc(rounds*sizeof(double)),*sx=malloc(rounds*sizeof(double));
  for (int r = 0; r < rounds; r++) {
    { double t0 = cpu_ns(); int64_t acc = 0;
      for (long k = 0; k < reps; k++) for (int64_t i = 0; i < N; i++) { acc += a[i]; BARRIER(acc); }
      double d = (cpu_ns() - t0) / (double)(reps * N); sink = acc; sp[r]=d; }
    { double t0 = cpu_ns(); int64_t acc = 0;
      for (long k = 0; k < reps; k++) for (int64_t i = 0; i < N; i++) { acc += checked_vector_at(&S, 0, i); BARRIER(acc); }
      double d = (cpu_ns() - t0) / (double)(reps * N); sink = acc; si[r]=d; }
    { double t0 = cpu_ns(); int64_t acc = 0;
      for (long k = 0; k < reps; k++) for (int64_t i = 0; i < N; i++) { acc += indirect(&S, 0, i); BARRIER(acc); }
      double d = (cpu_ns() - t0) / (double)(reps * N); sink = acc; sx[r]=d; }
  }
  for(int r=0;r<rounds;r++) printf("%s%.6f", r?",":"", sp[r]);
  printf("],\"inline\":[");
  for(int r=0;r<rounds;r++) printf("%s%.6f", r?",":"", si[r]);
  printf("],\"indirect\":[");
  for(int r=0;r<rounds;r++) printf("%s%.6f", r?",":"", sx[r]);
  printf("]}\n");
  return 0;
}
