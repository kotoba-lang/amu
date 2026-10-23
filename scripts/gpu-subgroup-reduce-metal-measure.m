// MEASUREMENT INSTRUMENT (JUN-58): interleaved :baseline-vs-:subgroup-reduce
// comparison of the EMITTED MSL arms on this host's Apple GPU.
//
// This is NOT repository product code and NOT a wire-42 route. The amu
// runtime executes :gpu/compute through wire 42, which has had no route since
// the C loader removal (ADR 0371); this harness dispatches the emitter's own
// MSL output (kotoba.compiler.accelerator / accelerator-subgroup-reduce, via
// scripts/gpu-subgroup-reduce-metal-measure.cljk) through the Metal API
// directly, so the two arms can be compared on real hardware today. The
// protocol follows the workgroup sweeps (ADR-0358): fresh-process runs,
// interleaved paired samples with alternating order, first submits discarded
// as warmup, and verified read-back of the partials the kernels produce.
//
//   measure <workdir> [workgroup] [elements] [op-order]
//
// [workgroup] is the dispatch width W (default 256, the measured Apple
// workgroup row of ADR-0358); a W-sweep cell passes its own width, and the
// emitted sources must have been emitted at that same width (the subgroup
// arm sizes its threadgroup partials array from the emitted W).
//
// [elements] is the reduction shape n (default 1000003 -- the shape every
// cell before the shape-2 run used; not a multiple of W, so the padded-lane
// tail is exercised). A shape-2 cell passes its own count (the shape-2 run
// uses 1048576 = 2^20: a clean multiple of every W in [32, 1024], so the
// tail is absent and the shape variable is the ONLY thing that changes).
// The emitted kernels read n at runtime (buffer 2), so the same emitted
// bytes serve every shape; the arms stay byte-identical across shapes.
//
// [op-order] is the operator dispatch order: a comma-separated permutation
// of sum,max,min (default "sum,max,min" -- the fixed order every cell before
// the op-order variant used). The variant exists because the fresh-process
// GPU clock ramp left :sum with NO fast-regime sample under the fixed order
// (the ramp completed after :sum's block on every cell), which structurally
// blocked the W = 32 regime question (the shape-2 record's named blocker).
// A "sum-last" order puts :sum's block after the ramp on purpose.
//
// <workdir> must contain baseline-<op>.metallib and subgroup-<op>.metallib
// for op in {sum, max, min} (entry reduce_<op>, the emitter's kernel name --
// one library per arm and operator: the subgroup arm's sources all define the
// same emitted `combine` helper, which collides if linked together) and
// probe.metallib (the instrument kernel that reports
// [[threads_per_simdgroup]] -- the tested device's reported subgroup size,
// which ADR-0360's measurement contract keys the result to).
//
// Output is machine-readable lines on stdout; statistics are computed by
// scripts/gpu-subgroup-reduce-metal-measure.py. All input values are in
// [0, 1): no NaN payloads and no negative zeros, i.e. rule 2's ordinary
// value domain (ADR-0356).

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* The reduction shape n. Default 1000003 (the historical cell); argv[3]
 * overrides -- the shape-2 run passes 1048576. NOT a compile-time constant
 * any more: the shape is a measurement variable, so it must ride the
 * command line like W does. The old #define kept the 'not a multiple of WG:
 * padded lanes exercised' property of the DEFAULT shape only. */
static uint32_t N = 1000003u;
#define PAIRS 20        /* interleaved pairs per operator per process */
#define WARMUP 2        /* discarded submits per arm */

static uint32_t WG = 256u; /* default: the measured Apple workgroup row
                            * (ADR-0358); argv[2] overrides */

static uint32_t lcg_state = 20261023u;
static uint32_t lcg_next(void) {
  lcg_state = lcg_state * 1664525u + 1013904223u;
  return lcg_state;
}

static id<MTLLibrary> load_lib(id<MTLDevice> dev, NSString *dir, NSString *name) {
  NSError *err = nil;
  NSString *path = [dir stringByAppendingPathComponent:name];
  id<MTLLibrary> lib = [dev newLibraryWithFile:path error:&err];
  if (lib == nil) {
    fprintf(stderr, "FATAL load %s: %s\n", name.UTF8String,
            err.localizedDescription.UTF8String);
    exit(2);
  }
  return lib;
}

static id<MTLComputePipelineState> pso_for(id<MTLDevice> dev, id<MTLLibrary> lib,
                                           const char *entry) {
  NSError *err = nil;
  id<MTLFunction> fn =
      [lib newFunctionWithName:[NSString stringWithUTF8String:entry]];
  if (fn == nil) {
    fprintf(stderr, "FATAL entry %s missing\n", entry);
    exit(2);
  }
  id<MTLComputePipelineState> pso =
      [dev newComputePipelineStateWithFunction:fn error:&err];
  if (pso == nil) {
    fprintf(stderr, "FATAL pso %s: %s\n", entry,
            err.localizedDescription.UTF8String);
    exit(2);
  }
  return pso;
}

// One reduce dispatch. tg_mem > 0 arms the baseline's [[threadgroup(0)]]
// scratch pointer; the subgroup arm declares its own threadgroup array.
// Answers the GPU-timestamp span in nanoseconds; host_ns is submit->done.
static double run_dispatch(id<MTLCommandQueue> q, id<MTLComputePipelineState> pso,
                            id<MTLBuffer> x, id<MTLBuffer> parts, id<MTLBuffer> nbuf,
                            NSUInteger num_groups, size_t tg_mem, double *host_ns) {
  id<MTLCommandBuffer> cb = [q commandBuffer];
  id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoder];
  [enc setComputePipelineState:pso];
  [enc setBuffer:x offset:0 atIndex:0];
  [enc setBuffer:parts offset:0 atIndex:1];
  [enc setBuffer:nbuf offset:0 atIndex:2];
  if (tg_mem > 0) {
    [enc setThreadgroupMemoryLength:tg_mem atIndex:0];
  }
  [enc dispatchThreadgroups:MTLSizeMake(num_groups, 1, 1)
      threadsPerThreadgroup:MTLSizeMake(WG, 1, 1)];
  [enc endEncoding];
  double t0 = CACurrentMediaTime();
  [cb commit];
  [cb waitUntilCompleted];
  *host_ns = (CACurrentMediaTime() - t0) * 1e9;
  return (cb.GPUEndTime - cb.GPUStartTime) * 1e9;
}

int main(int argc, char **argv) {
  @autoreleasepool {
    if (argc < 2 || argc > 5) {
      fprintf(stderr, "usage: measure <workdir> [workgroup] [elements] [op-order]\n");
      return 2;
    }
    NSString *dir = [NSString stringWithUTF8String:argv[1]];
    if (argc >= 3) {
      char *end = 0;
      unsigned long w = strtoul(argv[2], &end, 10);
      if (end == argv[2] || *end != '\0' || w < 32ul || w > 1024ul ||
          (w & (w - 1ul)) != 0) {
        fprintf(stderr, "REFUSED workgroup %s: need a power of two in [32, 1024]\n",
                argv[2]);
        return 2;
      }
      WG = (uint32_t)w;
    }
    /* argc >= 4, NOT argc == 4: the driver passes [workdir workgroup
     * elements op-order] (argc 5) since the op-order variable landed, and
     * the == 4 gate silently dropped the shape back to the 1000003 default
     * for every driver run -- found 2026-10-23 by a shape-2 band run whose
     * run-log header read n=1000003 (record: the misshape-defect cells in
     * docs/evidence/gpu-subgroup-reduce-m1max-shape2-band-20261023/). */
    if (argc >= 4) {
      char *end = 0;
      unsigned long e = strtoul(argv[3], &end, 10);
      /* Bound: [1, 2^24] -- the input buffer is 4n bytes and the CPU
       * reference loop is O(n) per operator per run. */
      if (end == argv[3] || *end != '\0' || e < 1ul || e > 16777216ul) {
        fprintf(stderr, "REFUSED elements %s: need an integer in [1, 16777216]\n",
                argv[3]);
        return 2;
      }
      N = (uint32_t)e;
    }
    /* The operator dispatch order: indices into ops[] below. Default
     * {0,1,2} = sum,max,min (the fixed order every earlier cell used);
     * argv[4] is a comma-separated permutation of sum,max,min. */
    int op_seq[3] = {0, 1, 2};
    /* argc >= 5, NOT argc == 5: the last residual of the exact-match gate
     * class the argc >= 4 comment above names. An == gate is dead the moment
     * a later positional lands behind this one (the usage bound grows, the
     * == gate silently falls back to the default, and the run-log header is
     * the only tell -- exactly how the 2026-10-23 misshape defect hid).
     * Every positional gate in this harness is a >= test; the pin is
     * test/kotoba/compiler/accelerator_variants_test.cljk's
     * the-measure-harness-argv-gates-carry-no-exact-match-class. */
    if (argc >= 5) {
      char buf[64];
      if (strlen(argv[4]) >= sizeof(buf)) {
        fprintf(stderr, "REFUSED op-order %s: need a comma-separated "
                        "permutation of sum,max,min\n", argv[4]);
        return 2;
      }
      strcpy(buf, argv[4]);
      int seen[3] = {0, 0, 0}, got = 0;
      char *save = buf, *tok;
      while ((tok = strsep(&save, ",")) != NULL) {
        int idx = (strcmp(tok, "sum") == 0)   ? 0
                  : (strcmp(tok, "max") == 0) ? 1
                  : (strcmp(tok, "min") == 0) ? 2
                                              : -1;
        if (idx < 0 || seen[idx] || got == 3) {
          fprintf(stderr, "REFUSED op-order %s: need a comma-separated "
                          "permutation of sum,max,min\n", argv[4]);
          return 2;
        }
        seen[idx] = 1;
        op_seq[got++] = idx;
      }
      if (got != 3) {
        fprintf(stderr, "REFUSED op-order %s: need a comma-separated "
                        "permutation of sum,max,min\n", argv[4]);
        return 2;
      }
    }
    const char *ops[3] = {"sum", "max", "min"};
    id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
    if (dev == nil) {
      fprintf(stderr, "FATAL no Metal device\n");
      return 2;
    }
    printf("device=%s\n", dev.name.UTF8String);

    NSUInteger num_groups = (N + WG - 1) / WG;

    // The tested device's reported subgroup size (the instrument kernel
    // reads [[threads_per_simdgroup]] -- what the variant's fold actually
    // sees at runtime on this device).
    id<MTLLibrary> probe_lib = load_lib(dev, dir, @"probe.metallib");
    id<MTLComputePipelineState> probe_pso = pso_for(dev, probe_lib, "probe_sg");
    id<MTLBuffer> probe_out = [dev newBufferWithLength:4
                                               options:MTLResourceStorageModeShared];
    id<MTLCommandQueue> q = [dev newCommandQueue];
    {
      id<MTLCommandBuffer> cb = [q commandBuffer];
      id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoder];
      [enc setComputePipelineState:probe_pso];
      [enc setBuffer:probe_out offset:0 atIndex:0];
      [enc dispatchThreadgroups:MTLSizeMake(1, 1, 1)
          threadsPerThreadgroup:MTLSizeMake(32, 1, 1)];
      [enc endEncoding];
      [cb commit];
      [cb waitUntilCompleted];
    }
    uint32_t sg_size = *(uint32_t *)probe_out.contents;
    printf("simdgroup_size=%u\n", sg_size);
    printf("n=%u\nworkgroup=%u\npairs=%d\nwarmup=%d\n", N, WG, PAIRS, WARMUP);
    printf("op_order=%s,%s,%s\n", ops[op_seq[0]], ops[op_seq[1]],
           ops[op_seq[2]]);
    if (sg_size == 0 || (WG % sg_size) != 0) {
      printf("shape=UNUSABLE (subgroup size does not divide W)\n");
      return 1;
    }

    id<MTLLibrary> base_lib, sub_lib;

    NSString *entry;
    id<MTLBuffer> x = [dev newBufferWithLength:(NSUInteger)N * 4
                                       options:MTLResourceStorageModeShared];
    id<MTLBuffer> parts = [dev newBufferWithLength:(NSUInteger)num_groups * 4
                                           options:MTLResourceStorageModeShared];
    id<MTLBuffer> nbuf = [dev newBufferWithLength:4
                                          options:MTLResourceStorageModeShared];
    float *xs = (float *)x.contents;
    for (uint32_t i = 0; i < N; i++) {
      xs[i] = (float)((lcg_next() >> 8) * (1.0f / 16777216.0f)); /* [0,1) */
    }
    *(uint32_t *)nbuf.contents = N;

    for (int oi = 0; oi < 3; oi++) {
      int op = op_seq[oi];
      entry = [NSString stringWithFormat:@"reduce_%s", ops[op]];
      base_lib = load_lib(dev, dir,
                          [NSString stringWithFormat:@"baseline-%s.metallib", ops[op]]);
      sub_lib = load_lib(dev, dir,
                         [NSString stringWithFormat:@"subgroup-%s.metallib", ops[op]]);
      id<MTLComputePipelineState> pso_base =
          pso_for(dev, base_lib, entry.UTF8String);
      id<MTLComputePipelineState> pso_sub =
          pso_for(dev, sub_lib, entry.UTF8String);
      // The dispatch width must fit what the emitted kernel's pipeline
      // allows (the subgroup arm sizes its threadgroup array from the
      // emitted W -- a source emitted at another W is not this cell).
      if (WG > pso_base.maxTotalThreadsPerThreadgroup ||
          WG > pso_sub.maxTotalThreadsPerThreadgroup) {
        printf("shape=UNUSABLE (W exceeds pipeline maxTotalThreadsPerThreadgroup)\n");
        return 1;
      }

      double host_ns;
      for (int w = 0; w < WARMUP; w++) {
        run_dispatch(q, pso_base, x, parts, nbuf, num_groups, WG * 4, &host_ns);
        run_dispatch(q, pso_sub, x, parts, nbuf, num_groups, 0, &host_ns);
      }
      for (int p = 0; p < PAIRS; p++) {
        // Alternate order within the pair (AB / BA) so drift cannot favor
        // one arm -- the paired-within-run statistic of ADR-0358.
        for (int k = 0; k < 2; k++) {
          int arm = ((p + k) % 2 == 0) ? 0 : 1; /* 0 = baseline, 1 = variant */
          id<MTLComputePipelineState> pso = arm ? pso_sub : pso_base;
          double gpu_ns =
              run_dispatch(q, pso, x, parts, nbuf, num_groups,
                            arm ? 0 : WG * 4, &host_ns);
          printf("sample op=%s pair=%d order=%c arm=%s gpu_ns=%.0f host_ns=%.0f\n",
                 ops[op], p, (p % 2 == 0) ? 'A' : 'B', arm ? "variant" : "baseline",
                 gpu_ns, host_ns);
        }
      }

      // Verified read-back (untimed): both arms' partials against a double
      // CPU reference folded over the same padded-lane shape. :max/:min must
      // agree BIT-FOR-BIT in the ordinary value domain (rule 2); :sum may
      // differ in the low bits, and the observed deviation is reported as
      // data rather than hidden behind a pass/fail alone.
      // Sized from THIS cell's num_groups. The old fixed 3907 was W = 256's
      // group count: W = 32 admits 31251 groups and overflowed the stack
      // here (SIGBUS before any output) -- a named instrument defect, fixed
      // in the low-band sweep tick that found it.
      double *ref = (double *)malloc((size_t)num_groups * sizeof(double));
      float *base_v = (float *)malloc((size_t)num_groups * sizeof(float));
      float *sub_v = (float *)malloc((size_t)num_groups * sizeof(float));
      if (ref == NULL || base_v == NULL || sub_v == NULL) {
        fprintf(stderr, "FATAL out of memory for %u groups\n", num_groups);
        return 2;
      }
      for (uint32_t g = 0; g < num_groups; g++) {
        double acc = (op == 1) ? -INFINITY : (op == 2) ? INFINITY : 0.0;
        for (uint32_t l = 0; l < WG; l++) {
          uint32_t i = g * WG + l;
          double v = (i < N) ? (double)xs[i]
                                  : (op == 1) ? -INFINITY
                                              : (op == 2) ? INFINITY : 0.0;
          if (op == 0) acc += v;
          else if (op == 1) acc = fmax(acc, v);
          else acc = fmin(acc, v);
        }
        ref[g] = acc;
      }
      run_dispatch(q, pso_base, x, parts, nbuf, num_groups, WG * 4, &host_ns);
      memcpy(base_v, parts.contents, num_groups * 4);
      run_dispatch(q, pso_sub, x, parts, nbuf, num_groups, 0, &host_ns);
      memcpy(sub_v, parts.contents, num_groups * 4);

      double max_dev_other = 0.0, max_dev_ref[2] = {0.0, 0.0};
      int exact_other = 1, exact_ref[2] = {1, 1};
      for (uint32_t g = 0; g < num_groups; g++) {
        double dv = fabs((double)base_v[g] - (double)sub_v[g]);
        if (dv > max_dev_other) max_dev_other = dv;
        if (memcmp(&base_v[g], &sub_v[g], 4) != 0) exact_other = 0;
        for (int arm = 0; arm < 2; arm++) {
          float a = arm ? sub_v[g] : base_v[g];
          double dr = fabs((double)a - ref[g]);
          if (dr > max_dev_ref[arm]) max_dev_ref[arm] = dr;
          /* bitwise identity check runs for every operator: for :sum it
             honestly reports 0 (the regrouping moves the low bits), for
             :max/:min rule 2 demands it be 1 */
          float rf = (float)ref[g];
          if (memcmp(&a, &rf, 4) != 0) exact_ref[arm] = 0;
        }
      }
      for (int arm = 0; arm < 2; arm++) {
        int ok = (op == 0)
                     ? (max_dev_ref[arm] < 0.05 && max_dev_other < 0.05)
                     : (exact_ref[arm] && exact_other);
        printf("verify op=%s arm=%s max_abs_vs_ref=%.9g max_abs_vs_other=%.9g "
               "bit_exact_vs_ref=%d bit_exact_vs_other=%d ok=%d\n",
               ops[op], arm ? "variant" : "baseline", max_dev_ref[arm],
               max_dev_other, exact_ref[arm], exact_other, ok);
      }
      free(ref);
      free(base_v);
      free(sub_v);
    }
    return 0;
  }
}
