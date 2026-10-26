// MEASUREMENT INSTRUMENT (JUN-57): the paired-timing instrument for the
// EMITTED CUDA reduce arms on an NVIDIA host -- the HONEST LEFT (a-rest)
// row of the baseline execute record
// (docs/evidence/gpu/cuda-baseline-execute-xavier-20261025/README.md):
// "the paired-timing protocol (interleaved pairs, alternating order,
// CUDA-event gpu-ns + host submit->done ns) of the ADR-0373 kind". The
// instrument class is the one ADR-0373 named for the Metal channel
// (scripts/gpu-subgroup-reduce-metal-measure.m): fresh-process runs,
// interleaved paired samples with alternating order, first submits
// discarded as warmup, and verified read-back of the partials the
// kernels produce. This is NOT repository product code and NOT a
// wire-42 route: it loads the emitters' own CUDA output (compiled to
// .cubin by nvcc) through the CUDA driver API directly.
//
// PAIRED-TIMING PROTOCOL ONLY. Unlike the correctness instrument
// (scripts/gpu-cuda-reduce-verify.cu, deliberately timer-free) this
// instrument records TWO clocks per timed dispatch:
//
//   gpu_ns  -- CUDA-event elapsed time around the kernel on the GPU
//              timeline (event record -> event record, same stream);
//   host_ns -- CLOCK_MONOTONIC around submit -> completion (the launch
//              call through the stop event's synchronize; the stop
//              event's own host-side record call sits inside the span,
//              named here rather than hidden).
//
//   timing <entry> <workgroup> <elements> <op> \
//          <cubinA> <armA> <sharedA> <cubinB> <armB> <sharedB>
//
// One PAIR of arms per invocation (a fresh process per pair block -- the
// Metal instrument's fresh-process run): PAIRS interleaved pairs, WARMUP
// discarded submits per arm first, and the within-pair order ALTERNATES
// (pair p runs arm ((p+k) mod 2 == 0) first for k = 0, 1 -- AB on even
// p, BA on odd p) so clock drift cannot favor one arm. That is the
// paired-within-run statistic of ADR-0358 / the Metal instrument,
// unchanged in substance.
//
// <cubinA>/<cubinB> are each one emitted arm compiled at the cell's W
// (the :subgroup-reduce arm sizes its __shared__ partials array from the
// emitted W, so a cubin built at another W is not this cell; the
// :warp-shuffle-reduce and :baseline arms are workgroup-parametric).
// <sharedA>/<sharedB> are the DYNAMIC shared memory each launch passes:
// W*4 for :baseline (extern __shared__ float s[] scratch), 0 for
// :subgroup-reduce (its array is static), W/32 floats = W/8 bytes for
// :warp-shuffle-reduce. The input is the Metal instrument's exact LCG
// (seed 20261023, xs[i] = (lcg_next() >> 8) / 2^24 in [0, 1)), reset
// per process -- so a pair block's two arms see the same input, and a
// cell's input equals the input the verify instrument's runs saw at that
// shape (pairing provenance across records).
//
// Output is machine-readable lines on stdout. Per timed dispatch:
//
//   sample op=<op> pair=<p> order=<A|B> arm=<arm> gpu_ns=<g> host_ns=<h>
//
// and after the pairs, an untimed verified read-back per arm (the
// correctness instrument's exact verify semantics: :sum judged by the
// observed max deviation against the 0.05 bound the Metal instrument
// set, :max/:min bit-for-bit against the double CPU reference in the
// ordinary value domain):
//
//   verify op=<op> arm=<arm> max_abs_vs_ref=<g> bit_exact_vs_ref=<0|1> ok=<0|1>
//
// Exit status 0 iff both arms verify ok and every pair produced both of
// its samples. Every positional gate is a REFUSAL outside its bound,
// never a clamp. NO SPEED CLAIM is made or implied by any line: this
// instrument records samples; the claim-protocol adoption row for the
// CUDA channel (sign claims channel-scoped) and the
// :warp-shuffle-reduce vs :subgroup-reduce vs :baseline speed question
// are their own later rows. A record of these samples is MEASURED
// timing data; every sign/verdict stays UNCLAIMED until those rows.

#include <cuda.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MAX_ELEMENTS 16777216u /* 2^24: the input buffer is 4n bytes and
                                * the CPU reference loop is O(n) per run */
#define MAX_SHARED 49152u      /* sm_72's dynamic shared-memory limit */
#define PAIRS 20               /* interleaved pairs per block (the Metal
                                * instrument's constant, unchanged) */
#define WARMUP 2               /* discarded submits per arm (ditto) */

static uint32_t lcg_state = 20261023u;
static uint32_t lcg_next(void) {
  lcg_state = lcg_state * 1664525u + 1013904223u;
  return lcg_state;
}

#define CK(call)                                                               \
  do {                                                                         \
    CUresult r_ = (call);                                                      \
    if (r_ != CUDA_SUCCESS) {                                                  \
      const char *e_ = "unknown";                                              \
      cuGetErrorString(r_, &e_);                                               \
      fprintf(stderr, "FATAL %s:%d %s -> %s\n", __FILE__, __LINE__, #call,     \
              e_);                                                             \
      return 2;                                                                \
    }                                                                          \
  } while (0)

static double host_ns_now(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (double)ts.tv_sec * 1e9 + (double)ts.tv_nsec;
}

int main(int argc, char **argv) {
  if (argc < 11 || argc > 11) {
    fprintf(stderr,
            "usage: timing <entry> <workgroup> <elements> <op> <cubinA> "
            "<armA> <sharedA> <cubinB> <armB> <sharedB>\n");
    return 2;
  }
  const char *entry = argv[1];
  char *end = 0;

  unsigned long w = strtoul(argv[2], &end, 10);
  if (end == argv[2] || *end != '\0' || w < 32ul || w > 1024ul ||
      (w & (w - 1ul)) != 0) {
    fprintf(stderr,
            "REFUSED workgroup %s: need a power of two in [32, 1024]\n",
            argv[2]);
    return 2;
  }
  uint32_t WG = (uint32_t)w;

  unsigned long e = strtoul(argv[3], &end, 10);
  if (end == argv[3] || *end != '\0' || e < 1ul ||
      e > (unsigned long)MAX_ELEMENTS) {
    fprintf(stderr, "REFUSED elements %s: need an integer in [1, %u]\n",
            argv[3], MAX_ELEMENTS);
    return 2;
  }
  uint32_t N = (uint32_t)e;

  int op = (strcmp(argv[4], "sum") == 0)   ? 0
           : (strcmp(argv[4], "max") == 0) ? 1
           : (strcmp(argv[4], "min") == 0) ? 2
                                           : -1;
  if (op < 0) {
    fprintf(stderr, "REFUSED op %s: need sum, max or min\n", argv[4]);
    return 2;
  }

  /* The entry is the KIR's :kernel/name; it must name THIS operator's
   * fold, so a mislabeled pair block is REFUSED instead of comparing
   * one operator's kernel against another operator's reference. */
  char want_entry[32];
  snprintf(want_entry, sizeof(want_entry), "reduce_%s", argv[4]);
  if (strcmp(entry, want_entry) != 0) {
    fprintf(stderr, "REFUSED entry %s: need %s for op %s\n", argv[1],
            want_entry, argv[4]);
    return 2;
  }

  const char *cubinA = argv[5];
  const char *armA = argv[6];
  const char *cubinB = argv[8];
  const char *armB = argv[9];
  for (int s = 0; s < 2; s++) {
    const char *arm = s ? armB : armA;
    size_t arm_len = strlen(arm);
    if (arm_len == 0 || arm_len > 32) {
      fprintf(stderr,
              "REFUSED arm %s: need a non-empty label of at most 32 "
              "characters\n",
              arm);
      return 2;
    }
  }
  if (strcmp(armA, armB) == 0) {
    fprintf(stderr,
            "REFUSED pair %s,%s: the two arms of a pair must differ\n", armA,
            armB);
    return 2;
  }

  size_t shared_bytes[2];
  for (int s = 0; s < 2; s++) {
    unsigned long sh = strtoul(s ? argv[10] : argv[7], &end, 10);
    if (end == (s ? argv[10] : argv[7]) || *end != '\0' ||
        sh > (unsigned long)MAX_SHARED) {
      fprintf(stderr,
              "REFUSED shared-bytes %s: need an integer in [0, %u]\n",
              s ? argv[10] : argv[7], MAX_SHARED);
      return 2;
    }
    shared_bytes[s] = (size_t)sh;
  }

  CK(cuInit(0));
  CUdevice dev;
  CK(cuDeviceGet(&dev, 0));
  char name[256] = {0};
  CK(cuDeviceGetName(name, (int)sizeof(name), dev));
  int major = 0, minor = 0;
  CK(cuDeviceGetAttribute(&major, CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR,
                          dev));
  CK(cuDeviceGetAttribute(&minor, CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR,
                          dev));
  printf("device=%s sm_%d%d\n", name, major, minor);
  printf("entry=%s\nn=%u\nworkgroup=%u\npairs=%d\nwarmup=%d\n", entry, N, WG,
         PAIRS, WARMUP);
  printf("arms=%s,%s\nshared_a=%zu shared_b=%zu\n", armA, armB, shared_bytes[0],
         shared_bytes[1]);

  CUcontext ctx;
  CK(cuCtxCreate(&ctx, 0, dev));
  CUmodule modA, modB;
  CK(cuModuleLoad(&modA, cubinA));
  CK(cuModuleLoad(&modB, cubinB));
  CUfunction fn[2];
  CK(cuModuleGetFunction(&fn[0], modA, entry));
  CK(cuModuleGetFunction(&fn[1], modB, entry));

  uint32_t num_groups = (N + WG - 1) / WG;

  /* Input: the Metal instrument's exact generator and value domain --
   * one LCG, xs[i] = (lcg_next() >> 8) / 2^24 in [0, 1). Reset per
   * process, so both arms of the block and the earlier verify
   * instrument's runs at this shape see the same input. */
  float *xs = (float *)malloc((size_t)N * sizeof(float));
  float *got = (float *)malloc((size_t)num_groups * sizeof(float));
  double *ref = (double *)malloc((size_t)num_groups * sizeof(double));
  if (xs == NULL || got == NULL || ref == NULL) {
    fprintf(stderr, "FATAL out of memory for N=%u groups=%u\n", N, num_groups);
    return 2;
  }
  for (uint32_t i = 0; i < N; i++) {
    xs[i] = (float)((lcg_next() >> 8) * (1.0f / 16777216.0f));
  }

  CUdeviceptr d_x = 0, d_parts = 0;
  CK(cuMemAlloc(&d_x, (size_t)N * 4));
  CK(cuMemAlloc(&d_parts, (size_t)num_groups * 4));
  CK(cuMemcpyHtoD(d_x, xs, (size_t)N * 4));
  uint32_t n32 = N;
  void *args[3] = {&d_x, &d_parts, &n32};

  CUevent ev_start, ev_stop;
  CK(cuEventCreate(&ev_start, CU_EVENT_DEFAULT));
  CK(cuEventCreate(&ev_stop, CU_EVENT_DEFAULT));

  /* Warmup: WARMUP discarded submits per arm (the Metal instrument's
   * idiom) -- untimed. */
  for (int wd = 0; wd < WARMUP; wd++) {
    for (int s = 0; s < 2; s++) {
      CK(cuLaunchKernel(fn[s], num_groups, 1, 1, WG, 1, 1, shared_bytes[s], 0,
                        args, NULL));
      CK(cuCtxSynchronize());
    }
  }

  /* Interleaved pairs, alternating order within the pair sequence. */
  for (int p = 0; p < PAIRS; p++) {
    for (int k = 0; k < 2; k++) {
      int s = ((p + k) % 2 == 0) ? 0 : 1; /* 0 = armA, 1 = armB */
      CK(cuEventRecord(ev_start, 0));
      double t0 = host_ns_now();
      CK(cuLaunchKernel(fn[s], num_groups, 1, 1, WG, 1, 1, shared_bytes[s], 0,
                        args, NULL));
      CK(cuEventRecord(ev_stop, 0));
      CK(cuEventSynchronize(ev_stop));
      double t1 = host_ns_now();
      float gpu_ms = 0.0f;
      CK(cuEventElapsedTime(&gpu_ms, ev_start, ev_stop));
      printf("sample op=%s pair=%d order=%c arm=%s gpu_ns=%.0f host_ns=%.0f\n",
             argv[4], p, (p % 2 == 0) ? 'A' : 'B', s ? armB : armA,
             (double)gpu_ms * 1e6, t1 - t0);
    }
  }

  /* Verified read-back (untimed): both arms' partials against the double
   * CPU reference folded over the same padded-lane shape -- the
   * correctness instrument's exact semantics. */
  for (uint32_t g = 0; g < num_groups; g++) {
    double acc = (op == 1) ? -INFINITY : (op == 2) ? INFINITY : 0.0;
    for (uint32_t l = 0; l < WG; l++) {
      uint32_t i = g * WG + l;
      double v = (i < N) ? (double)xs[i]
                         : (op == 1) ? -INFINITY
                         : (op == 2) ? INFINITY
                                     : 0.0;
      if (op == 0) acc += v;
      else if (op == 1) acc = fmax(acc, v);
      else acc = fmin(acc, v);
    }
    ref[g] = acc;
  }
  int all_ok = 1;
  for (int s = 0; s < 2; s++) {
    CK(cuLaunchKernel(fn[s], num_groups, 1, 1, WG, 1, 1, shared_bytes[s], 0,
                      args, NULL));
    CK(cuCtxSynchronize());
    CK(cuMemcpyDtoH(got, d_parts, (size_t)num_groups * 4));
    double max_dev_ref = 0.0;
    int exact_ref = 1;
    for (uint32_t g = 0; g < num_groups; g++) {
      double dr = fabs((double)got[g] - ref[g]);
      if (dr > max_dev_ref) max_dev_ref = dr;
      /* bitwise identity check runs for every operator: for :sum it
       * honestly reports 0 (the regrouping moves the low bits), for
       * :max/:min rule 2 demands it be 1 */
      float rf = (float)ref[g];
      if (memcmp(&got[g], &rf, 4) != 0) exact_ref = 0;
    }
    int ok = (op == 0) ? (max_dev_ref < 0.05) : exact_ref;
    if (!ok) all_ok = 0;
    printf("verify op=%s arm=%s max_abs_vs_ref=%.9g bit_exact_vs_ref=%d ok=%d\n",
           argv[4], s ? armB : armA, max_dev_ref, exact_ref, ok);
  }

  CK(cuEventDestroy(ev_start));
  CK(cuEventDestroy(ev_stop));
  cuMemFree(d_x);
  cuMemFree(d_parts);
  cuModuleUnload(modA);
  cuModuleUnload(modB);
  cuCtxDestroy(ctx);
  free(xs);
  free(got);
  free(ref);
  return all_ok ? 0 : 1;
}
