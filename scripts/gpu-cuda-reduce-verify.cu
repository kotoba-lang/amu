// MEASUREMENT INSTRUMENT (JUN-57): the correctness instrument for the
// EMITTED CUDA reduce arms on an NVIDIA host -- the instrument class
// ADR-0373 named for the Metal channel ("a native harness of the
// ADR-0373 kind"), written for the CUDA channel. This is NOT repository
// product code and NOT a wire-42 route: the amu runtime executes
// :gpu/compute through wire 42, which has had no route since the C
// loader removal (ADR 0371); this instrument loads the emitter's own
// CUDA output (kotoba.compiler.accelerator / accelerator-subgroup-reduce
// / accelerator-warp-shuffle-reduce, via scripts/emit-gpu-*-reduce-cuda.cljk,
// compiled to .cubin by nvcc) through the CUDA driver API directly, so
// the emitted bytes execute on real hardware today.
//
// CORRECTNESS ONLY. It dispatches each arm once per cell and verifies
// the partials the kernel produces against a double CPU reference
// folded over the same padded-lane shape, with the exact semantics of
// the Metal instrument (scripts/gpu-subgroup-reduce-metal-measure.m):
// :sum may differ in the low bits (the tree regrouping moves them) and
// is judged by the observed max deviation against the 0.05 bound the
// Metal instrument set; :max/:min must agree BIT-FOR-BIT with the
// reference in the ordinary value domain (rule 2). It records NO
// timing: no CUDA events, no host clock span, no `sample` line exists
// in this instrument. The paired-timing protocol (interleaved pairs,
// alternating order, warmup discard) and the claim-protocol adoption
// row for the CUDA channel are their own later rows -- this slice
// answers EXECUTED-CORRECT and nothing else.
//
//   verify <cubin> <entry> <workgroup> <elements> <op> <arm> <shared-bytes>
//
// <cubin> is one emitted arm compiled at the cell's W (the :subgroup-
// reduce arm sizes its __shared__ partials array from the emitted W, so
// a cubin built at another W is not this cell; the :warp-shuffle-reduce
// arm is workgroup-parametric and its bytes are W-independent). <entry>
// is reduce_sum / reduce_max / reduce_min -- the kernel name the KIR's
// :kernel/name carries. <shared-bytes> is the DYNAMIC shared memory the
// launch passes: 0 for the :subgroup-reduce arm (its array is static),
// W/32 floats for the :warp-shuffle-reduce arm (its `extern __shared__
// float s[]` scratch). The padded-lane identities the kernels fold are
// per-operator (0.0f for :sum/:max, +inf for :min) and the reference
// folds the same identities over the same padded shape.
//
// Output is machine-readable lines on stdout; the verdict line is
//
//   verify op=<op> arm=<arm> max_abs_vs_ref=<g> bit_exact_vs_ref=<0|1> ok=<0|1>
//
// Exit status 0 iff every ok flag is 1. Every positional gate is a >=
// test (the exact-match class the Metal instrument's argv-gate comment
// names); a value outside its bound is REFUSED, never clamped.

#include <cuda.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ELEMENTS 16777216u /* 2^24: the input buffer is 4n bytes and
                                * the CPU reference loop is O(n) per run */
#define MAX_SHARED 49152u      /* sm_72's dynamic shared-memory limit */

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

int main(int argc, char **argv) {
  if (argc < 8 || argc > 8) {
    fprintf(stderr,
            "usage: verify <cubin> <entry> <workgroup> <elements> <op> "
            "<arm> <shared-bytes>\n");
    return 2;
  }
  const char *cubin = argv[1];
  const char *entry = argv[2];
  char *end = 0;

  unsigned long w = strtoul(argv[3], &end, 10);
  if (end == argv[3] || *end != '\0' || w < 32ul || w > 1024ul ||
      (w & (w - 1ul)) != 0) {
    fprintf(stderr,
            "REFUSED workgroup %s: need a power of two in [32, 1024]\n",
            argv[3]);
    return 2;
  }
  uint32_t WG = (uint32_t)w;

  unsigned long e = strtoul(argv[4], &end, 10);
  if (end == argv[4] || *end != '\0' || e < 1ul || e > (unsigned long)MAX_ELEMENTS) {
    fprintf(stderr,
            "REFUSED elements %s: need an integer in [1, %u]\n", argv[4],
            MAX_ELEMENTS);
    return 2;
  }
  uint32_t N = (uint32_t)e;

  int op = (strcmp(argv[5], "sum") == 0)   ? 0
           : (strcmp(argv[5], "max") == 0) ? 1
           : (strcmp(argv[5], "min") == 0) ? 2
                                           : -1;
  if (op < 0) {
    fprintf(stderr, "REFUSED op %s: need sum, max or min\n", argv[5]);
    return 2;
  }

  const char *arm = argv[6];
  size_t arm_len = strlen(arm);
  if (arm_len == 0 || arm_len > 32) {
    fprintf(stderr, "REFUSED arm %s: need a non-empty label of at most 32 "
                    "characters\n", argv[6]);
    return 2;
  }

  unsigned long sh = strtoul(argv[7], &end, 10);
  if (end == argv[7] || *end != '\0' || sh > (unsigned long)MAX_SHARED) {
    fprintf(stderr,
            "REFUSED shared-bytes %s: need an integer in [0, %u]\n", argv[7],
            MAX_SHARED);
    return 2;
  }
  size_t shared_bytes = (size_t)sh;

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

  CUcontext ctx;
  CK(cuCtxCreate(&ctx, 0, dev));

  CUmodule mod;
  CK(cuModuleLoad(&mod, cubin));
  CUfunction fn;
  CK(cuModuleGetFunction(&fn, mod, entry));

  uint32_t num_groups = (N + WG - 1) / WG;

  /* Input: the Metal instrument's exact generator and value domain --
   * one LCG, xs[i] = (lcg_next() >> 8) / 2^24 in [0, 1). */
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

  /* One discarded warmup launch, then the verification launch -- the
   * Metal instrument's warmup idiom, minus the timed submits this
   * instrument deliberately does not have. */
  CK(cuLaunchKernel(fn, num_groups, 1, 1, WG, 1, 1, shared_bytes, 0, args,
                    NULL));
  CK(cuCtxSynchronize());
  CK(cuLaunchKernel(fn, num_groups, 1, 1, WG, 1, 1, shared_bytes, 0, args,
                    NULL));
  CK(cuCtxSynchronize());
  CK(cuMemcpyDtoH(got, d_parts, (size_t)num_groups * 4));

  /* Verified read-back against the double CPU reference folded over the
   * same padded-lane shape (the Metal instrument's semantics, verbatim
   * in substance). */
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
  printf("verify op=%s arm=%s max_abs_vs_ref=%.9g bit_exact_vs_ref=%d ok=%d\n",
         argv[5], arm, max_dev_ref, exact_ref, ok);

  cuMemFree(d_x);
  cuMemFree(d_parts);
  cuModuleUnload(mod);
  cuCtxDestroy(ctx);
  free(xs);
  free(got);
  free(ref);
  return ok ? 0 : 1;
}
