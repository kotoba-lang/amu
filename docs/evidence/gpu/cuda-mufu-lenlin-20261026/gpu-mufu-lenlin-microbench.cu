// gpu-mufu-lenlin-microbench.cu -- amu-gpu tick 2026-10-26 (v8 of the
// interleaved-spelling MUFU row -- THE LENGTH-SERIES instrument),
// SCRATCH ONLY (never staged).
//
// THE NAMED ITEM: the ADR-0361 thirty-first amendment's UNRESOLVED
// "discipline-premise-vs-further-realization deviation" (v7 refuted the
// pad-fold reading as the closure cause; the premise itself or a
// further unexcluded realization property remains). v8 attacks the
// question at the PURE-WORD level with a length series: words M^k and
// F^k for k = 1..5 under v7's exact discipline (entry-excluded
// open-chain instances, realized 16-IMAD pad). The edge-additive model
// says V(M^k) = f + e(ent,M) + (k-1)*e(M,M) + e(M,exit) -- AFFINE in k
// -- and that stays true under ANY end-artifact that is a function of
// the first/last op only (it cancels across k). So the length series
// separates the two readings cleanly:
//   * non-affine V(M^k) or V(F^k) => no edge-additive-plus-end-artifact
//     reading survives; the measured V is REFUTED as edge-additive
//     in-form at the pure-word level (the premise is implicated), and a
//     length-dependent realization effect is named, not attributed;
//   * affine but with a slope that misses the landed cyclic price
//     (e_MM 14.9966 / e_FF 4.0000) => the interior same-pipe price is
//     CHANNEL-DEPENDENT (entry-excluded single-instance form vs the
//     cyclic/loop slope form disagree), named, not attributed;
//   * affine AND at the landed cyclic slope => the pure-word interior
//     prices are channel-consistent and the v7 closure failure lives in
//     MIXED composition (the cross edges) -- the next named question.
//
// THE ONE CHANGE (named) vs v7: the arm words. v7 = 8 composition arms
// (M/F/MM/FF/MF/FM/MFM/FMF). v8 = 10 pure-word length arms
// (M^1..M^5, F^1..F^5). EVERY OTHER byte of the instrument is
// identical to v7 (same discipline, same RLT=256/NS=128, same symbolic
// operands, same PAD16 = 16 dependent mad.lo.u32 with symbolic
// multiplier/addend, same tails).
//
// DISCIPLINE (unchanged from v7, per the twenty-ninth amendment):
//   t0 = clock64();  <word w: a dependent chain on x>  t1 = clock64();
//   acc += t1 - t0;  <16 dependent mad.lo.u32 pad ops>;
// entry operand x READY BEFORE t0 (recurrence across iterations), pad
// OUTSIDE every timed region and identical in every arm.
//
// PREDICTIONS (PRE-REGISTERED here before the first run; tested, not
// assumed). V(w) = per-iteration delta of word w; D_T(k) = V(T^k) -
// V(T^(k-1)) for T in {M,F}, k = 2..5; s_T = mean of T's first
// differences. TOL = 1.0 cyc (v6/v7's named tolerance).
//   P1 (AFFINE-M): the four M first differences are constant within
//     TOL (every |second difference| <= 1.0). FAIL => the per-op
//     increment itself depends on k: edge-additivity of the measured V
//     REFUTED in-form at the pure-word level; the end-artifact class
//     (first/last-op-only deviations) REFUTED with it.
//   P2 (AFFINE-F): same for F^k.
//   P3 (CHANNEL-M): s_M reproduces the landed MEASURED cyclic slope
//     e_MM = 14.9966 (CONSUMED at its commit) within TOL. P1 holds and
//     P3 fails => the interior M->M price is CHANNEL-DEPENDENT
//     (named, not attributed); the landed cyclic value stays the only
//     measured one under the registered criterion.
//   P4 (CHANNEL-F): s_F reproduces the landed MEASURED cyclic slope
//     e_FF = 4.0000 within TOL (same consequence shape as P3).
//   P5 (v7 REPRODUCTION, cross-instrument consistency, NOT a model
//     prediction): V(M1) reproduces v7's V(M) = 10.1602, V(F1)
//     reproduces v7's V(F) = 10.1758, D_M(2) reproduces v7's
//     V(MM)-V(M) = 11.0352, D_F(2) reproduces v7's V(FF)-V(F) =
//     -0.0273 -- each within TOL.
//   P6 (falsifier stance): NOTHING this run admits the e_MF/e_FM
//     estimators; the split STAYS UNMEASURED regardless of outcome.
//     P1/P2 hold + P3/P4 fail => the v7 failure locus moves to
//     channel-dependent interior prices (the closure residual and the
//     channel discrepancy must then be explained together -- next
//     named question). P1/P2 fail => premise implicated at the
//     pure-word level. P1..P4 all hold => closure failure localized to
//     MIXED composition (cross edges) -- next named question.
//   P7 (PAD-VERDICT, structural): every body carries exactly 16 IMAD*
//     pad instructions between the t1 clock read and the loop BRA,
//     0 inside the timed region; CHAIN-VERDICT exact named chains in
//     order; CLOCK-WRAP; OVERHEAD-IDENTICAL across all 10 arms. Any
//     P7 failure: that arm's numbers enter nothing; >0 failures and
//     the run adjudicates NOTHING.
//
// ANCHORS: operands SYMBOLIC (x = 2.0f, cf = 1.0f from global memory)
// in EVERY arm; pad multiplier/addend k/c also from global memory
// (0x9E3779B9 / 0x7F4A7C15); final x bit patterns are NO-FOLD
// WITNESSES ONLY (MUFU approximations are not re-derivable
// off-device); pad_final is a pad-executed witness.
//
// This is a PROBE, not a registered timing session: no paired samples,
// no AB/BA, inadmissible under the entry criterion BY KIND; it enters
// nothing, moves no record and no :measured? flag. It measures
// instruction chains, not kernels. SAME UTC DAY (2026-10-26) as every
// earlier probe: "cross-day run 3+" does not move.
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cuda_runtime.h>

#define NS 128    // threads = samples per launch
#define RLT 256   // timed open-chain instances per thread
#define PADN 16   // dependent pad ops between t1 and the next t0

#define CK(x) do { cudaError_t e__ = (x); if (e__) { printf("CUDAERR %s %d\n", #x, (int)e__); } } while (0)

#define CLK(dst) asm volatile("mov.u64 %0, %%clock64;" : "=l"(dst))
#define RSQ(v)   asm volatile("rsqrt.approx.ftz.f32 %0, %0;" : "+f"(v));
#define FADD(v)  asm volatile("add.rn.ftz.f32 %0, %0, %1;" : "+f"(v) : "f"(cf));
// v7's realized pad, unchanged: 16 DEPENDENT mad.lo.u32 on p, k/c
// symbolic from global memory -- ptxas cannot strength-reduce a mad
// chain (composition of p |-> p*k+c is not a mad).
#define PMAD     asm volatile("mad.lo.u32 %0, %0, %1, %2;" : "+r"(p) : "r"(k), "r"(c));
#define PAD16 PMAD PMAD PMAD PMAD PMAD PMAD PMAD PMAD \
              PMAD PMAD PMAD PMAD PMAD PMAD PMAD PMAD

#define M RSQ(x)
#define F FADD(x)
#define W_M1  M
#define W_M2  M M
#define W_M3  M M M
#define W_M4  M M M M
#define W_M5  M M M M M
#define W_F1  F
#define W_F2  F F
#define W_F3  F F F
#define W_F4  F F F F
#define W_F5  F F F F F

// entry-excluded open-chain kernel: one word instance per timed region
#define EEK(NAME, WORD)                                                          \
__global__ void ee_##NAME(const unsigned long long *in, unsigned long long *o) { \
  float x = ((const float *)in)[2];                                              \
  float cf = ((const float *)in)[3];                                             \
  unsigned int k = ((const unsigned int *)in)[4];                                \
  unsigned int c = ((const unsigned int *)in)[5];                                \
  unsigned int p = 7u;                                                           \
  unsigned long long acc = 0;                                                    \
  asm volatile("" ::: "memory");                                                 \
  _Pragma("unroll 1")                                                            \
  for (int r = 0; r < RLT; ++r) {                                                \
    unsigned long long t0, t1;                                                   \
    CLK(t0);                                                                     \
    WORD                                                                         \
    CLK(t1);                                                                     \
    asm volatile("" ::: "memory");                                               \
    acc += (t1 - t0);                                                            \
    PAD16                                                                        \
  }                                                                              \
  asm volatile("" ::: "memory");                                                 \
  o[threadIdx.x] = acc;                                                          \
  o[256 + threadIdx.x] = (unsigned long long)__float_as_uint(x);                 \
  o[512 + threadIdx.x] = (unsigned long long)p;                                  \
}

EEK(M1, W_M1)
EEK(M2, W_M2)
EEK(M3, W_M3)
EEK(M4, W_M4)
EEK(M5, W_M5)
EEK(F1, W_F1)
EEK(F2, W_F2)
EEK(F3, W_F3)
EEK(F4, W_F4)
EEK(F5, W_F5)

static int cmp_ull(const void *a, const void *b) {
  unsigned long long x = *(const unsigned long long *)a;
  unsigned long long y = *(const unsigned long long *)b;
  return (x > y) - (x < y);
}

static void report(const char *arm, int launch, unsigned long long *accs) {
  unsigned long long s[NS];
  for (int i = 0; i < NS; ++i) s[i] = accs[i];
  qsort(s, NS, sizeof(unsigned long long), cmp_ull);
  double mean = 0.0;
  unsigned long long modmin = ~0ULL, modmax = 0;
  for (int i = 0; i < NS; ++i) {
    mean += (double)accs[i];
    unsigned long long m = accs[i] % RLT;
    if (m < modmin) modmin = m;
    if (m > modmax) modmax = m;
  }
  mean /= (double)NS;
  unsigned long long med = (s[NS / 2 - 1] + s[NS / 2]) / 2;
  printf("RESULT arm=%s launch=%d n=%d med_acc=%llu med_per_iter=%.6f "
         "mean_per_iter=%.6f min_per_iter=%.6f max_per_iter=%.6f "
         "p10_per_iter=%.6f p90_per_iter=%.6f accmod_min=%llu accmod_max=%llu\n",
         arm, launch, NS,
         (unsigned long long)med,
         (double)med / (double)RLT,
         mean / (double)RLT,
         (double)s[0] / (double)RLT,
         (double)s[NS - 1] / (double)RLT,
         (double)s[NS / 10] / (double)RLT,
         (double)s[NS * 9 / 10] / (double)RLT,
         modmin, modmax);
}

int main() {
  cudaDeviceProp pr;
  CK(cudaGetDeviceProperties(&pr, 0));
  printf("device name=%s clockRate_kHz=%d multiProcessorCount=%d\n",
         pr.name, pr.clockRate, pr.multiProcessorCount);
  unsigned long long *in, *o;
  CK(cudaMallocManaged(&in, 8 * sizeof(unsigned long long)));
  CK(cudaMallocManaged(&o, 640 * sizeof(unsigned long long)));
  ((float *)in)[2] = 2.0f;          // symbolic entry operand
  ((float *)in)[3] = 1.0f;          // symbolic fadd operand
  ((unsigned int *)in)[4] = 0x9E3779B9u;  // symbolic pad multiplier
  ((unsigned int *)in)[5] = 0x7F4A7C15u;  // symbolic pad addend
  struct { const char *name; void (*fn)(const unsigned long long *, unsigned long long *); } arms[] = {
    { "M1", ee_M1 }, { "M2", ee_M2 }, { "M3", ee_M3 }, { "M4", ee_M4 }, { "M5", ee_M5 },
    { "F1", ee_F1 }, { "F2", ee_F2 }, { "F3", ee_F3 }, { "F4", ee_F4 }, { "F5", ee_F5 },
  };
  for (int a = 0; a < 10; ++a) {
    for (int l = 0; l < 3; ++l) {
      CK(cudaMemset(o, 0, 640 * sizeof(unsigned long long)));
      arms[a].fn<<<1, NS>>>(in, o);
      CK(cudaDeviceSynchronize());
      unsigned long long accs[NS];
      for (int i = 0; i < NS; ++i) accs[i] = o[i];
      report(arms[a].name, l, accs);
      if (l == 2) {
        unsigned long long xb = o[256], pv = o[512];
        printf("ANCHOR arm=%s xbits=%u (0x%08x, no-fold witness only) pad_final=%llu\n",
               arms[a].name, (unsigned)xb, (unsigned)xb, (unsigned long long)pv);
      }
    }
  }
  CK(cudaFree(in));
  CK(cudaFree(o));
  printf("run complete\n");
  return 0;
}
