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
//   measure <workdir>
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

#define N_ELEM 1000003u /* not a multiple of WG: padded lanes exercised */
#define WG 256u         /* the measured Apple workgroup row (ADR-0358) */
#define PAIRS 20        /* interleaved pairs per operator per process */
#define WARMUP 2        /* discarded submits per arm */

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
    if (argc != 2) {
      fprintf(stderr, "usage: measure <workdir>\n");
      return 2;
    }
    NSString *dir = [NSString stringWithUTF8String:argv[1]];
    id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
    if (dev == nil) {
      fprintf(stderr, "FATAL no Metal device\n");
      return 2;
    }
    printf("device=%s\n", dev.name.UTF8String);

    NSUInteger num_groups = (N_ELEM + WG - 1) / WG;

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
    printf("n=%u\nworkgroup=%u\npairs=%d\nwarmup=%d\n", N_ELEM, WG, PAIRS, WARMUP);
    if (sg_size == 0 || (WG % sg_size) != 0) {
      printf("shape=UNUSABLE (subgroup size does not divide W)\n");
      return 1;
    }

    id<MTLLibrary> base_lib, sub_lib;

    const char *ops[3] = {"sum", "max", "min"};
    NSString *entry;
    id<MTLBuffer> x = [dev newBufferWithLength:(NSUInteger)N_ELEM * 4
                                       options:MTLResourceStorageModeShared];
    id<MTLBuffer> parts = [dev newBufferWithLength:(NSUInteger)num_groups * 4
                                           options:MTLResourceStorageModeShared];
    id<MTLBuffer> nbuf = [dev newBufferWithLength:4
                                          options:MTLResourceStorageModeShared];
    float *xs = (float *)x.contents;
    for (uint32_t i = 0; i < N_ELEM; i++) {
      xs[i] = (float)((lcg_next() >> 8) * (1.0f / 16777216.0f)); /* [0,1) */
    }
    *(uint32_t *)nbuf.contents = N_ELEM;

    for (int op = 0; op < 3; op++) {
      entry = [NSString stringWithFormat:@"reduce_%s", ops[op]];
      base_lib = load_lib(dev, dir,
                          [NSString stringWithFormat:@"baseline-%s.metallib", ops[op]]);
      sub_lib = load_lib(dev, dir,
                         [NSString stringWithFormat:@"subgroup-%s.metallib", ops[op]]);
      id<MTLComputePipelineState> pso_base =
          pso_for(dev, base_lib, entry.UTF8String);
      id<MTLComputePipelineState> pso_sub =
          pso_for(dev, sub_lib, entry.UTF8String);

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
      double ref[3907];
      float base_v[3907], sub_v[3907];
      for (uint32_t g = 0; g < num_groups; g++) {
        double acc = (op == 1) ? -INFINITY : (op == 2) ? INFINITY : 0.0;
        for (uint32_t l = 0; l < WG; l++) {
          uint32_t i = g * WG + l;
          double v = (i < N_ELEM) ? (double)xs[i]
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
    }
    return 0;
  }
}
