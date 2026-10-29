// gpu-mufu-padgap-microbench.cu -- amu-gpu tick 2026-10-26 (v7 of the
// interleaved-spelling MUFU row -- THE PAD-GAP instrument), SCRATCH
// ONLY (never staged).
//
// THE NAMED ITEM: the ADR-0361 thirtieth amendment's UNRESOLVED
// "discipline-premise-vs-realization deviation": whether the v6
// entry-excluded instrument's closure failure was (a) the
// entry-excluding discipline's premise being wrong (P6's wording) or
// (b) the realization deviating from the discipline -- the design's
// PAD16 (16 DEPENDENT add.u32) was strength-reduced by ptxas to ONE
// "IADD3 R6, R6, 0x10" (SASS-verified), so the inter-iteration gap was
// 8 instructions, not the 23 the readiness argument assumed. v7
// resolves (b) by REALIZING the gap: the pad is 16 DEPENDENT
// mad.lo.u32 on a separate register p with SYMBOLIC multiplier/addend
// (from global memory), which ptxas cannot strength-reduce. EVERY
// OTHER byte of the instrument is identical to v6 (same arms, same
// RLT=256/NS=128, same symbolic operands, same tails, same discipline).
//
// THE ONE CHANGE (named): the pad realization. v6 = 16 dependent
// add.u32 (folds to 1 instruction). v7 = 16 dependent mad.lo.u32
// (SASS must verify 16 pad instructions in every body). This DEVIATES
// from the spec's literal "16 dependent integer adds" in op class
// (IMAD, not IADD) -- named, and forced: inline asm volatile does NOT
// stop ptxas from folding add chains (v6 SASS fact), and adds of
// symbolic values still merge pairwise into IADD3's three-input add;
// a dependent IMAD chain is the smallest realization that guarantees
// the spec's actual requirement -- an inter-iteration gap of wall time
// far beyond the longest single-op latency (~15 cyc MUFU). 16
// dependent IMAD (>=4 cyc each) = >=64 cyc of gap wall time.
//
// DISCIPLINE (unchanged from v6, per the twenty-ninth amendment):
// each loop iteration times ONE open-chain instance of the arm's word
// w with a clock64() pair:
//   t0 = clock64();  <word w: a dependent chain on x>  t1 = clock64();
//   acc += t1 - t0;  <16 dependent mad.lo.u32 pad ops>;
// The entry operand x is READY BEFORE t0 (the gap now carries t1's
// S2R, the acc add, 16 DEPENDENT IMADs, the counter/ISETP/BRA -- far
// beyond the longest single-op latency). The pad is OUTSIDE every
// timed region and identical in every arm. The tail after the last
// chain op is byte-identical across arms.
//
// PREDICTIONS (PRE-REGISTERED here before the first run; tested, not
// assumed). V(w) = per-iteration delta D(w) of word w:
//   P1 (closure C1): V(MFM) == V(MF) + V(FM) - V(F)   [tol 1.0 cyc]
//   P2 (closure C2): V(FMF) == V(FM) + V(MF) - V(M)   [tol 1.0 cyc]
//   P3: e_MM' = V(MM) - V(M) reproduces the landed MEASURED cyclic
//       slope e_MM = 14.9966 (CONSUMED at its commit) to quantization
//   P4: e_FF' = V(FF) - V(F) reproduces the landed MEASURED cyclic
//       slope e_FF = 4.0000 to quantization
//   P5: e_MF + e_FM = (V(MF)-V(F)) + (V(FM)-V(M)) reproduces the
//       landed MEASURED cycle sum 21.0000 to quantization
//   P6 (falsifier stance): if C1 or C2 STILL fails beyond tolerance
//       with the SASS-verified UNFOLDED pad (16 dependent IMAD in
//       every body), the pad-fold reading (realization deviation) is
//       REFUTED as the cause of the v6 failure, the discipline's
//       premise itself is implicated (P6's original wording), and the
//       e_MF/e_FM split STAYS UNMEASURED -- the estimators must NOT
//       be reported as the split.
//   P7 (PAD-VERDICT, structural): every loop body carries exactly 16
//       pad instructions (IMAD*) between the t1 clock read and the
//       loop BRA -- the gap is REALIZED, not assumed. If P7 fails,
//       this run adjudicates NOTHING (the instrument is not the one
//       pre-registered) and is reported as a failed realization.
// TOLERANCE: identical to v6 -- closures at 1.0 cyc; per-thread means
// over RLT=256 at 1/256 cyc granularity if iteration deltas vary,
// integer cyc if phase-locked (acc%256 probed).
//
// ANCHORS: operands SYMBOLIC (x = 2.0f, cf = 1.0f from global memory)
// in EVERY arm; pad multiplier/addend k/c also from global memory
// (0x9E3779B9 / 0x7F4A7C15); final x bit patterns are NO-FOLD
// WITNESSES ONLY (MUFU approximations are not re-derivable
// off-device); pad_final is a pad-executed witness (identical across
// arms by construction).
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
// v7 THE ONE CHANGE: the pad. 16 DEPENDENT mad.lo.u32 on p, k/c
// symbolic from global memory -- ptxas cannot strength-reduce a mad
// chain (composition of p |-> p*k+c is not a mad), so the gap is
// realized as 16 instructions (P7 verifies this in SASS).
#define PMAD     asm volatile("mad.lo.u32 %0, %0, %1, %2;" : "+r"(p) : "r"(k), "r"(c));
#define PAD16 PMAD PMAD PMAD PMAD PMAD PMAD PMAD PMAD \
              PMAD PMAD PMAD PMAD PMAD PMAD PMAD PMAD

#define M RSQ(x)
#define F FADD(x)
#define W_M   M
#define W_F   F
#define W_MM  M M
#define W_FF  F F
#define W_MF  M F
#define W_FM  F M
#define W_MFM M F M
#define W_FMF F M F

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

EEK(M,   W_M)
EEK(F,   W_F)
EEK(MM,  W_MM)
EEK(FF,  W_FF)
EEK(MF,  W_MF)
EEK(FM,  W_FM)
EEK(MFM, W_MFM)
EEK(FMF, W_FMF)

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
    { "M",   ee_M   }, { "F",   ee_F   },
    { "MM",  ee_MM  }, { "FF",  ee_FF  },
    { "MF",  ee_MF  }, { "FM",  ee_FM  },
    { "MFM", ee_MFM }, { "FMF", ee_FMF },
  };
  for (int a = 0; a < 8; ++a) {
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
