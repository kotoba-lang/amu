// gpu-mufu-entryexcl-microbench.cu -- amu-gpu tick 2026-10-26 (v6 of the
// interleaved-spelling MUFU row -- THE ENTRY-EXCLUDED OPEN-CHAIN
// INSTRUMENT), SCRATCH ONLY (never staged).
//
// THE NAMED ITEM: the ADR-0361 twenty-ninth amendment's PROPOSED
// instrument ("identifiable only under the spec'd entry-excluding
// discipline; instrument PROPOSED, not implemented"). This file
// IMPLEMENTS it: open chains with the entry edge EXCLUDED by timing
// discipline (first operand ready before the timing boundary, sink
// consumer common to all arms), which the twenty-ninth amendment's
// exact rank/nullspace analysis says is the ONLY family in which the
// e_MF/e_FM split is identifiable.
//
// DISCIPLINE (per the twenty-ninth amendment): each loop iteration times
// ONE open-chain instance of the arm's word w with a clock64() pair:
//   t0 = clock64();  <word w: a dependent chain on x>  t1 = clock64();
//   acc += t1 - t0;  <16 dependent integer adds (pad)>;
// The entry operand x is READY BEFORE t0: for r=0 it sits in the
// prologue; for r>0 it is the previous iteration's chain output, which
// completes long before the next t0 (the gap carries t1's S2R, the acc
// add, 16 DEPENDENT add.u32 pad ops on a separate register p, the
// counter/ISETP/BRA -- far more than the longest single-op latency, the
// MUFU at ~15 cyc). The pad is OUTSIDE every timed region and identical
// in every arm. The tail after the last chain op is byte-identical
// across arms (same clock pair, same acc/pad/counter), so every arm
// measures D(w) = sum of w's internal edge prices + one end-type
// constant + one common floor -- exactly the model the estimators and
// closures of the twenty-ninth amendment are written in.
//
// PREDICTIONS (PRE-REGISTERED here before the first run; tested, not
// assumed). V(w) below = per-iteration delta D(w) of word w:
//   P1 (closure C1, 29th amendment): V(MFM) == V(MF) + V(FM) - V(F)
//   P2 (closure C2, 29th amendment): V(FMF) == V(FM) + V(MF) - V(M)
//   P3: e_MM' = V(MM) - V(M) reproduces the landed MEASURED cyclic
//       slope e_MM = 14.9966 (CONSUMED at its commit) to quantization
//   P4: e_FF' = V(FF) - V(F) reproduces the landed MEASURED cyclic
//       slope e_FF = 4.0000 to quantization
//   P5: e_MF + e_FM = (V(MF)-V(F)) + (V(FM)-V(M)) reproduces the landed
//       MEASURED cycle sum 21.0000 to quantization
//   P6 (falsifier stance, 29th amendment): if C1 or C2 fails beyond the
//       instrument's named tolerance, the entry-excluding discipline's
//       premise is wrong and the split STAYS UNMEASURED -- the
//       estimators must NOT be reported as the split.
// TOLERANCE: each per-iteration delta quantizes to whole SM cycles
// (clock64); the per-thread mean over RLT=256 iterations has 1/256 cyc
// granularity IF iteration deltas vary, and integer cyc if they are
// phase-locked (acc mod 256 probes this -- acc%256==0 for every thread
// means every iteration returned the same integer). Closures/estimators
// are reported at the resolution the data actually carries; a closure
// residual beyond 1.0 cyc is a FAIL at any resolution this instrument
// carries.
//
// The estimators of the twenty-ninth amendment (reported ONLY if P1/P2
// hold): e_MF = V(MF) - V(F), e_FM = V(FM) - V(M).
//
// ANCHORS: operands are SYMBOLIC (x = 2.0f, cf = 1.0f from global
// memory -- unknowable to ptxas) in EVERY arm, the chains are asm
// volatile no-fold forms; final x bit patterns are NO-FOLD WITNESSES
// ONLY (MUFU approximations are not re-derivable off-device).
//
// This is a PROBE, not a registered timing session: no paired samples,
// no AB/BA, inadmissible under the entry criterion BY KIND; it enters
// nothing, moves no record and no :measured? flag. It measures
// instruction chains, not kernels.
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cuda_runtime.h>

#define NS 128    // threads = samples per launch
#define RLT 256   // timed open-chain instances per thread
#define PADN 16   // dependent pad adds between t1 and the next t0

#define CK(x) do { cudaError_t e__ = (x); if (e__) { printf("CUDAERR %s %d\n", #x, (int)e__); } } while (0)

#define CLK(dst) asm volatile("mov.u64 %0, %%clock64;" : "=l"(dst))
#define RSQ(v)   asm volatile("rsqrt.approx.ftz.f32 %0, %0;" : "+f"(v));
#define FADD(v)  asm volatile("add.rn.ftz.f32 %0, %0, %1;" : "+f"(v) : "f"(cf));
#define PADD     asm volatile("add.u32 %0, %0, 1;" : "+r"(p));
#define PAD16 PADD PADD PADD PADD PADD PADD PADD PADD \
              PADD PADD PADD PADD PADD PADD PADD PADD

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
  ((float *)in)[2] = 2.0f;   // symbolic entry operand
  ((float *)in)[3] = 1.0f;   // symbolic fadd operand
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
