/* gpu-subgroup-reduce-anv-causeprobe.c -- JUN-59 s243: THE CAUSE-RESOLUTION
 * ACT'S INSTRUMENT (ARM-Z1 / ARM-Z2 / ARM-H probe rows added to the named
 * Vulkan instrument family).  IMPLEMENTATION + CAPTURE ONLY, NO runs, NO
 * measurement claims.  Every act quantity stays UNMEASURED until the act's
 * measurement half runs on aiueos-6600hs under the FROZEN protocol
 * docs/evidence/gpu/anv-b3causeprereg-20261103/protocol.txt (16,913 bytes,
 * sha256 f1d500623a98693c71c3a04e4b29f15f86fda2069cf832f0de7f6ad82380f709).
 *
 * DERIVED FROM gpu-subgroup-reduce-anv-subgroupsize-batch.c (the committed
 * v2-batch64 family base, archived at
 * docs/evidence/gpu/anv-instrument-source-snapshots-20261027/
 * gpu-subgroup-reduce-anv-subgroupsize-batch.c.txt, 27,780 bytes, sha256
 * 34d56fa11831cbb3ea0ef61a5580f10689ae6af25f15912d731182e6efd51e06).
 * NAMED RECONSTRUCTION RESIDUAL: the c2 control-stream build that produced
 * the committed c2 run logs (the build carrying the barrier_n/work_mul/ndiv
 * knob surface) has NO committed source -- no committed .c file anywhere in
 * the chain history carries work_mul/barrier_n (git pickaxe over all
 * revisions).  This instrument is therefore a RECONSTRUCTION of the c2
 * build's OBSERVABLE contract from committed run-log byte forms bound by
 * impl-verify-s243.py: header metadata (7 '#' lines) byte-identical, CELL /
 * SAMPLE / VERIFY row forms byte-identical, the per-round cell order
 * algorithm (seeded Fisher-Yates, lcg_state = SEED + round, in-place over
 * the 24-cell map, pipeline-FAIL cells skipped) byte-reproduced against
 * every round of every committed c2 run log, and the knob formula
 * n = floor(N_ELEMENTS * work_mul / ndiv) re-derived against every committed
 * knob-bearing run-log header.  The x-corpus initialization is carried
 * byte-identical from the family base; the committed run logs do not record
 * corpus bytes, so corpus identity with the c2 build is UNVERIFIABLE from
 * committed bytes (named residual, not hidden).
 *
 * THE ACT (protocol section 4): the act's instrument is a NEW build of this
 * family -- ARM-K sample-row semantics byte-preserved, plus three probe
 * arms whose rows ride INSIDE the same run logs:
 *   ARM-Z1  zero-work timestamp pair (channel=zwts) at round start before
 *           any dispatch: two vkCmdWriteTimestamp calls back to back, same
 *           pipeline stage, NO command between them.
 *   ARM-Z2  empty-barrier timestamp pair (channel=zwbar) placed immediately
 *           after ARM-Z1: vkCmdWriteTimestamp (TOP_OF_PIPE), one
 *           vkCmdPipelineBarrier with no memory/execution dependencies
 *           beyond the barrier itself, vkCmdWriteTimestamp
 *           (BOTTOM_OF_PIPE).
 *   ARM-K   the committed c2 control stream unchanged in the middle of the
 *           round (the committed per-round cell order, byte-preserved rows).
 *   ARM-H   one isolated single dispatch (batch=1) of the reading-cell
 *           kernel at round end, timed on the host with CLOCK_MONOTONIC_RAW
 *           around submit->completion by busy polling (channel=isohost,
 *           REPORT-ONLY, no branch authority).
 * PROBE PLACEMENT (protocol section 4, frozen): Z1, Z2 at round start (in
 * that order), the ARM-K stream in the middle in committed order, H at
 * round end.  Placement effects are UNMEASURED (protocol L4).
 *
 * The instrument identity line is printed BYTE-IDENTICAL to the committed
 * c2 run-log header because the frozen protocol (section 1c) REQUIRES the
 * act's ARM-K to reproduce that metadata exactly; the build difference of
 * this instrument is pinned by the measuring session's first-measured
 * binary digests (protocol section 5, L3), never by the header.
 *
 * MEASUREMENT INSTRUMENT, NOT PRODUCT CODE, NOT THE WIRE-42 LOADER PATH.
 *
 * Output (stdout, line-oriented, parsed verbatim into evidence):
 *   # key=value            -- identity, device facts, protocol constants
 *   CELL idx=.. spv=.. op=.. wg=.. forced=.. probe_size=.. probe_nsub=..
 *        probe_wg=.. pipeline=ok|FAIL void=0|1 void_reason=..
 *   PROBE round=.. channel=zwts ticks=..     (ARM-Z1, round start)
 *   PROBE round=.. channel=zwbar ticks=..    (ARM-Z2, right after Z1)
 *   SAMPLE round=.. idx=.. batch=.. work_mul=.. ndiv=.. gpu_ticks=..
 *        gpu_ns=.. per_dispatch_ns=.. host_ns=..   (ARM-K, committed form)
 *   PROBE round=.. channel=isohost raw_ns=.. (ARM-H, round end)
 *   VERIFY idx=.. checked=.. mismatch=.. ok=0|1
 *
 * Build (the measuring session records the first-measured digests):
 *   gcc -O2 -o anv-causeprobe gpu-subgroup-reduce-anv-causeprobe.c -lvulkan
 *
 * Usage: ./anv-causeprobe <manifest.txt>
 * Manifest line: <measured.spv> <W> <S|default> <op> <probe.spv>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <vulkan/vulkan.h>

#define MAX_CELLS 64
#define N_ELEMENTS 1000003u
#define PARTS_CAP 8192u

/* The act's FROZEN knob set (protocol section 4 ARM-K): the committed c2
 * control stream's knobs exactly -- n=1000003 rounds=6400 warmup=3 batch=2
 * barrier_n=0 work_mul=1 ndiv=1 seed=20261027.  At this set the knob
 * formula below degenerates to n = N_ELEMENTS, so no reconstruction choice
 * can affect any act byte. */
#define ROUNDS 6400
#define WARMUP 3
#define BATCH 2
#define BARRIER_N 0
#define WORK_MUL 1
#define NDIV 1
#define SEED 20261027u

typedef struct {
    char spv[512];
    char probe_spv[512];
    char op[16];
    uint32_t wg;
    int forced;             /* -1 = default (no forcing) */
    uint32_t groups;        /* dispatch group count */
    VkShaderModule module;
    VkShaderModule probe_module;
    VkPipeline pipeline;
    VkPipeline probe_pipeline;
    int pipeline_ok;
    int probe_size;
    int probe_nsub;
    int probe_wg;
    int void_cell;
    char void_reason[128];
} Cell;

static VkInstance instance;
static VkPhysicalDevice phys;
static VkDevice device;
static VkQueue queue;
static uint32_t qfamily;
static VkCommandPool cmdpool;
static VkQueryPool querypool;   /* 6 queries: 0-1 ARM-K, 2-3 ARM-Z1, 4-5 ARM-Z2 */
static VkDescriptorSetLayout dsl;        /* 3 storage buffers */
static VkDescriptorSetLayout probe_dsl;  /* 1 storage buffer */
static VkPipelineLayout playout;
static VkPipelineLayout probe_playout;
static VkDescriptorPool dpool;
static VkDescriptorSet dset;
static VkDescriptorSet probe_dset;
static VkFence isohost_fence;  /* ARM-H busy-poll fence, reused per round */

static VkBuffer xbuf, partsbuf, nbuf, obuf;
static VkDeviceMemory xm, pm, nm, om;
static float *xhost;
static float *phost;    /* partsbuf, persistently mapped at startup */
static uint32_t *ohost; /* obuf, persistently mapped at startup */
static uint32_t nparts;

static float device_name[128]; /* unused placeholder to keep layout obvious */
/* gpu_devname: the base's 'devname' renamed -- macOS <stdlib.h> declares a
 * devname(dev_t, mode_t) function and the local syntax gate would collide.
 * Internal identifier only; no output byte is affected (named deviation
 * from the family base source). */
static char gpu_devname[256];
static uint32_t dev_vendor = 0, dev_device = 0, dev_api = 0;
static float timestamp_period = 0.0f;
static int timestamp_compute_graphics = 0;
static uint32_t subgroup_size_reported = 0;
static uint32_t min_sub = 0, max_sub = 0;
static int size_control_feature = 0, size_control_full = 0;
static uint32_t required_stages = 0;

static void die(const char *msg) {
    fprintf(stderr, "FATAL: %s\n", msg);
    exit(1);
}

static void vkchk(VkResult r, const char *what) {
    if (r != VK_SUCCESS) {
        fprintf(stderr, "FATAL: %s -> VkResult %d\n", what, (int)r);
        exit(1);
    }
}

static uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

/* ARM-H ONLY: the protocol's frozen host clock for channel=isohost is
 * CLOCK_MONOTONIC_RAW (protocol section 4); ARM-K's host_ns keeps the
 * committed CLOCK_MONOTONIC (now_ns) byte-preserved. */
static uint64_t now_raw_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

static uint32_t lcg_state;
static uint32_t lcg_next(void) {
    lcg_state = lcg_state * 1664525u + 1013904223u;
    return lcg_state;
}

static uint32_t *read_file(const char *path, size_t *words) {
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "FATAL: cannot open %s\n", path); exit(1); }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz % 4 != 0) die("SPIR-V file size not a multiple of 4");
    uint32_t *buf = (uint32_t *)malloc((size_t)sz);
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) die("short read");
    fclose(f);
    *words = (size_t)sz / 4;
    return buf;
}

static VkShaderModule load_module(const char *path) {
    size_t words;
    uint32_t *code = read_file(path, &words);
    VkShaderModuleCreateInfo ci;
    memset(&ci, 0, sizeof ci);
    ci.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    ci.codeSize = words * 4;
    ci.pCode = code;
    VkShaderModule m;
    vkchk(vkCreateShaderModule(device, &ci, NULL, &m), "vkCreateShaderModule");
    free(code);
    return m;
}

static uint32_t find_memory(uint32_t bits) {
    VkPhysicalDeviceMemoryProperties mp;
    vkGetPhysicalDeviceMemoryProperties(phys, &mp);
    for (uint32_t i = 0; i < mp.memoryTypeCount; i++) {
        if ((bits & (1u << i)) &&
            (mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) &&
            (mp.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))
            return i;
    }
    die("no HOST_VISIBLE|HOST_COHERENT memory type");
    return 0;
}

static void make_buffer(VkDeviceSize size, VkBufferUsageFlags usage,
                        VkBuffer *b, VkDeviceMemory *m, void **mapped) {
    VkBufferCreateInfo bi;
    memset(&bi, 0, sizeof bi);
    bi.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    bi.size = size;
    bi.usage = usage;
    bi.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    vkchk(vkCreateBuffer(device, &bi, NULL, b), "vkCreateBuffer");
    VkMemoryRequirements req;
    vkGetBufferMemoryRequirements(device, *b, &req);
    VkMemoryAllocateInfo ai;
    memset(&ai, 0, sizeof ai);
    ai.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    ai.allocationSize = req.size;
    ai.memoryTypeIndex = find_memory(req.memoryTypeBits);
    vkchk(vkAllocateMemory(device, &ai, NULL, m), "vkAllocateMemory");
    vkchk(vkBindBufferMemory(device, *b, *m, 0), "vkBindBufferMemory");
    if (mapped) vkchk(vkMapMemory(device, *m, 0, VK_WHOLE_SIZE, 0, mapped), "vkMapMemory");
}

static VkPipeline make_pipeline(VkShaderModule mod, uint32_t wg, int forced,
                                VkPipelineLayout layout) {
    VkPipelineShaderStageCreateInfo si;
    memset(&si, 0, sizeof si);
    si.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    si.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    si.module = mod;
    si.pName = "main";
    VkPipelineShaderStageRequiredSubgroupSizeCreateInfo ssi;
    memset(&ssi, 0, sizeof ssi);
    ssi.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_REQUIRED_SUBGROUP_SIZE_CREATE_INFO;
    ssi.requiredSubgroupSize = (uint32_t)forced;
    if (forced > 0) si.pNext = &ssi;
    VkComputePipelineCreateInfo ci;
    memset(&ci, 0, sizeof ci);
    ci.sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;
    ci.stage = si;
    ci.layout = layout;
    VkPipeline p;
    VkResult r = vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &ci, NULL, &p);
    if (r != VK_SUCCESS) return VK_NULL_HANDLE;
    return p;
}

static void submit_one(VkPipeline p, VkPipelineLayout layout, VkDescriptorSet set,
                       uint32_t groups, VkCommandBuffer *out_cmd) {
    VkCommandBufferAllocateInfo ai;
    memset(&ai, 0, sizeof ai);
    ai.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    ai.commandPool = cmdpool;
    ai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    ai.commandBufferCount = 1;
    VkCommandBuffer cmd;
    vkchk(vkAllocateCommandBuffers(device, &ai, &cmd), "vkAllocateCommandBuffers");
    VkCommandBufferBeginInfo bi;
    memset(&bi, 0, sizeof bi);
    bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkchk(vkBeginCommandBuffer(cmd, &bi), "vkBeginCommandBuffer");
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, p);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 0, 1, &set, 0, NULL);
    vkCmdDispatch(cmd, groups, 1, 1);
    vkEndCommandBuffer(cmd);
    VkSubmitInfo si;
    memset(&si, 0, sizeof si);
    si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    si.commandBufferCount = 1;
    si.pCommandBuffers = &cmd;
    vkchk(vkQueueSubmit(queue, 1, &si, VK_NULL_HANDLE), "vkQueueSubmit");
    vkchk(vkQueueWaitIdle(queue), "vkQueueWaitIdle");
    if (out_cmd) *out_cmd = cmd; else vkFreeCommandBuffers(device, cmdpool, 1, &cmd);
}

static void submit_timed(VkPipeline p, VkPipelineLayout layout, VkDescriptorSet set,
                         uint32_t groups, uint64_t *gpu_ticks, uint64_t *host_ns) {
    VkCommandBufferAllocateInfo ai;
    memset(&ai, 0, sizeof ai);
    ai.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    ai.commandPool = cmdpool;
    ai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    ai.commandBufferCount = 1;
    VkCommandBuffer cmd;
    vkchk(vkAllocateCommandBuffers(device, &ai, &cmd), "vkAllocateCommandBuffers");
    VkCommandBufferBeginInfo bi;
    memset(&bi, 0, sizeof bi);
    bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkchk(vkBeginCommandBuffer(cmd, &bi), "vkBeginCommandBuffer");
    vkCmdResetQueryPool(cmd, querypool, 0, 2);
    vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, querypool, 0);
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, p);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 0, 1, &set, 0, NULL);
    /* ARM-K bracket, byte-preserved from the family base: BATCH consecutive
       dispatches inside one bracket (floor lifting), identical idempotent
       writes to parts[], no barriers between them at BARRIER_N=0 (the act's
       frozen set).  The BARRIER_N interleaving below is the reconstruction's
       reading of the committed (BATCH,BARRIER_N) pair design (s232: "2
       dispatches + 2 barriers"); at the act's BARRIER_N=0 it is inert. */
    for (int b = 0; b < BATCH; b++) {
        vkCmdDispatch(cmd, groups, 1, 1);
        if (b < BARRIER_N) {
            VkMemoryBarrier mb;
            memset(&mb, 0, sizeof mb);
            mb.sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER;
            vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                                 VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0,
                                 1, &mb, 0, NULL, 0, NULL);
        }
    }
    vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, querypool, 1);
    vkEndCommandBuffer(cmd);
    VkSubmitInfo si;
    memset(&si, 0, sizeof si);
    si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    si.commandBufferCount = 1;
    si.pCommandBuffers = &cmd;
    uint64_t t0 = now_ns();
    vkchk(vkQueueSubmit(queue, 1, &si, VK_NULL_HANDLE), "vkQueueSubmit");
    vkchk(vkQueueWaitIdle(queue), "vkQueueWaitIdle");
    *host_ns = now_ns() - t0;
    uint64_t ts[2] = {0, 0};
    VkResult r = vkGetQueryPoolResults(device, querypool, 0, 2, sizeof ts, ts,
                                       sizeof(uint64_t),
                                       VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT);
    if (r == VK_SUCCESS && ts[1] >= ts[0]) *gpu_ticks = ts[1] - ts[0];
    else *gpu_ticks = 0;
    vkFreeCommandBuffers(device, cmdpool, 1, &cmd);
}

/* ---- ACT ARM-Z1 + ARM-Z2 probe (protocol section 4) ----
 * ONE command buffer submitted at round start before any dispatch (the
 * frozen placement: Z1, Z2 at round start in that order):
 *   ARM-Z1 (zwts): two vkCmdWriteTimestamp calls back to back, same
 *     pipeline stage (TOP_OF_PIPE both), NO command between them.
 *   ARM-Z2 (zwbar): placed immediately after ARM-Z1 -- vkCmdWriteTimestamp
 *     (TOP_OF_PIPE), ONE vkCmdPipelineBarrier with no memory/execution
 *     dependencies beyond the barrier itself (zero access masks, zero
 *     buffer/image barriers; the stage pair is the barrier's own
 *     ordering), vkCmdWriteTimestamp (BOTTOM_OF_PIPE).
 * No kernel work of any kind is inside either probe bracket.  Recording
 * both pairs in one command buffer realizes "Z2 placed immediately after
 * Z1" in the GPU stream with no host-side gap. */
static void probe_zpair(uint64_t *zwts_ticks, uint64_t *zwbar_ticks) {
    VkCommandBufferAllocateInfo ai;
    memset(&ai, 0, sizeof ai);
    ai.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    ai.commandPool = cmdpool;
    ai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    ai.commandBufferCount = 1;
    VkCommandBuffer cmd;
    vkchk(vkAllocateCommandBuffers(device, &ai, &cmd), "vkAllocateCommandBuffers");
    VkCommandBufferBeginInfo bi;
    memset(&bi, 0, sizeof bi);
    bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkchk(vkBeginCommandBuffer(cmd, &bi), "vkBeginCommandBuffer");
    vkCmdResetQueryPool(cmd, querypool, 2, 4);
    /* ARM-Z1 pair (back to back, same stage, no command between them) */
    vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, querypool, 2);
    vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, querypool, 3);
    /* ARM-Z2 pair (immediately after ARM-Z1; empty barrier between) */
    vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, querypool, 4);
    VkMemoryBarrier mb;
    memset(&mb, 0, sizeof mb);
    mb.sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER;
    vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
                         VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 0,
                         0, &mb, 0, NULL, 0, NULL);
    vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, querypool, 5);
    vkEndCommandBuffer(cmd);
    VkSubmitInfo si;
    memset(&si, 0, sizeof si);
    si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    si.commandBufferCount = 1;
    si.pCommandBuffers = &cmd;
    vkchk(vkQueueSubmit(queue, 1, &si, VK_NULL_HANDLE), "vkQueueSubmit");
    vkchk(vkQueueWaitIdle(queue), "vkQueueWaitIdle");
    uint64_t ts[4] = {0, 0, 0, 0};
    VkResult r = vkGetQueryPoolResults(device, querypool, 2, 4, sizeof ts, ts,
                                       sizeof(uint64_t),
                                       VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT);
    if (r == VK_SUCCESS && ts[1] >= ts[0]) *zwts_ticks = ts[1] - ts[0];
    else *zwts_ticks = 0;
    if (r == VK_SUCCESS && ts[3] >= ts[2]) *zwbar_ticks = ts[3] - ts[2];
    else *zwbar_ticks = 0;
    vkFreeCommandBuffers(device, cmdpool, 1, &cmd);
}

/* ---- ACT ARM-H probe (protocol section 4) ----
 * One isolated single dispatch (batch=1) of the reading-cell kernel
 * (op=sum, W=128, forced=16 = the committed idx=1 cell), timed on the host
 * with CLOCK_MONOTONIC_RAW around submit->completion by busy polling a
 * fence to completion.  REPORT-ONLY channel (no branch authority). */
static void probe_isohost(VkPipeline p, uint32_t groups, uint64_t *raw_ns) {
    VkCommandBufferAllocateInfo ai;
    memset(&ai, 0, sizeof ai);
    ai.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    ai.commandPool = cmdpool;
    ai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    ai.commandBufferCount = 1;
    VkCommandBuffer cmd;
    vkchk(vkAllocateCommandBuffers(device, &ai, &cmd), "vkAllocateCommandBuffers");
    VkCommandBufferBeginInfo bi;
    memset(&bi, 0, sizeof bi);
    bi.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkchk(vkBeginCommandBuffer(cmd, &bi), "vkBeginCommandBuffer");
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, p);
    vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, playout, 0, 1, &dset, 0, NULL);
    vkCmdDispatch(cmd, groups, 1, 1);  /* exactly one dispatch (batch=1) */
    vkEndCommandBuffer(cmd);
    VkSubmitInfo si;
    memset(&si, 0, sizeof si);
    si.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    si.commandBufferCount = 1;
    si.pCommandBuffers = &cmd;
    uint64_t t0 = now_raw_ns();
    vkchk(vkQueueSubmit(queue, 1, &si, isohost_fence), "vkQueueSubmit");
    while (vkGetFenceStatus(device, isohost_fence) != VK_SUCCESS) {
        /* busy poll to completion (the frozen protocol's host bracket) */
    }
    uint64_t t1 = now_raw_ns();
    *raw_ns = t1 - t0;
    vkchk(vkResetFences(device, 1, &isohost_fence), "vkResetFences");
    vkFreeCommandBuffers(device, cmdpool, 1, &cmd);
}

int main(int argc, char **argv) {
    if (argc != 2) die("usage: anv-causeprobe <manifest>");
    FILE *mf = fopen(argv[1], "r");
    if (!mf) die("cannot open manifest");
    static Cell cells[MAX_CELLS];
    int ncells = 0;
    char line[1200];
    while (fgets(line, sizeof line, mf)) {
        if (line[0] == '#' || line[0] == '\n') continue;
        Cell *c = &cells[ncells];
        char sbuf[32];
        if (sscanf(line, "%511s %u %31s %15s %511s", c->spv, &c->wg, sbuf, c->op,
                   c->probe_spv) != 5)
            die("bad manifest line");
        if (strcmp(sbuf, "default") == 0) c->forced = -1;
        else c->forced = atoi(sbuf);
        ncells++;
        if (ncells >= MAX_CELLS) die("too many cells");
    }
    fclose(mf);

    /* the committed knob formula (bound by impl-verify-s243.py against
       every committed knob-bearing run-log header):
       n = floor(N_ELEMENTS * work_mul / ndiv); at the act's frozen set
       work_mul=1 ndiv=1 this is exactly N_ELEMENTS. */
    uint32_t n_elems = (uint32_t)(((uint64_t)N_ELEMENTS * (uint64_t)WORK_MUL) / (uint64_t)NDIV);
    for (int i = 0; i < ncells; i++)
        cells[i].groups = (n_elems + cells[i].wg - 1) / cells[i].wg;

    /* ---- instance ---- */
    VkApplicationInfo app;
    memset(&app, 0, sizeof app);
    app.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName = "anv-subgroupsize";
    app.apiVersion = VK_API_VERSION_1_2;
    VkInstanceCreateInfo ici;
    memset(&ici, 0, sizeof ici);
    ici.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    ici.pApplicationInfo = &app;
    vkchk(vkCreateInstance(&ici, NULL, &instance), "vkCreateInstance");

    uint32_t ndev = 0;
    vkEnumeratePhysicalDevices(instance, &ndev, NULL);
    VkPhysicalDevice *devs = (VkPhysicalDevice *)malloc(ndev * sizeof(VkPhysicalDevice));
    vkEnumeratePhysicalDevices(instance, &ndev, devs);
    int picked = -1;
    for (uint32_t i = 0; i < ndev; i++) {
        VkPhysicalDeviceProperties p;
        vkGetPhysicalDeviceProperties(devs[i], &p);
        if (p.vendorID == 0x8086) { picked = (int)i; break; }
    }
    if (picked < 0) die("no Intel (vendorID 0x8086) Vulkan device");
    phys = devs[picked];
    free(devs);

    VkPhysicalDeviceProperties props;
    vkGetPhysicalDeviceProperties(phys, &props);
    snprintf(gpu_devname, sizeof gpu_devname, "%s", props.deviceName);
    dev_vendor = props.vendorID;
    dev_device = props.deviceID;
    dev_api = props.apiVersion;
    timestamp_period = props.limits.timestampPeriod;
    timestamp_compute_graphics = props.limits.timestampComputeAndGraphics ? 1 : 0;

    /* subgroup + subgroup-size-control facts */
    VkPhysicalDeviceSubgroupSizeControlProperties sscp;
    memset(&sscp, 0, sizeof sscp);
    sscp.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SUBGROUP_SIZE_CONTROL_PROPERTIES;
    VkPhysicalDeviceSubgroupProperties sgp;
    memset(&sgp, 0, sizeof sgp);
    sgp.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SUBGROUP_PROPERTIES;
    sgp.pNext = &sscp;
    VkPhysicalDeviceProperties2 p2;
    memset(&p2, 0, sizeof p2);
    p2.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2;
    p2.pNext = &sgp;
    vkGetPhysicalDeviceProperties2(phys, &p2);
    subgroup_size_reported = sgp.subgroupSize;
    min_sub = sscp.minSubgroupSize;
    max_sub = sscp.maxSubgroupSize;
    required_stages = sscp.requiredSubgroupSizeStages;

    VkPhysicalDeviceSubgroupSizeControlFeatures sscf;
    memset(&sscf, 0, sizeof sscf);
    sscf.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_SUBGROUP_SIZE_CONTROL_FEATURES;
    VkPhysicalDeviceFeatures2 f2;
    memset(&f2, 0, sizeof f2);
    f2.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2;
    f2.pNext = &sscf;
    vkGetPhysicalDeviceFeatures2(phys, &f2);
    size_control_feature = sscf.subgroupSizeControl ? 1 : 0;
    size_control_full = sscf.computeFullSubgroups ? 1 : 0;

    /* ---- device ---- */
    float prio = 1.0f;
    VkDeviceQueueCreateInfo qci;
    memset(&qci, 0, sizeof qci);
    qci.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    qci.queueFamilyIndex = qfamily = 0;
    qci.queueCount = 1;
    qci.pQueuePriorities = &prio;
    VkDeviceCreateInfo dci;
    memset(&dci, 0, sizeof dci);
    dci.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    dci.queueCreateInfoCount = 1;
    dci.pQueueCreateInfos = &qci;
    dci.pNext = &sscf;
    vkchk(vkCreateDevice(phys, &dci, NULL, &device), "vkCreateDevice");
    vkGetDeviceQueue(device, qfamily, 0, &queue);

    VkCommandPoolCreateInfo cpci;
    memset(&cpci, 0, sizeof cpci);
    cpci.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    cpci.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    cpci.queueFamilyIndex = qfamily;
    vkchk(vkCreateCommandPool(device, &cpci, NULL, &cmdpool), "vkCreateCommandPool");

    VkQueryPoolCreateInfo qpci;
    memset(&qpci, 0, sizeof qpci);
    qpci.sType = VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO;
    qpci.queryType = VK_QUERY_TYPE_TIMESTAMP;
    qpci.queryCount = 6;
    vkchk(vkCreateQueryPool(device, &qpci, NULL, &querypool), "vkCreateQueryPool");

    VkFenceCreateInfo fci;
    memset(&fci, 0, sizeof fci);
    fci.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    vkchk(vkCreateFence(device, &fci, NULL, &isohost_fence), "vkCreateFence");

    /* ---- buffers ---- */
    nparts = PARTS_CAP;
    void *map;
    make_buffer((VkDeviceSize)N_ELEMENTS * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, &xbuf, &xm, &map);
    xhost = (float *)map;
    make_buffer((VkDeviceSize)nparts * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, &partsbuf, &pm, &map);
    phost = (float *)map;
    make_buffer(4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, &nbuf, &nm, &map);
    *(uint32_t *)map = n_elems;
    make_buffer((VkDeviceSize)nparts * 4, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, &obuf, &om, &map);
    ohost = (uint32_t *)map;
    memset(map, 0, nparts * 4);

    lcg_state = SEED;
    for (uint32_t i = 0; i < N_ELEMENTS; i++) xhost[i] = (float)(lcg_next() % 1024u);

    /* ---- descriptors ---- */
    VkDescriptorSetLayoutBinding b3[3];
    memset(b3, 0, sizeof b3);
    for (int i = 0; i < 3; i++) {
        b3[i].binding = (uint32_t)i;
        b3[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        b3[i].descriptorCount = 1;
        b3[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }
    VkDescriptorSetLayoutCreateInfo dlci;
    memset(&dlci, 0, sizeof dlci);
    dlci.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    dlci.bindingCount = 3;
    dlci.pBindings = b3;
    vkchk(vkCreateDescriptorSetLayout(device, &dlci, NULL, &dsl), "dsl");
    VkDescriptorSetLayoutBinding b1 = b3[0];
    dlci.bindingCount = 1;
    dlci.pBindings = &b1;
    vkchk(vkCreateDescriptorSetLayout(device, &dlci, NULL, &probe_dsl), "probe dsl");

    VkDescriptorPoolSize ps[1];
    ps[0].type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    ps[0].descriptorCount = 8;
    VkDescriptorPoolCreateInfo dpci;
    memset(&dpci, 0, sizeof dpci);
    dpci.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
    dpci.maxSets = 4;
    dpci.poolSizeCount = 1;
    dpci.pPoolSizes = ps;
    vkchk(vkCreateDescriptorPool(device, &dpci, NULL, &dpool), "pool");
    VkDescriptorSetAllocateInfo dsai;
    memset(&dsai, 0, sizeof dsai);
    dsai.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    dsai.descriptorPool = dpool;
    dsai.descriptorSetCount = 1;
    dsai.pSetLayouts = &dsl;
    vkchk(vkAllocateDescriptorSets(device, &dsai, &dset), "dset");
    dsai.pSetLayouts = &probe_dsl;
    vkchk(vkAllocateDescriptorSets(device, &dsai, &probe_dset), "probe dset");

    VkDescriptorBufferInfo bi0 = {xbuf, 0, VK_WHOLE_SIZE};
    VkDescriptorBufferInfo bi1 = {partsbuf, 0, VK_WHOLE_SIZE};
    VkDescriptorBufferInfo bi2 = {nbuf, 0, VK_WHOLE_SIZE};
    VkWriteDescriptorSet w3[3];
    memset(w3, 0, sizeof w3);
    for (int i = 0; i < 3; i++) {
        w3[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
        w3[i].dstSet = dset;
        w3[i].dstBinding = (uint32_t)i;
        w3[i].descriptorCount = 1;
        w3[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    }
    w3[0].pBufferInfo = &bi0;
    w3[1].pBufferInfo = &bi1;
    w3[2].pBufferInfo = &bi2;
    vkUpdateDescriptorSets(device, 3, w3, 0, NULL);
    VkDescriptorBufferInfo bo = {obuf, 0, VK_WHOLE_SIZE};
    VkWriteDescriptorSet w1;
    memset(&w1, 0, sizeof w1);
    w1.sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;
    w1.dstSet = probe_dset;
    w1.dstBinding = 0;
    w1.descriptorCount = 1;
    w1.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
    w1.pBufferInfo = &bo;
    vkUpdateDescriptorSets(device, 1, &w1, 0, NULL);

    VkPushConstantRange pcr; /* none */
    memset(&pcr, 0, sizeof pcr);
    VkPipelineLayoutCreateInfo plci;
    memset(&plci, 0, sizeof plci);
    plci.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    plci.setLayoutCount = 1;
    plci.pSetLayouts = &dsl;
    vkchk(vkCreatePipelineLayout(device, &plci, NULL, &playout), "playout");
    plci.pSetLayouts = &probe_dsl;
    vkchk(vkCreatePipelineLayout(device, &plci, NULL, &probe_playout), "probe_playout");

    /* ---- header (byte-identical to the committed c2 run-log header;
       protocol section 1c requires the act's ARM-K to reproduce this
       metadata exactly) ---- */
    printf("# instrument=anv-subgroupsize-batch v2-batch64 (JUN-59 subgroup 16-vs-32 floor-lifting rerun, 2026-10-27)\n");
    printf("# device_name=%s vendor=%04x device=%04x api=%u.%u.%u\n", gpu_devname,
           dev_vendor, dev_device, VK_API_VERSION_MAJOR(dev_api),
           VK_API_VERSION_MINOR(dev_api), VK_API_VERSION_PATCH(dev_api));
    printf("# maxComputeWorkGroupSize=%u,%u,%u\n", props.limits.maxComputeWorkGroupSize[0],
           props.limits.maxComputeWorkGroupSize[1], props.limits.maxComputeWorkGroupSize[2]);
    printf("# subgroupSize=%u subgroupStages=%08x subgroupOps=%08x\n",
           sgp.subgroupSize, sgp.supportedStages, sgp.supportedOperations);
    printf("# subgroupSizeControl: feature=%d computeFullSubgroups=%d min=%u max=%u requiredStages=%08x\n",
           size_control_feature, size_control_full, min_sub, max_sub, required_stages);
    printf("# timestampPeriod=%.3f timestampComputeAndGraphics=%d\n", timestamp_period,
           timestamp_compute_graphics);
    printf("# n=%u rounds=%d warmup=%d batch=%d barrier_n=%d work_mul=%d ndiv=%d seed=%u metric=gpu_ns (vkCmdWriteTimestamp BATCH-dispatch bracket; per_dispatch_ns=gpu_ns/batch) +host_ns (CLOCK_MONOTONIC submit->completion)\n",
           n_elems, ROUNDS, WARMUP, BATCH, BARRIER_N, WORK_MUL, NDIV, SEED);

    /* ---- pipelines + probe verification ---- */
    for (int i = 0; i < ncells; i++) {
        Cell *c = &cells[i];
        c->module = load_module(c->spv);
        c->probe_module = load_module(c->probe_spv);
        int forced_ok = (c->forced < 0) || (size_control_feature &&
                        (required_stages & VK_SHADER_STAGE_COMPUTE_BIT) &&
                        c->forced >= (int)min_sub && c->forced <= (int)max_sub);
        c->pipeline = forced_ok ? make_pipeline(c->module, c->wg, c->forced > 0 ? c->forced : 0, playout)
                                : VK_NULL_HANDLE;
        c->pipeline_ok = (c->pipeline != VK_NULL_HANDLE);
        /* probe: one workgroup at this wg width, same forcing */
        VkPipeline pp = forced_ok ? make_pipeline(c->probe_module, c->wg, c->forced > 0 ? c->forced : 0, probe_playout)
                                  : VK_NULL_HANDLE;
        if (pp) {
            /* om is ALREADY persistently mapped by make_buffer at startup --
               never vkMapMemory it again (the family's defect-(c) fix). */
            ohost[0] = ohost[1] = ohost[2] = 0;
            submit_one(pp, probe_playout, probe_dset, 1, NULL);
            c->probe_size = (int)ohost[0];
            c->probe_nsub = (int)ohost[1];
            c->probe_wg = (int)ohost[2];
            vkDestroyPipeline(device, pp, NULL);
        } else {
            c->probe_size = c->probe_nsub = c->probe_wg = -1;
        }
        c->void_cell = 0;
        c->void_reason[0] = 0;
        if (!c->pipeline_ok) {
            c->void_cell = 1;
            snprintf(c->void_reason, sizeof c->void_reason, "pipeline-create-failed");
        } else if (c->forced > 0 && c->probe_size != c->forced) {
            c->void_cell = 1;
            snprintf(c->void_reason, sizeof c->void_reason, "probe-size-mismatch");
        } else if (c->forced < 0 && c->probe_size != (int)subgroup_size_reported) {
            c->void_cell = 1;
            snprintf(c->void_reason, sizeof c->void_reason, "default-probe-mismatch");
        }
        printf("CELL idx=%d spv=%s op=%s wg=%u forced=%s probe_size=%d probe_nsub=%d probe_wg=%d pipeline=%s void=%d void_reason=%s\n",
               i, c->spv, c->op, c->wg, c->forced < 0 ? "default" : (c->forced == 8 ? "8" : c->forced == 16 ? "16" : "32"),
               c->probe_size, c->probe_nsub, c->probe_wg,
               c->pipeline_ok ? "ok" : "FAIL", c->void_cell, c->void_reason);
    }

    /* ARM-H reading-cell kernel: the committed idx=1 cell (op=sum, wg=128,
       forced=16) -- the act's reading cell (sum,128,S=16).  Fail closed if
       the map does not carry it. */
    Cell *reading = NULL;
    for (int i = 0; i < ncells; i++) {
        Cell *c = &cells[i];
        if (strcmp(c->op, "sum") == 0 && c->wg == 128 && c->forced == 16 && c->pipeline_ok) {
            reading = c;
            break;
        }
    }
    if (!reading) die("reading cell (op=sum wg=128 forced=16) missing or failed");

    /* ---- warmup ---- */
    for (int i = 0; i < ncells; i++) {
        Cell *c = &cells[i];
        if (!c->pipeline_ok) continue;
        for (int w = 0; w < WARMUP; w++)
            submit_one(c->pipeline, playout, dset, c->groups, NULL);
    }

    /* ---- interleaved timed rounds with the act's probe rows ---- */
    int order[MAX_CELLS];
    for (int i = 0; i < ncells; i++) order[i] = i;
    for (int r = 0; r < ROUNDS; r++) {
        /* ARM-Z1 + ARM-Z2 at round start, in that order (before any
           dispatch of the round) */
        uint64_t d1 = 0, d2 = 0;
        probe_zpair(&d1, &d2);
        printf("PROBE round=%d channel=zwts ticks=%llu\n", r, (unsigned long long)d1);
        printf("PROBE round=%d channel=zwbar ticks=%llu\n", r, (unsigned long long)d2);
        /* seeded Fisher-Yates, byte-preserved from the family base:
           identical order in every process (run unit varies only in
           process state, never in visit order) */
        lcg_state = SEED + (uint32_t)r;
        for (int i = ncells - 1; i > 0; i--) {
            int j = (int)(lcg_next() % (uint32_t)(i + 1));
            int t = order[i]; order[i] = order[j]; order[j] = t;
        }
        /* ARM-K: the committed c2 control stream in the middle of the
           round, committed per-round order, byte-preserved rows */
        for (int k = 0; k < ncells; k++) {
            Cell *c = &cells[order[k]];
            if (!c->pipeline_ok) continue;
            uint64_t ticks = 0, host = 0;
            submit_timed(c->pipeline, playout, dset, c->groups, &ticks, &host);
            printf("SAMPLE round=%d idx=%d batch=%d work_mul=%d ndiv=%d gpu_ticks=%llu gpu_ns=%.1f per_dispatch_ns=%.2f host_ns=%llu\n",
                   r, order[k], BATCH, WORK_MUL, NDIV, (unsigned long long)ticks,
                   (double)ticks * (double)timestamp_period,
                   (double)ticks * (double)timestamp_period / (double)BATCH,
                   (unsigned long long)host);
        }
        /* ARM-H at round end: isolated single dispatch of the reading-cell
           kernel, host-timed CLOCK_MONOTONIC_RAW by busy polling */
        uint64_t h = 0;
        probe_isohost(reading->pipeline, reading->groups, &h);
        printf("PROBE round=%d channel=isohost raw_ns=%llu\n", r, (unsigned long long)h);
    }

    /* ---- correctness, inside the run ---- */
    for (int i = 0; i < ncells; i++) {
        Cell *c = &cells[i];
        if (!c->pipeline_ok) {
            printf("VERIFY idx=%d checked=0 mismatch=0 ok=0 note=pipeline-failed\n", i);
            continue;
        }
        submit_one(c->pipeline, playout, dset, c->groups, NULL);
        /* pm is persistently mapped at startup (phost); never remap. */
        float *parts = phost;
        int mismatch = 0;
        for (uint32_t g = 0; g < c->groups; g++) {
            uint32_t lo = g * c->wg;
            uint32_t hi = lo + c->wg; if (hi > n_elems) hi = n_elems;
            double ref;
            if (strcmp(c->op, "sum") == 0) {
                ref = 0.0;
                for (uint32_t e = lo; e < hi; e++) ref += (double)xhost[e];
            } else if (strcmp(c->op, "max") == 0) {
                ref = -1e30;
                for (uint32_t e = lo; e < hi; e++) if ((double)xhost[e] > ref) ref = (double)xhost[e];
            } else {
                ref = 1e30;
                for (uint32_t e = lo; e < hi; e++) if ((double)xhost[e] < ref) ref = (double)xhost[e];
            }
            if ((double)parts[g] != ref) mismatch++;
        }
        printf("VERIFY idx=%d checked=%u mismatch=%d ok=%d\n", i, c->groups, mismatch,
               mismatch == 0 ? 1 : 0);
    }
    printf("# done cells=%d\n", ncells);
    return 0;
}
