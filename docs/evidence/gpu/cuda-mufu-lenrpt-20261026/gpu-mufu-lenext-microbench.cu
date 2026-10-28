// gpu-mufu-lenext-microbench.cu -- amu-gpu tick 2026-10-26 (v9 of the
// interleaved-spelling MUFU row -- THE LENGTH-EXTENSION instrument),
// SCRATCH ONLY (never staged).
//
// THE NAMED ITEM: the ADR-0361 thirty-second amendment's finding that
// the measured V is REFUTED as edge-additive in-form at the pure-word
// level (the v8 length series M^1..M^5 / F^1..F^5 is NON-AFFINE) with
// "a length-dependent realization effect NAMED, NOT ATTRIBUTED", plus
// the v8-named stable non-monotonicity V(F1) = 12.5039 >
// V(F2) = 10.2266 (one FADD measures SLOWER than two). v9 extends the
// series to k = 1..8 for both families and asks two questions the v8
// range cannot answer: (a) does the F non-monotonicity REPRODUCE on a
// fresh run (stable effect vs run-specific), and (b) does the
// non-affinity PERSIST over a longer range (the refutation's scope).
//
// THE ONE CHANGE (named) vs v8: the series range. v8 = 10 pure-word
// length arms M^1..M^5 / F^1..F^5; v9 = 16 pure-word length arms
// M^1..M^8 / F^1..F^8. EVERY OTHER byte of the instrument is
// identical to v8 (same entry-excluded discipline, same RLT=256/NS=128,
// same symbolic operands, same PAD16 = 16 dependent mad.lo.u32 with
// symbolic multiplier/addend, same tails, 3 launches).
//
// DISCIPLINE (unchanged from v8, per the twenty-ninth amendment):
//   t0 = clock64();  <word w: a dependent chain on x>  t1 = clock64();
//   acc += t1 - t0;  <16 dependent mad.lo.u32 pad ops>;
// entry operand x READY BEFORE t0 (recurrence across iterations), pad
// OUTSIDE every timed region and identical in every arm.
//
// PREDICTIONS (PRE-REGISTERED here before the first run; tested, not
// assumed). V(w) = pooled median over the 3 launches of med_per_iter;
// D_T(k) = V(T^k) - V(T^(k-1)) for T in {M,F}, k = 2..8; D2_T(k) =
// D_T(k+1) - D_T(k), k = 2..7; s_T = mean of T's first differences
// over k = 2..8. TOL = 1.0 cyc (the named tolerance).
//   P1 (v8 REPRODUCTION, cross-run consistency, NOT a model
//     prediction): each shared arm's pooled V reproduces v8's pooled V
//     within TOL -- M1 10.2148, M2 23.5156, M3 46.2617, M4 61.2227,
//     M5 76.2266, F1 12.5039, F2 10.2266, F3 14.3711, F4 18.8359,
//     F5 22.3047 (CONSUMED at the v8 commit). NAMED IN HEADER: v8's
//     own launch-to-launch median spreads exceeded TOL on M1 (2.875),
//     M3 (2.301), F4 (2.313), F5 (2.285) -- the P1 verdicts on those
//     four arms are noise-limited by v8's own noise floor (named, not
//     hidden); the other six arms are not.
//   P2 (F-NON-MONOTONICITY): pooled V(F1) > pooled V(F2) + TOL (v8
//     delta +2.2773). FAIL => the named stable non-monotonicity does
//     not reproduce; it is downgraded from "stable within v8" to
//     run-specific (named).
//   P3 (NON-AFFINITY EXTENDS): max |D2_T| > TOL for BOTH families over
//     the full k = 1..8 range (and the k = 1..5 subset verdict is
//     reported as the direct v8 reproduction sub-test). FAIL for a
//     family => that family's series is affine over the extended
//     range; the v8 refutation is range-limited (named).
//   P4 (CHANNEL-M): s_M reproduces the landed MEASURED cyclic slope
//     e_MM = 14.9966 (CONSUMED at its commit) within TOL.
//   P5 (CHANNEL-F): s_F reproduces the landed MEASURED cyclic slope
//     e_FF = 4.0000 within TOL.
//   P6 (falsifier stance): NOTHING this run admits the e_MF/e_FM
//     estimators; the split STAYS UNMEASURED regardless of outcome;
//     NOTHING MOVES (rule 4) -- no record, no :measured? flag, no
//     selection answer, no workgroup row.
//   P7 (structural): every body carries exactly k named chain
//     operations IN ORDER (M^k = k MUFU.RSQ, F^k = k FADD*), the
//     chain strictly between the two SR_CLOCKLO reads (CLOCK-WRAP),
//     exactly 16 IMAD* pad instructions after t1 and 0 inside the
//     timed region (PAD-VERDICT), and the non-chain overhead multiset
//     IDENTICAL across all 16 arms (OVERHEAD-IDENTICAL). Any P7
//     failure: that arm's numbers enter nothing; >0 failures and the
//     run adjudicates NOTHING.
//
// SHAPE: the k = 6..8 points beyond v8's range are reported
// descriptively (no shape prediction is registered; P3 is the only
// verdict the extension carries).
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
// v8's realized pad, unchanged: 16 DEPENDENT mad.lo.u32 on p, k/c
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
#define W_M6  M M M M M M
#define W_M7  M M M M M M M
#define W_M8  M M M M M M M M
#define W_F1  F
#define W_F2  F F
#define W_F3  F F F
#define W_F4  F F F F
#define W_F5  F F F F F
#define W_F6  F F F F F F
#define W_F7  F F F F F F F
#define W_F8  F F F F F F F F

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
EEK(M6, W_M6)
EEK(M7, W_M7)
EEK(M8, W_M8)
EEK(F1, W_F1)
EEK(F2, W_F2)
EEK(F3, W_F3)
EEK(F4, W_F4)
EEK(F5, W_F5)
EEK(F6, W_F6)
EEK(F7, W_F7)
EEK(F8, W_F8)

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
    { "M1", ee_M1 }, { "M2", ee_M2 }, { "M3", ee_M3 }, { "M4", ee_M4 },
    { "M5", ee_M5 }, { "M6", ee_M6 }, { "M7", ee_M7 }, { "M8", ee_M8 },
    { "F1", ee_F1 }, { "F2", ee_F2 }, { "F3", ee_F3 }, { "F4", ee_F4 },
    { "F5", ee_F5 }, { "F6", ee_F6 }, { "F7", ee_F7 }, { "F8", ee_F8 },
  };
  for (int a = 0; a < 16; ++a) {
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
