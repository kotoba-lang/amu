/* kexe_gpu_metal.m — the wire-42 :gpu/compute broker on NATIVE Metal.
 *
 * Co-scientist iteration 1 (JUN-138): the G1 residual (1.39x behind
 * llama-bench tg128) is per-kernel cost through Vulkan-over-MoltenVK
 * (measured ~11 us/kernel against llama.cpp's Metal-native ~5 us). This file
 * replaces tools/kexe_gpu_vulkan.c behind the SAME pipe protocol (the guest
 * and its .kotoba program are unchanged): KEXE_GPU_METAL selects it at build
 * time. PIPELINE maps foo.spv -> foo.msl (same directory) and compiles the
 * MSL source at load time (newLibraryWithSource).
 *
 * Iteration-1 scope: the flat verb set (INFO ALLOC MAP WRITE WRITEDEC READ
 * ZERO PIPELINE BEGIN DISPATCH DISPATCHC SUBMIT) plus BEGINK/REPLAY via
 * re-recording (Metal command buffers are one-shot). Only the kdot Q8_0
 * family has an MSL twin yet (kdot_h2_r1.msl); other PIPELINE requests fail
 * closed with a clear reason.
 *
 * The correctness bar is unchanged: the CPU-reference gate
 * (kdot_check.py vs kdot_ref.py) passes before any speed number is read.
 */
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

/* kgpu_req_pipe / kgpu_resp_pipe / kgpu_broker_active live in kexe_loader.c. */

#define KGPU_MAX_BUFFERS 1024
#define KGPU_MAX_PIPELINES 64
#define KGPU_MAX_KEPT 8
#define KGPU_MAX_DISPATCHES 8192
#define KGPU_STAGING_BYTES (16u * 1024u * 1024u)
/* review P1 (amu #1404): a PIPELINE binds at most this many buffers --
 * struct kgpu_dispatch holds this many handles (the Vulkan backend's
 * KGPU_MAX_BINDINGS, the same bound). */
#define KGPU_MAX_BINDINGS 16
/* review P2: the guest provider receives a gpu answer into a fixed 4 MiB
 * buffer (kexe_loader.c gpu_compute_provider) and refuses a longer one, so
 * no answer may exceed it: READ is bounded by this, not by `cap`. */
#define KGPU_GUEST_ANSWER_BYTES (4u * 1024u * 1024u)

static char kgpu_reason[512];

/* review P1 (amu #1404): a refusal is "!" then the reason -- the guest
 * provider fails closed only on a reply that begins with '!'
 * (kexe_loader.c), so a bare reason would be interned as a successful
 * answer. Reported on stderr the way kexe_gpu_vulkan.c reports it. */
static size_t kgpu_fail(uint8_t *out, size_t cap, const char *reason) {
  if (cap == 0) return 0;
  size_t n = strlen(reason);
  if (n + 1 > cap) n = cap - 1;
  out[0] = '!';
  memcpy(out + 1, reason, n);
  fprintf(stderr, "kexe-loader gpu: %s\n", reason);
  return n + 1;
}
static size_t kgpu_decimal(uint8_t *out, uint64_t value) {
  char b[32]; int w = snprintf(b, sizeof b, "%llu", (unsigned long long)value);
  if (w < 0 || (size_t)w > 20) return 0;
  memcpy(out, b, (size_t)w); return (size_t)w;
}

@interface KgpuMetal : NSObject
@property (nonatomic, strong) id<MTLDevice> device;
@property (nonatomic, strong) id<MTLCommandQueue> queue;
@end
@implementation KgpuMetal
@end

struct kgpu_buffer { int live; id<MTLBuffer> buf; uint64_t size; void *map; };
struct kgpu_dispatch { int pipeline; uint32_t x, y, z; long handles[KGPU_MAX_BINDINGS]; int bindings; };
struct kgpu_pipeline {
  int live; int bindings; id<MTLComputePipelineState> pso;
  /* kept-command-buffer support: the recorded dispatch list */
};
struct kgpu_kept { int live; int count; struct kgpu_dispatch ds[KGPU_MAX_DISPATCHES]; };

static struct {
  KgpuMetal *m;
  struct kgpu_buffer buffers[KGPU_MAX_BUFFERS];
  struct kgpu_pipeline pipelines[KGPU_MAX_PIPELINES];
  struct kgpu_kept kept[KGPU_MAX_KEPT];
  int recording, recording_kept, recorded;
  struct kgpu_dispatch current[KGPU_MAX_DISPATCHES];
  int current_count;
  int ready;
  uint32_t max_wg_x;
} kgpu;

static int kgpu_init(void) {
  if (kgpu.ready) return 0;
  @autoreleasepool {
    KgpuMetal *m = [KgpuMetal new];
    m.device = MTLCreateSystemDefaultDevice();
    if (!m.device) { snprintf(kgpu_reason, sizeof kgpu_reason, "Metal: no device"); return -1; }
    m.queue = [m.device newCommandQueue];
    if (!m.queue) { snprintf(kgpu_reason, sizeof kgpu_reason, "Metal: no queue"); return -1; }
    kgpu.m = m;
    kgpu.max_wg_x = 1024;   /* iteration 1: the INFO string only; query the device limit later */
    kgpu.ready = 1;
    return 0;
  }
}

static struct kgpu_buffer *kgpu_buffer_at(long h) {
  if (h <= 0 || h >= KGPU_MAX_BUFFERS || !kgpu.buffers[h].live) return NULL;
  return &kgpu.buffers[h];
}
static int kgpu_new_buffer(uint64_t bytes, int *out) {
  @autoreleasepool {
    for (int i = 1; i < KGPU_MAX_BUFFERS; i++) {
      if (kgpu.buffers[i].live) continue;
      id<MTLBuffer> b = [kgpu.m.device newBufferWithLength:(NSUInteger)bytes options:MTLResourceStorageModeShared];
      if (!b) { snprintf(kgpu_reason, sizeof kgpu_reason, "Metal: buffer allocation failed"); return -1; }
      kgpu.buffers[i].buf = b; kgpu.buffers[i].size = bytes;
      kgpu.buffers[i].map = [b contents]; kgpu.buffers[i].live = 1;
      *out = i; return 0;
    }
  }
  snprintf(kgpu_reason, sizeof kgpu_reason, "out of buffer handles"); return -1;
}

/* PIPELINE: the .spv name maps to a sibling .msl, compiled at load. */
static int kgpu_new_pipeline(const char *spv_path, uint64_t bindings, int *out) {
  char msl[1024];
  if (bindings == 0 || bindings > KGPU_MAX_BINDINGS) {
    snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE bindings must be 1..%d", KGPU_MAX_BINDINGS);
    return -1;
  }
  size_t n = strlen(spv_path);
  if (n + 2 >= sizeof msl) { snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE path too long"); return -1; }
  memcpy(msl, spv_path, n + 1);
  char *dot = strrchr(msl, '.');
  if (!dot) { snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE: no extension"); return -1; }
  strcpy(dot, ".msl");
  NSError *err = nil;
  NSString *src = [NSString stringWithContentsOfFile:[NSString stringWithUTF8String:msl]
                                            encoding:NSUTF8StringEncoding error:&err];
  if (!src) { snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE cannot read %s", msl); return -1; }
  @autoreleasepool {
    /* Strict IEEE: MSL defaults to fast-math (reassociation + contraction),
     * GLSL is strict — the measured 2.7e-3 cross-backend divergence
     * (kernel-dsl-iteration2) points here. JUN-139 identity contract. */
    MTLCompileOptions *opts = [MTLCompileOptions new];
    opts.fastMathEnabled = NO;
    /* macOS 15 deprecated fastMathEnabled (it may be ignored there) — the
     * modern strict switch is mathMode. Set both for SDK coverage. */
#if defined(MAC_OS_X_VERSION_15_0) && __MAC_OS_X_VERSION_MAX_ALLOWED >= 150000
    if (@available(macOS 15.0, *)) opts.mathMode = MTLMathModeStrict;
#endif
    id<MTLLibrary> lib = [kgpu.m.device newLibraryWithSource:src options:opts error:&err];
    if (!lib) { snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE MSL compile failed: %s",
                         err ? err.localizedDescription.UTF8String : "?"); return -1; }
    /* every MSL twin declares its entry as "kmain" */
    id<MTLFunction> fn = [lib newFunctionWithName:@"kmain"];
    if (!fn) { snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE: no kmain in %s", msl); return -1; }
    id<MTLComputePipelineState> pso = [kgpu.m.device newComputePipelineStateWithFunction:fn error:&err];
    if (!pso) { snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE pso failed: %s",
                         err ? err.localizedDescription.UTF8String : "?"); return -1; }
    for (int i = 1; i < KGPU_MAX_PIPELINES; i++) {
      if (kgpu.pipelines[i].live) continue;
      kgpu.pipelines[i].pso = pso; kgpu.pipelines[i].bindings = (int)bindings;
      kgpu.pipelines[i].live = 1; *out = i; return 0;
    }
  }
  snprintf(kgpu_reason, sizeof kgpu_reason, "out of pipeline handles"); return -1;
}

/* Encode the recorded dispatches into one command buffer and wait. */
static int kgpu_run(struct kgpu_dispatch *ds, int count, uint64_t *ns) {
  @autoreleasepool {
    id<MTLCommandBuffer> cb = [kgpu.m.queue commandBuffer];
    id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoder];
    if (!enc) { snprintf(kgpu_reason, sizeof kgpu_reason, "Metal: no encoder"); return -1; }
    for (int i = 0; i < count; i++) {
      struct kgpu_dispatch *d = &ds[i];
      struct kgpu_pipeline *p = &kgpu.pipelines[d->pipeline];
      [enc setComputePipelineState:p->pso];
      for (int b = 0; b < d->bindings && b < KGPU_MAX_BINDINGS; b++) {
        struct kgpu_buffer *buf = kgpu_buffer_at(d->handles[b]);
        if (!buf) { snprintf(kgpu_reason, sizeof kgpu_reason, "DISPATCH binding %d: no such buffer", b); return -1; }
        [enc setBuffer:buf->buf offset:0 atIndex:b];
      }
      MTLSize grid = MTLSizeMake(d->x, d->y, d->z);
      MTLSize tg = MTLSizeMake(64, 1, 1);   /* the kdot family: local_size_x = 64 */
      [enc dispatchThreadgroups:grid threadsPerThreadgroup:tg];
    }
    [enc endEncoding];
    /* review P1 (amu #1404): the answer is the HOST monotonic time from
     * submit through completion, the metric kexe_gpu_vulkan.c reports
     * (vkQueueSubmit .. vkWaitForFences) -- not the GPU start/end
     * timestamps, which leave out queue submission, scheduling and the
     * wait, and would understate the per-command cost against Vulkan. */
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    [cb commit];
    [cb waitUntilCompleted];
    clock_gettime(CLOCK_MONOTONIC, &t1);
    /* review P2: a command buffer that did not complete (an execution error,
     * e.g. a kernel faulting on a short binding) is a refusal, never a
     * success answering stale output. */
    if (cb.status != MTLCommandBufferStatusCompleted) {
      snprintf(kgpu_reason, sizeof kgpu_reason, "Metal command buffer failed (status %ld): %s",
               (long)cb.status, cb.error ? cb.error.localizedDescription.UTF8String : "no error object");
      return -1;
    }
    if (ns)
      *ns = (uint64_t)(t1.tv_sec - t0.tv_sec) * UINT64_C(1000000000) + (uint64_t)(t1.tv_nsec - t0.tv_nsec);
    return 0;
  }
}

/* ---- the request verbs (formats identical to kexe_gpu_vulkan.c) ---------- */

static int kgpu_hex_nibble(uint8_t c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}
static int kgpu_parse_u64(const char *s, uint64_t *out) {
  char *end; unsigned long long v = strtoull(s, &end, 10);
  if (end == s || *end != 0) return -1;
  *out = (uint64_t)v; return 0;
}
static int kgpu_tokens(const uint8_t *req, size_t len, char *buf, size_t cap, char **tok, int max) {
  if (len == 0 || len >= cap) return -1;
  memcpy(buf, req, len); buf[len] = 0;
  int n = 0; char *p = buf;
  while (n < max) {
    tok[n++] = p;
    char *sp = strchr(p, ' ');
    if (!sp) break;
    *sp = 0; p = sp + 1;
  }
  return n;
}

static size_t kgpu_handle(const uint8_t *req, size_t len, uint8_t *out, size_t cap) {
  static char buf[KGPU_STAGING_BYTES / 4 + 1024];
  char *tok[40];
  int n = kgpu_tokens(req, len, buf, sizeof buf, tok, (int)(sizeof tok / sizeof tok[0]));
  if (n <= 0) return kgpu_fail(out, cap, "empty request");
  if (kgpu_init() != 0) return kgpu_fail(out, cap, kgpu_reason);
  const char *op = tok[0];

  if (strcmp(op, "INFO") == 0) {
    int w = snprintf((char *)out, cap, "%s|1.0.0|%u|1", "Apple Metal (native)",
                     kgpu.max_wg_x);
    return w < 0 ? kgpu_fail(out, cap, "INFO format") : (size_t)w;
  }
  if (strcmp(op, "ALLOC") == 0) {
    uint64_t bytes; int h;
    if (n != 2 || kgpu_parse_u64(tok[1], &bytes) != 0 || bytes == 0)
      return kgpu_fail(out, cap, "ALLOC <bytes>");
    if (kgpu_new_buffer(bytes, &h) != 0) return kgpu_fail(out, cap, kgpu_reason);
    return kgpu_decimal(out, (uint64_t)h);
  }
  if (strcmp(op, "MAP") == 0) {
    if (kgpu.recording) return kgpu_fail(out, cap, "MAP while recording (BEGIN open): finish with SUBMIT first");
    uint64_t offset, length; int h;
    if (n != 4 || kgpu_parse_u64(tok[2], &offset) != 0 || kgpu_parse_u64(tok[3], &length) != 0 || length == 0)
      return kgpu_fail(out, cap, "MAP <path> <offset> <length>");
    int fd = open(tok[1], O_RDONLY);
    if (fd < 0) return kgpu_fail(out, cap, "MAP cannot open the path");
    if (kgpu_new_buffer(length, &h) != 0) { close(fd); return kgpu_fail(out, cap, kgpu_reason); }
    uint8_t *dst = (uint8_t *)kgpu.buffers[h].map;
    uint64_t done = 0;
    while (done < length) {
      ssize_t r = pread(fd, dst + done, (size_t)(length - done), (off_t)(offset + done));
      if (r <= 0) { close(fd); return kgpu_fail(out, cap, "MAP short read"); }
      done += (uint64_t)r;
    }
    close(fd);
    return kgpu_decimal(out, (uint64_t)h);
  }
  if (strcmp(op, "WRITE") == 0) {
    if (kgpu.recording) return kgpu_fail(out, cap, "WRITE while recording (BEGIN open): finish with SUBMIT first");
    uint64_t handle, offset;
    if (n != 4 || kgpu_parse_u64(tok[1], &handle) != 0 || kgpu_parse_u64(tok[2], &offset) != 0)
      return kgpu_fail(out, cap, "WRITE <handle> <offset> <hex>");
    struct kgpu_buffer *b = kgpu_buffer_at((long)handle);
    if (!b) return kgpu_fail(out, cap, "WRITE: no such buffer");
    size_t digits = strlen(tok[3]);
    if ((digits & 1u) != 0) return kgpu_fail(out, cap, "WRITE hex length");
    size_t bytes = digits / 2;
    if (offset > b->size || bytes > b->size - offset) return kgpu_fail(out, cap, "WRITE past the buffer");
    uint8_t *dst = (uint8_t *)b->map + offset;
    for (size_t i = 0; i < bytes; i++) {
      int hi = kgpu_hex_nibble((uint8_t)tok[3][2 * i]), lo = kgpu_hex_nibble((uint8_t)tok[3][2 * i + 1]);
      if (hi < 0 || lo < 0) return kgpu_fail(out, cap, "WRITE hex digit");
      dst[i] = (uint8_t)((hi << 4) | lo);
    }
    out[0] = '1'; return 1;
  }
  if (strcmp(op, "WRITEDEC") == 0) {
    if (kgpu.recording) return kgpu_fail(out, cap, "WRITEDEC while recording");
    uint64_t handle, offset;
    if (n != 4 || kgpu_parse_u64(tok[1], &handle) != 0 || kgpu_parse_u64(tok[2], &offset) != 0)
      return kgpu_fail(out, cap, "WRITEDEC <handle> <offset> <u32,...>");
    struct kgpu_buffer *b = kgpu_buffer_at((long)handle);
    if (!b) return kgpu_fail(out, cap, "WRITEDEC: no such buffer");
    /* review P1 (amu #1404): the offset is checked BEFORE any pointer is
     * formed from it -- `b->size - offset` underflowed for an offset past
     * the buffer and `dst` pointed outside the allocation -- and a list that
     * does not fit is refused whole (as kexe_gpu_vulkan.c does), validated
     * before the first byte is written, never truncated. */
    if (offset > b->size) return kgpu_fail(out, cap, "WRITEDEC past the buffer");
    uint64_t room = b->size - offset;
    uint64_t words = 0; const char *p = tok[3];
    while (*p) {
      char *end; unsigned long long v = strtoull(p, &end, 10);
      if (end == p || v > 0xFFFFFFFFull) return kgpu_fail(out, cap, "WRITEDEC: not a u32");
      if (words + 1 > room / 4) return kgpu_fail(out, cap, "WRITEDEC past the buffer");
      words++;
      if (*end == ',') p = end + 1; else if (*end == 0) p = end; else return kgpu_fail(out, cap, "WRITEDEC separator");
    }
    if (words == 0) return kgpu_fail(out, cap, "WRITEDEC: empty list");
    uint8_t *dst = (uint8_t *)b->map + offset;
    p = tok[3];
    for (uint64_t w = 0; w < words; w++) {
      char *end; unsigned long long v = strtoull(p, &end, 10);
      dst[4 * w] = (uint8_t)(v & 255); dst[4 * w + 1] = (uint8_t)((v >> 8) & 255);
      dst[4 * w + 2] = (uint8_t)((v >> 16) & 255); dst[4 * w + 3] = (uint8_t)((v >> 24) & 255);
      p = (*end == ',') ? end + 1 : end;
    }
    return kgpu_decimal(out, words);
  }
  if (strcmp(op, "READ") == 0) {
    if (kgpu.recording) return kgpu_fail(out, cap, "READ while recording (BEGIN open): finish with SUBMIT first");
    uint64_t handle, offset, length;
    if (n != 4 || kgpu_parse_u64(tok[1], &handle) != 0 || kgpu_parse_u64(tok[2], &offset) != 0 ||
        kgpu_parse_u64(tok[3], &length) != 0) return kgpu_fail(out, cap, "READ <handle> <offset> <length>");
    struct kgpu_buffer *b = kgpu_buffer_at((long)handle);
    if (!b) return kgpu_fail(out, cap, "READ: no such buffer");
    if (offset > b->size || length > b->size - offset) return kgpu_fail(out, cap, "READ past the buffer");
    if (length > KGPU_GUEST_ANSWER_BYTES / 2 || length * 2 > cap)
      return kgpu_fail(out, cap, "READ longer than the guest answer buffer (4 MiB of hex)");
    static const char hex[] = "0123456789abcdef";
    const uint8_t *src = (const uint8_t *)b->map + offset;
    for (uint64_t i = 0; i < length; i++) {
      out[2 * i] = (uint8_t)hex[src[i] >> 4]; out[2 * i + 1] = (uint8_t)hex[src[i] & 15];
    }
    return (size_t)(length * 2);
  }
  if (strcmp(op, "ZERO") == 0) {
    uint64_t handle;
    if (n != 2 || kgpu_parse_u64(tok[1], &handle) != 0) return kgpu_fail(out, cap, "ZERO <handle>");
    struct kgpu_buffer *b = kgpu_buffer_at((long)handle);
    if (!b) return kgpu_fail(out, cap, "ZERO: no such buffer");
    /* review P2 (amu #1404): a host-side clear between BEGIN and SUBMIT
     * would run ahead of every dispatch already recorded; refuse it, as
     * kexe_gpu_vulkan.c does. */
    if (kgpu.recording) return kgpu_fail(out, cap, "ZERO while recording");
    memset(b->map, 0, (size_t)b->size);
    out[0] = '1'; return 1;
  }
  if (strcmp(op, "PIPELINE") == 0) {
    uint64_t bindings; int h;
    if (n != 3 || kgpu_parse_u64(tok[2], &bindings) != 0)
      return kgpu_fail(out, cap, "PIPELINE <spv-path> <bindings>");
    if (kgpu_new_pipeline(tok[1], bindings, &h) != 0) return kgpu_fail(out, cap, kgpu_reason);
    return kgpu_decimal(out, (uint64_t)h);
  }
  if (strcmp(op, "BEGIN") == 0 || strcmp(op, "BEGINK") == 0) {
    uint64_t slot = 0;
    if (op[4] == 'K' && (n != 2 || kgpu_parse_u64(tok[1], &slot) != 0 || slot >= KGPU_MAX_KEPT))
      return kgpu_fail(out, cap, "BEGINK <slot>");
    if (kgpu.recording) return kgpu_fail(out, cap, "BEGIN while recording");
    if (op[4] == 'K' && kgpu.kept[slot].live) return kgpu_fail(out, cap, "BEGINK: slot is kept (DROP it first)");
    kgpu.recording = 1; kgpu.recorded = 0; kgpu.current_count = 0;
    kgpu.recording_kept = (op[4] == 'K') ? (int)slot : -1;
    out[0] = '1'; return 1;
  }
  if (strcmp(op, "DISPATCH") == 0 || strcmp(op, "DISPATCHC") == 0) {
    /* Outside BEGIN..SUBMIT a dispatch runs IMMEDIATELY and answers its ns —
     * the kdot micro-bench measures the single-dispatch time that way (the
     * Vulkan backend has the same semantics). */
    int immediate = !kgpu.recording;
    if (kgpu.current_count >= KGPU_MAX_DISPATCHES) return kgpu_fail(out, cap, "too many dispatches");
    uint64_t pipe, gx, gy, gz;
    if (n < 5 || kgpu_parse_u64(tok[1], &pipe) != 0 || kgpu_parse_u64(tok[2], &gx) != 0 ||
        kgpu_parse_u64(tok[3], &gy) != 0 || kgpu_parse_u64(tok[4], &gz) != 0)
      { static char dbg[1200]; snprintf(dbg, sizeof dbg, "PARSE (n=%d): %.900s", n, (const char *)req); return kgpu_fail(out, cap, dbg); }
    if (pipe == 0 || pipe >= KGPU_MAX_PIPELINES || !kgpu.pipelines[pipe].live)
      return kgpu_fail(out, cap, "DISPATCH: no such pipeline");
    int bindings = kgpu.pipelines[pipe].bindings;
    if (n != 5 + bindings) return kgpu_fail(out, cap, "DISPATCH: handle count != pipeline bindings");
    struct kgpu_dispatch *d = &kgpu.current[kgpu.current_count++];
    d->pipeline = (int)pipe; d->x = (uint32_t)gx; d->y = (uint32_t)gy; d->z = (uint32_t)gz;
    d->bindings = bindings;
    for (int b = 0; b < bindings; b++) {
      uint64_t h;
      if (kgpu_parse_u64(tok[5 + b], &h) != 0) return kgpu_fail(out, cap, "DISPATCH: bad handle");
      d->handles[b] = (long)h;
    }
    kgpu.recorded++;
    if (immediate) {
      uint64_t ns = 0;
      if (kgpu_run(d, 1, &ns) != 0) { kgpu.current_count--; return kgpu_fail(out, cap, kgpu_reason); }
      kgpu.current_count--;
      return kgpu_decimal(out, ns);
    }
    out[0] = '1'; return 1;
  }
  if (strcmp(op, "SUBMIT") == 0) {
    if (!kgpu.recording) return kgpu_fail(out, cap, "SUBMIT without BEGIN");
    uint64_t ns = 0;
    if (kgpu_run(kgpu.current, kgpu.current_count, &ns) != 0) return kgpu_fail(out, cap, kgpu_reason);
    if (kgpu.recording_kept >= 0) {
      struct kgpu_kept *k = &kgpu.kept[kgpu.recording_kept];
      k->count = kgpu.current_count; memcpy(k->ds, kgpu.current, sizeof(struct kgpu_dispatch) * (size_t)kgpu.current_count);
      k->live = 1;
    }
    kgpu.recording = 0; kgpu.recording_kept = -1;
    return kgpu_decimal(out, ns);
  }
  if (strcmp(op, "REPLAY") == 0) {
    uint64_t slot;
    if (n != 2 || kgpu_parse_u64(tok[1], &slot) != 0 || slot >= KGPU_MAX_KEPT)
      return kgpu_fail(out, cap, "REPLAY <slot>");
    if (kgpu.recording) return kgpu_fail(out, cap, "REPLAY while recording");
    struct kgpu_kept *k = &kgpu.kept[slot];
    if (!k->live || k->count == 0) return kgpu_fail(out, cap, "REPLAY: slot holds nothing");
    uint64_t ns = 0;
    if (kgpu_run(k->ds, k->count, &ns) != 0) return kgpu_fail(out, cap, kgpu_reason);
    return kgpu_decimal(out, ns);
  }
  if (strcmp(op, "DROP") == 0) {
    uint64_t slot;
    if (n != 2 || kgpu_parse_u64(tok[1], &slot) != 0 || slot >= KGPU_MAX_KEPT)
      return kgpu_fail(out, cap, "DROP <slot>");
    kgpu.kept[slot].live = 0;
    out[0] = '1'; return 1;
  }
  return kgpu_fail(out, cap, "unknown gpu request");
}

/* ---- the broker: supervisor side (framing identical to the Vulkan one) ---- */

static int kgpu_read_all(int fd, uint8_t *dst, size_t len) {
  size_t got = 0;
  while (got < len) {
    ssize_t r = read(fd, dst + got, len - got);
    if (r == 0) return -1;
    if (r < 0) { if (errno == EINTR) continue; return -1; }
    got += (size_t)r;
  }
  return 0;
}
static int kgpu_write_all(int fd, const uint8_t *src, size_t len) {
  size_t put = 0;
  while (put < len) {
    ssize_t w = write(fd, src + put, len - put);
    if (w < 0) { if (errno == EINTR) continue; return -1; }
    put += (size_t)w;
  }
  return 0;
}
static int kgpu_serve_one(int req_fd, int resp_fd) {
  static uint8_t request[KGPU_STAGING_BYTES * 2 + 64];
  static uint8_t answer[KGPU_STAGING_BYTES * 2 + 64];
  uint8_t header[4];
  if (kgpu_read_all(req_fd, header, 4) != 0) return -1;
  uint32_t len = (uint32_t)header[0] | ((uint32_t)header[1] << 8) | ((uint32_t)header[2] << 16) | ((uint32_t)header[3] << 24);
  if (len > sizeof request) return -1;
  if (kgpu_read_all(req_fd, request, len) != 0) return -1;
  size_t alen = kgpu_handle(request, len, answer, sizeof answer);
  uint8_t ahead[4] = { (uint8_t)alen, (uint8_t)(alen >> 8), (uint8_t)(alen >> 16), (uint8_t)(alen >> 24) };
  if (kgpu_write_all(resp_fd, ahead, 4) != 0) return -1;
  if (kgpu_write_all(resp_fd, answer, alen) != 0) return -1;
  return 0;
}
static void kgpu_shutdown(void) {
  for (int i = 1; i < KGPU_MAX_BUFFERS; i++) kgpu.buffers[i].live = 0;
  for (int i = 1; i < KGPU_MAX_PIPELINES; i++) kgpu.pipelines[i].live = 0;
  kgpu.ready = 0;
}
