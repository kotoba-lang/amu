// MEASUREMENT INSTRUMENT (JUN-58): the "counters" channel -- per-dispatch
// GPU-core time of ONE reduce dispatch on this host's Apple GPU, as the delta
// of two GPUTimestamp counter samples bracketing the dispatch, in GPU ns.
//
// This is NOT repository product code and NOT a wire-42 route. The amu
// runtime executes :gpu/compute through wire 42, which has had no route since
// the C loader removal (ADR 0371); this harness dispatches the emitter's own
// MSL output (the same workdir contract as
// scripts/gpu-subgroup-reduce-metal-measure.m) through the Metal API
// directly. The claim-protocol channel is ADR-0360's 2026-10-25 counter-
// channel amendment; the BRACKET METHOD is that amendment's letter AS
// CORRECTED by the harness-row probe (record:
// docs/evidence/gpu/metal-counter-channel-harness-20261025.txt):
//
//   * The design letter named the COMPUTE ENCODER's
//     sampleCountersInBuffer:atSampleIndex:withBarrier: (before/after the
//     dispatch). REFUTED live on this host: the Metal framework asserts
//     "MTLComputeCommandEncoder:sampleCountersInBuffer:atSampleIndex:
//     withBarrier not supported on this device" and ABORTS at encode time
//     (SIGABRT) -- MTLCounterSamplingPointAtDispatchBoundary is unsupported
//     here, and the SDK ties that method to that sampling point.
//   * The measured sampling-point matrix on this M1 Max is
//     dispatch=0 stage=1 draw=0 tile=0 blit=0 (probe v1) -- only
//     AtStageBoundary is supported.
//   * The bracket this harness uses is the AtStageBoundary route the device
//     supports: the compute pass sample-buffer attachment's
//     startOfEncoderSampleIndex / endOfEncoderSampleIndex -- the sample taken
//     at the start and at the end of command encoder processing -- with
//     EXACTLY ONE dispatch inside the compute encoder, so the sample pair
//     brackets that dispatch. Resolved via the blit encoder's
//     resolveCounters:inRange:destinationBuffer:destinationOffset:, read back
//     as two MTLCounterResultTimestamp uint64 values (GPU ns), the pair's
//     delta being the sample line's counter_ns.
//
// Whether that delta equals the dispatch's GPU time or carries sampling /
// encoder-boundary overhead is UNMEASURED -- the measurement row's own
// calibration question (ADR-0360's letter). Nothing in this file answers it.
// The instrument's own smoke run is INSTRUMENT VERIFICATION ONLY: its numbers
// are not an arm-vs-arm answer and not a claim-protocol record (no rule-1 /
// rule-2 publication here -- those ride the measurement row).
//
// Protocol (unchanged from the MSL campaign instrument -- ADR-0358):
// fresh-process runs, interleaved paired samples with alternating order,
// first submits discarded as warmup, verified read-back of the partials the
// kernels produce.
//
//   counters <workdir> [workgroup] [elements] [op-order] [variant-prefix]
//
// Positional semantics, argv gates and the workdir contract are byte-for-byte
// the measure instrument's (see its header): [workgroup] W, default 256;
// [elements] n, default 1000003; [op-order] a comma-separated permutation of
// sum,max,min; [variant-prefix] the variant arm's metallib prefix, default
// "subgroup". <workdir> must contain baseline-<op>.metallib and
// <prefix>-<op>.metallib for op in {sum, max, min} (entry reduce_<op>) and
// probe.metallib (entry probe_sg, the [[threads_per_simdgroup]] reporter).
// Every positional gate is a >= test (the misshape class is pinned out by
// test/kotoba/compiler/accelerator_variants_test.cljk).
//
// Output is machine-readable lines on stdout: the header block above the
// samples names the channel and the sampling-point matrix; each sample line
// carries the bracket's raw pair and delta
// (`sample op=.. pair=.. order=.. arm=.. ts0=.. ts1=.. counter_ns=..`; on an
// unresolved sample MTLCounterErrorValue the delta prints as ERR); the
// read-back block is the measure instrument's `verify` lines. All input
// values are in [0, 1): no NaN payloads and no negative zeros, i.e. rule 2's
// ordinary value domain (ADR-0356).

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

// One reduce dispatch, bracketed by the compute pass's start/end-of-encoder
// GPUTimestamp samples (the AtStageBoundary route; see the header). Answers
// the pair's raw timestamps and the delta; *unresolved is set when either
// sample resolved to MTLCounterErrorValue (the delta is then meaningless).
static double run_bracket(id<MTLCommandQueue> q, id<MTLComputePipelineState> pso,
                          id<MTLBuffer> x, id<MTLBuffer> parts, id<MTLBuffer> nbuf,
                          id<MTLCounterSampleBuffer> sb, id<MTLBuffer> resolved,
                          NSUInteger num_groups, size_t tg_mem,
                          uint64_t *ts0, uint64_t *ts1, int *unresolved) {
  MTLComputePassDescriptor *pd = [MTLComputePassDescriptor new];
  MTLComputePassSampleBufferAttachmentDescriptor *att = pd.sampleBufferAttachments[0];
  att.sampleBuffer = sb;
  att.startOfEncoderSampleIndex = 0;
  att.endOfEncoderSampleIndex = 1;
  id<MTLCommandBuffer> cb = [q commandBuffer];
  id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoderWithDescriptor:pd];
  if (enc == nil) {
    fprintf(stderr, "FATAL computeCommandEncoderWithDescriptor returned nil\n");
    exit(2);
  }
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
  [cb commit];
  [cb waitUntilCompleted];
  if (cb.error != nil) {
    fprintf(stderr, "FATAL compute cb error: %s\n",
            cb.error.localizedDescription.UTF8String);
    exit(2);
  }
  // Resolve the pair (indices 0..2) in a following command buffer -- the
  // verified probe idiom (a separate cb, ordered after the samples land).
  id<MTLCommandBuffer> rcb = [q commandBuffer];
  id<MTLBlitCommandEncoder> blit = [rcb blitCommandEncoder];
  [blit resolveCounters:sb inRange:NSMakeRange(0, 2)
        destinationBuffer:resolved destinationOffset:0];
  [blit endEncoding];
  [rcb commit];
  [rcb waitUntilCompleted];
  if (rcb.error != nil) {
    fprintf(stderr, "FATAL resolve cb error: %s\n",
            rcb.error.localizedDescription.UTF8String);
    exit(2);
  }
  uint64_t *r = (uint64_t *)resolved.contents;
  *ts0 = r[0];
  *ts1 = r[1];
  *unresolved = (r[0] == MTLCounterErrorValue || r[1] == MTLCounterErrorValue);
  return (double)(r[1] - r[0]);
}

// Untimed correctness dispatch (the read-back block's): plain compute encoder,
// no counter sampling -- this channel's samples answer only timed brackets.
static void run_plain(id<MTLCommandQueue> q, id<MTLComputePipelineState> pso,
                      id<MTLBuffer> x, id<MTLBuffer> parts, id<MTLBuffer> nbuf,
                      NSUInteger num_groups, size_t tg_mem) {
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
  [cb commit];
  [cb waitUntilCompleted];
}

int main(int argc, char **argv) {
  @autoreleasepool {
    if (argc < 2 || argc > 6) {
      fprintf(stderr, "usage: counters <workdir> [workgroup] [elements] [op-order] [variant-prefix]\n");
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
    /* Every positional gate is a >= test, never an exact-match (argc == N)
     * gate -- the misshape class the measure instrument's 2026-10-23 defect
     * named (an == gate dies silently the moment a later positional lands
     * behind it). Pinned by
     * test/kotoba/compiler/accelerator_variants_test.cljk. */
    if (argc >= 4) {
      char *end = 0;
      unsigned long e = strtoul(argv[3], &end, 10);
      if (end == argv[3] || *end != '\0' || e < 1ul || e > 16777216ul) {
        fprintf(stderr, "REFUSED elements %s: need an integer in [1, 16777216]\n",
                argv[3]);
        return 2;
      }
      N = (uint32_t)e;
    }
    int op_seq[3] = {0, 1, 2};
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
    NSString *variant_prefix = @"subgroup";
    if (argc >= 6) {
      if (strlen(argv[5]) == 0 || strlen(argv[5]) > 32) {
        fprintf(stderr, "REFUSED variant-prefix %s: need a non-empty label\n",
                argv[5]);
        return 2;
      }
      variant_prefix = [NSString stringWithUTF8String:argv[5]];
    }
    id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
    if (dev == nil) {
      fprintf(stderr, "FATAL no Metal device\n");
      return 2;
    }
    printf("device=%s\n", dev.name.UTF8String);
    printf("channel=counters (GPUTimestamp counter-sample delta, GPU ns; "
           "one dispatch per compute encoder bracketed by "
           "MTLComputePassSampleBufferAttachment startOfEncoderSampleIndex/"
           "endOfEncoderSampleIndex -- the AtStageBoundary route)\n");
    printf("sampling_points dispatch=%d stage=%d draw=%d tile=%d blit=%d\n",
           [dev supportsCounterSampling:MTLCounterSamplingPointAtDispatchBoundary],
           [dev supportsCounterSampling:MTLCounterSamplingPointAtStageBoundary],
           [dev supportsCounterSampling:MTLCounterSamplingPointAtDrawBoundary],
           [dev supportsCounterSampling:MTLCounterSamplingPointAtTileDispatchBoundary],
           [dev supportsCounterSampling:MTLCounterSamplingPointAtBlitBoundary]);

    // The timestamp counter set + its sample buffer (2 samples per bracket).
    MTLCounterSampleBufferDescriptor *d = [MTLCounterSampleBufferDescriptor new];
    id<MTLCounterSet> ts = nil;
    for (id<MTLCounterSet> cs in dev.counterSets)
      if ([cs.name.lowercaseString containsString:@"timestamp"]) ts = cs;
    if (ts == nil) {
      fprintf(stderr, "FATAL no timestamp counter set on this device\n");
      return 2;
    }
    d.counterSet = ts;
    d.sampleCount = 2;
    d.storageMode = MTLStorageModeShared;
    NSError *cserr = nil;
    id<MTLCounterSampleBuffer> sb =
        [dev newCounterSampleBufferWithDescriptor:d error:&cserr];
    if (sb == nil) {
      fprintf(stderr, "FATAL counter sample buffer: %s\n",
              cserr.localizedDescription.UTF8String);
      return 2;
    }
    id<MTLBuffer> resolved = [dev newBufferWithLength:16
                                              options:MTLResourceStorageModeShared];

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
                         [NSString stringWithFormat:@"%@-%s.metallib",
                              variant_prefix, ops[op]]);
      id<MTLComputePipelineState> pso_base =
          pso_for(dev, base_lib, entry.UTF8String);
      id<MTLComputePipelineState> pso_sub =
          pso_for(dev, sub_lib, entry.UTF8String);
      if (WG > pso_base.maxTotalThreadsPerThreadgroup ||
          WG > pso_sub.maxTotalThreadsPerThreadgroup) {
        printf("shape=UNUSABLE (W exceeds pipeline maxTotalThreadsPerThreadgroup)\n");
        return 1;
      }

      uint64_t ts0, ts1;
      int unresolved;
      for (int w = 0; w < WARMUP; w++) {
        run_bracket(q, pso_base, x, parts, nbuf, sb, resolved, num_groups,
                    WG * 4, &ts0, &ts1, &unresolved);
        run_bracket(q, pso_sub, x, parts, nbuf, sb, resolved, num_groups, 0,
                    &ts0, &ts1, &unresolved);
      }
      for (int p = 0; p < PAIRS; p++) {
        // Alternate order within the pair (AB / BA) so drift cannot favor
        // one arm -- the paired-within-run statistic of ADR-0358.
        for (int k = 0; k < 2; k++) {
          int arm = ((p + k) % 2 == 0) ? 0 : 1; /* 0 = baseline, 1 = variant */
          id<MTLComputePipelineState> pso = arm ? pso_sub : pso_base;
          double delta = run_bracket(q, pso, x, parts, nbuf, sb, resolved,
                                     num_groups, arm ? 0 : WG * 4,
                                     &ts0, &ts1, &unresolved);
          if (unresolved) {
            printf("sample op=%s pair=%d order=%c arm=%s ts0=%llu ts1=%llu "
                   "counter_ns=ERR\n",
                   ops[op], p, (p % 2 == 0) ? 'A' : 'B',
                   arm ? "variant" : "baseline",
                   (unsigned long long)ts0, (unsigned long long)ts1);
          } else {
            printf("sample op=%s pair=%d order=%c arm=%s ts0=%llu ts1=%llu "
                   "counter_ns=%.0f\n",
                   ops[op], p, (p % 2 == 0) ? 'A' : 'B',
                   arm ? "variant" : "baseline",
                   (unsigned long long)ts0, (unsigned long long)ts1, delta);
          }
        }
      }

      // Verified read-back (untimed): both arms' partials against a double
      // CPU reference folded over the same padded-lane shape. :max/:min must
      // agree BIT-FOR-BIT in the ordinary value domain (rule 2); :sum may
      // differ in the low bits, and the observed deviation is reported as
      // data rather than hidden behind a pass/fail alone.
      double *ref = (double *)malloc((size_t)num_groups * sizeof(double));
      float *base_v = (float *)malloc((size_t)num_groups * sizeof(float));
      float *sub_v = (float *)malloc((size_t)num_groups * sizeof(float));
      if (ref == NULL || base_v == NULL || sub_v == NULL) {
        fprintf(stderr, "FATAL out of memory for %lu groups\n",
                (unsigned long)num_groups);
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
      run_plain(q, pso_base, x, parts, nbuf, num_groups, WG * 4);
      memcpy(base_v, parts.contents, num_groups * 4);
      run_plain(q, pso_sub, x, parts, nbuf, num_groups, 0);
      memcpy(sub_v, parts.contents, num_groups * 4);

      double max_dev_other = 0.0, max_dev_ref[2] = {0.0, 0.0};
      int exact_other = 1, exact_ref[2] = {1, 1};
      for (uint32_t g = 0; g < num_groups; g++) {
        double dv = fabs((double)base_v[g] - (double)sub_v[g]);
        if (dv > max_dev_other) max_dev_other = dv;
        if (memcmp(&base_v[g], &sub_v[g], 4) != 0) exact_other = 0;
        for (int arm = 0; arm < 2; arm++) {
          float a = arm ? sub_v[g] : base_v[g];
          double dr = fabs((double)a - (double)ref[g]);
          if (dr > max_dev_ref[arm]) max_dev_ref[arm] = dr;
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
