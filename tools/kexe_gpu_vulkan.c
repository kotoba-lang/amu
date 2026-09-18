/* kexe_gpu_vulkan.c -- the MECHANISM half of capability :gpu/compute
 * (compiler wire id 42; root ADR-2609182400 C, kotoba-lang capability-catalog).
 *
 * This file is #included by kexe_loader.c when it is built with
 * -DKEXE_GPU_VULKAN (and linked with -lvulkan). It runs in the SUPERVISOR
 * process, never in the sandboxed guest: the guest's provider (wire 42) writes
 * the request bytes to a pipe and blocks on the answer, and the supervisor --
 * which the seccomp filter does not cover -- performs the Vulkan work here.
 * That keeps the filter as tight as it was: a Mesa/NVIDIA driver needs ioctl,
 * mmap, futex, threads and a dozen more syscalls the guest is not admitted,
 * and it must not be.
 *
 * It decides nothing. Every request names handles the guest already holds
 * and a workgroup count; which kernel, which layer, which token, what to
 * sample -- all of that is the `.kotoba` program's. The request grammar is
 * one ASCII line, space separated, and the answer is decimal or hex text
 * (`:string -> :string`, the shape every wire here has):
 *
 *   INFO                                   -> "<device>|<api>|<maxWgX>|<unified>"
 *   ALLOC <bytes>                          -> handle            (device-local storage buffer)
 *   MAP <path> <offset> <length>           -> handle            (file bytes uploaded through staging)
 *   WRITE <handle> <offset> <hex>          -> "1"
 *   READ <handle> <offset> <length>        -> hex
 *   PIPELINE <spv-path> <bindings>         -> handle            (entry "main", <bindings> storage buffers 0..n-1)
 *   BEGIN                                  -> "1"               (start recording one command buffer)
 *   DISPATCH <pipe> <x> <y> <z> <h>...     -> "1"               (recorded when BEGIN is open, else submitted alone)
 *   SUBMIT                                 -> nanoseconds       (submit -> fence, host clock)
 *   FREE <handle>                          -> "1"
 *   ZERO <handle>                          -> "1"               (fill the buffer with zeros: fresh state / ring)
 *
 * A malformed request or a Vulkan error answers the single byte "!" followed
 * by the reason; the guest-side provider turns that into SIGILL (fail closed),
 * and the reason is printed on the supervisor's stderr so the run says WHY.
 *
 * Bounds: 256 buffers, 64 pipelines, 64 dispatches per command buffer, 8
 * bindings per pipeline. A request above them is refused by name. */

#include <vulkan/vulkan.h>

#define KGPU_MAX_BUFFERS 256
#define KGPU_MAX_PIPELINES 64
#define KGPU_MAX_BINDINGS 8
#define KGPU_MAX_DISPATCHES 64
#define KGPU_STAGING_BYTES (64u * 1024u * 1024u)

struct kgpu_buffer {
  VkBuffer buffer;
  VkDeviceMemory memory;
  VkDeviceSize size;
  int live;
};

struct kgpu_pipeline {
  VkShaderModule module;
  VkDescriptorSetLayout set_layout;
  VkPipelineLayout layout;
  VkPipeline pipeline;
  uint32_t bindings;
  int live;
};

static struct {
  int ready;
  VkInstance instance;
  VkPhysicalDevice physical;
  VkDevice device;
  VkQueue queue;
  uint32_t queue_family;
  VkCommandPool pool;
  VkCommandBuffer cmd;
  VkFence fence;
  VkDescriptorPool descriptors;
  VkBuffer staging;
  VkDeviceMemory staging_memory;
  void *staging_map;
  int recording;
  uint32_t recorded;
  VkDescriptorSet sets_in_flight[KGPU_MAX_DISPATCHES];
  uint32_t sets_in_flight_count;
  struct kgpu_buffer buffers[KGPU_MAX_BUFFERS];
  struct kgpu_pipeline pipelines[KGPU_MAX_PIPELINES];
  char device_name[256];
  uint32_t api_version;
  uint32_t max_wg_x;
  int unified_memory;
} kgpu;

/* ---- answer helpers ------------------------------------------------------ */

static size_t kgpu_fail(uint8_t *out, size_t cap, const char *reason) {
  size_t n = strlen(reason);
  if (n + 1 > cap) n = cap - 1;
  out[0] = '!';
  memcpy(out + 1, reason, n);
  fprintf(stderr, "kexe-loader gpu: %s\n", reason);
  return n + 1;
}

static size_t kgpu_decimal(uint8_t *out, uint64_t value) {
  char tmp[24];
  size_t n = 0;
  do { tmp[n++] = (char)('0' + (value % 10u)); value /= 10u; } while (value != 0);
  for (size_t k = 0; k < n; k++) out[k] = (uint8_t)tmp[n - 1 - k];
  return n;
}

static const char *kgpu_vk_name(VkResult r) {
  switch (r) {
    case VK_SUCCESS: return "VK_SUCCESS";
    case VK_ERROR_OUT_OF_HOST_MEMORY: return "VK_ERROR_OUT_OF_HOST_MEMORY";
    case VK_ERROR_OUT_OF_DEVICE_MEMORY: return "VK_ERROR_OUT_OF_DEVICE_MEMORY";
    case VK_ERROR_INITIALIZATION_FAILED: return "VK_ERROR_INITIALIZATION_FAILED";
    case VK_ERROR_DEVICE_LOST: return "VK_ERROR_DEVICE_LOST";
    case VK_ERROR_INVALID_SHADER_NV: return "VK_ERROR_INVALID_SHADER";
    case VK_TIMEOUT: return "VK_TIMEOUT";
    default: return "VK_ERROR (other)";
  }
}

static char kgpu_reason[512];
#define KGPU_VK(call) do { VkResult kgpu_r_ = (call); if (kgpu_r_ != VK_SUCCESS) { \
  snprintf(kgpu_reason, sizeof kgpu_reason, "%s: %s", #call, kgpu_vk_name(kgpu_r_)); return -1; } } while (0)

/* ---- device -------------------------------------------------------------- */

static int kgpu_find_memory(uint32_t type_bits, VkMemoryPropertyFlags want, uint32_t *index) {
  VkPhysicalDeviceMemoryProperties props;
  vkGetPhysicalDeviceMemoryProperties(kgpu.physical, &props);
  for (uint32_t i = 0; i < props.memoryTypeCount; i++) {
    if ((type_bits & (1u << i)) && (props.memoryTypes[i].propertyFlags & want) == want) {
      *index = i;
      return 0;
    }
  }
  return -1;
}

static int kgpu_make_buffer(VkDeviceSize size, VkBufferUsageFlags usage, VkMemoryPropertyFlags want,
                            VkBuffer *buffer, VkDeviceMemory *memory) {
  VkBufferCreateInfo bi = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = size,
                            .usage = usage, .sharingMode = VK_SHARING_MODE_EXCLUSIVE };
  KGPU_VK(vkCreateBuffer(kgpu.device, &bi, NULL, buffer));
  VkMemoryRequirements req;
  vkGetBufferMemoryRequirements(kgpu.device, *buffer, &req);
  uint32_t type;
  if (kgpu_find_memory(req.memoryTypeBits, want, &type) != 0) {
    /* device-local asked for but not available in that form: fall back to any */
    if (kgpu_find_memory(req.memoryTypeBits, 0, &type) != 0) {
      snprintf(kgpu_reason, sizeof kgpu_reason, "no memory type for buffer");
      return -1;
    }
  }
  VkMemoryAllocateInfo ai = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
                              .allocationSize = req.size, .memoryTypeIndex = type };
  KGPU_VK(vkAllocateMemory(kgpu.device, &ai, NULL, memory));
  KGPU_VK(vkBindBufferMemory(kgpu.device, *buffer, *memory, 0));
  return 0;
}

static int kgpu_init(void) {
  if (kgpu.ready) return 0;
  VkApplicationInfo app = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
                            .pApplicationName = "kexe-loader :gpu/compute",
                            .apiVersion = VK_API_VERSION_1_1 };
  VkInstanceCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &app };
  KGPU_VK(vkCreateInstance(&ici, NULL, &kgpu.instance));
  uint32_t count = 0;
  KGPU_VK(vkEnumeratePhysicalDevices(kgpu.instance, &count, NULL));
  if (count == 0) { snprintf(kgpu_reason, sizeof kgpu_reason, "no Vulkan physical device"); return -1; }
  VkPhysicalDevice devices[8];
  if (count > 8) count = 8;
  KGPU_VK(vkEnumeratePhysicalDevices(kgpu.instance, &count, devices));
  /* KEXE_GPU_DEVICE=<index> picks; otherwise the first with a compute queue,
   * preferring a discrete GPU over an integrated one. */
  const char *pick = getenv("KEXE_GPU_DEVICE");
  int chosen = -1;
  int best_score = -1;
  for (uint32_t d = 0; d < count; d++) {
    uint32_t qcount = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(devices[d], &qcount, NULL);
    VkQueueFamilyProperties families[16];
    if (qcount > 16) qcount = 16;
    vkGetPhysicalDeviceQueueFamilyProperties(devices[d], &qcount, families);
    int compute = -1;
    for (uint32_t q = 0; q < qcount; q++)
      if (families[q].queueFlags & VK_QUEUE_COMPUTE_BIT) { compute = (int)q; break; }
    if (compute < 0) continue;
    VkPhysicalDeviceProperties p;
    vkGetPhysicalDeviceProperties(devices[d], &p);
    int score = p.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU ? 3
              : p.deviceType == VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU ? 2 : 1;
    if (pick != NULL) score = (uint32_t)atoi(pick) == d ? 10 : 0;
    if (score > best_score) { best_score = score; chosen = (int)d; kgpu.queue_family = (uint32_t)compute; }
  }
  if (chosen < 0) { snprintf(kgpu_reason, sizeof kgpu_reason, "no device with a compute queue"); return -1; }
  kgpu.physical = devices[chosen];
  VkPhysicalDeviceProperties props;
  vkGetPhysicalDeviceProperties(kgpu.physical, &props);
  snprintf(kgpu.device_name, sizeof kgpu.device_name, "%s", props.deviceName);
  kgpu.api_version = props.apiVersion;
  kgpu.max_wg_x = props.limits.maxComputeWorkGroupSize[0];
  kgpu.unified_memory = props.deviceType == VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU;

  float priority = 1.0f;
  VkDeviceQueueCreateInfo qi = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                                 .queueFamilyIndex = kgpu.queue_family, .queueCount = 1,
                                 .pQueuePriorities = &priority };
  VkDeviceCreateInfo di = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
                            .queueCreateInfoCount = 1, .pQueueCreateInfos = &qi };
  KGPU_VK(vkCreateDevice(kgpu.physical, &di, NULL, &kgpu.device));
  vkGetDeviceQueue(kgpu.device, kgpu.queue_family, 0, &kgpu.queue);
  VkCommandPoolCreateInfo pi = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
                                 .flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
                                 .queueFamilyIndex = kgpu.queue_family };
  KGPU_VK(vkCreateCommandPool(kgpu.device, &pi, NULL, &kgpu.pool));
  VkCommandBufferAllocateInfo cai = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
                                      .commandPool = kgpu.pool, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
                                      .commandBufferCount = 1 };
  KGPU_VK(vkAllocateCommandBuffers(kgpu.device, &cai, &kgpu.cmd));
  VkFenceCreateInfo fi = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
  KGPU_VK(vkCreateFence(kgpu.device, &fi, NULL, &kgpu.fence));
  VkDescriptorPoolSize psize = { .type = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                                 .descriptorCount = KGPU_MAX_DISPATCHES * KGPU_MAX_BINDINGS * 4 };
  VkDescriptorPoolCreateInfo dpi = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
                                     .maxSets = KGPU_MAX_DISPATCHES * 4, .poolSizeCount = 1, .pPoolSizes = &psize };
  KGPU_VK(vkCreateDescriptorPool(kgpu.device, &dpi, NULL, &kgpu.descriptors));
  if (kgpu_make_buffer(KGPU_STAGING_BYTES, VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                       VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                       &kgpu.staging, &kgpu.staging_memory) != 0) return -1;
  KGPU_VK(vkMapMemory(kgpu.device, kgpu.staging_memory, 0, KGPU_STAGING_BYTES, 0, &kgpu.staging_map));
  kgpu.ready = 1;
  return 0;
}

/* one-shot command: record with `record`, submit, wait. Returns ns. */
static int kgpu_submit_wait(uint64_t *nanoseconds) {
  KGPU_VK(vkEndCommandBuffer(kgpu.cmd));
  VkSubmitInfo si = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO, .commandBufferCount = 1, .pCommandBuffers = &kgpu.cmd };
  struct timespec t0, t1;
  clock_gettime(CLOCK_MONOTONIC, &t0);
  KGPU_VK(vkResetFences(kgpu.device, 1, &kgpu.fence));
  KGPU_VK(vkQueueSubmit(kgpu.queue, 1, &si, kgpu.fence));
  KGPU_VK(vkWaitForFences(kgpu.device, 1, &kgpu.fence, VK_TRUE, UINT64_C(60000000000)));
  clock_gettime(CLOCK_MONOTONIC, &t1);
  if (nanoseconds != NULL)
    *nanoseconds = (uint64_t)(t1.tv_sec - t0.tv_sec) * UINT64_C(1000000000) + (uint64_t)(t1.tv_nsec - t0.tv_nsec);
  if (kgpu.sets_in_flight_count > 0) {
    vkFreeDescriptorSets(kgpu.device, kgpu.descriptors, kgpu.sets_in_flight_count, kgpu.sets_in_flight);
    kgpu.sets_in_flight_count = 0;
  }
  return 0;
}

static int kgpu_begin_cmd(void) {
  KGPU_VK(vkResetCommandBuffer(kgpu.cmd, 0));
  VkCommandBufferBeginInfo bi = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO,
                                  .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT };
  KGPU_VK(vkBeginCommandBuffer(kgpu.cmd, &bi));
  return 0;
}

/* copy CHUNK bytes from the mapped staging buffer into BUFFER at OFFSET */
static int kgpu_upload_chunk(VkBuffer buffer, VkDeviceSize offset, VkDeviceSize chunk) {
  if (kgpu_begin_cmd() != 0) return -1;
  VkBufferCopy region = { .srcOffset = 0, .dstOffset = offset, .size = chunk };
  vkCmdCopyBuffer(kgpu.cmd, kgpu.staging, buffer, 1, &region);
  return kgpu_submit_wait(NULL);
}

static int kgpu_download_chunk(VkBuffer buffer, VkDeviceSize offset, VkDeviceSize chunk) {
  if (kgpu_begin_cmd() != 0) return -1;
  VkBufferCopy region = { .srcOffset = offset, .dstOffset = 0, .size = chunk };
  vkCmdCopyBuffer(kgpu.cmd, buffer, kgpu.staging, 1, &region);
  return kgpu_submit_wait(NULL);
}

/* ---- handles ------------------------------------------------------------- */

static int kgpu_new_buffer(VkDeviceSize size, int *handle) {
  for (int i = 1; i < KGPU_MAX_BUFFERS; i++) {
    if (kgpu.buffers[i].live) continue;
    if (kgpu_make_buffer(size, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT |
                         VK_BUFFER_USAGE_TRANSFER_DST_BIT, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
                         &kgpu.buffers[i].buffer, &kgpu.buffers[i].memory) != 0) return -1;
    kgpu.buffers[i].size = size;
    kgpu.buffers[i].live = 1;
    *handle = i;
    return 0;
  }
  snprintf(kgpu_reason, sizeof kgpu_reason, "buffer table full (%d)", KGPU_MAX_BUFFERS);
  return -1;
}

static struct kgpu_buffer *kgpu_buffer_at(long handle) {
  if (handle <= 0 || handle >= KGPU_MAX_BUFFERS || !kgpu.buffers[handle].live) return NULL;
  return &kgpu.buffers[handle];
}

static int kgpu_new_pipeline(const char *spv_path, uint32_t bindings, int *handle) {
  if (bindings == 0 || bindings > KGPU_MAX_BINDINGS) {
    snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE bindings must be 1..%d", KGPU_MAX_BINDINGS);
    return -1;
  }
  int slot = -1;
  for (int i = 1; i < KGPU_MAX_PIPELINES; i++) if (!kgpu.pipelines[i].live) { slot = i; break; }
  if (slot < 0) { snprintf(kgpu_reason, sizeof kgpu_reason, "pipeline table full"); return -1; }
  FILE *f = fopen(spv_path, "rb");
  if (f == NULL) { snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE cannot open %s", spv_path); return -1; }
  fseek(f, 0, SEEK_END);
  long n = ftell(f);
  fseek(f, 0, SEEK_SET);
  if (n <= 0 || (n % 4) != 0 || n > (16 << 20)) { fclose(f); snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE %s is not a SPIR-V blob", spv_path); return -1; }
  uint32_t *code = (uint32_t *)malloc((size_t)n);
  if (code == NULL || fread(code, 1, (size_t)n, f) != (size_t)n) { fclose(f); free(code); snprintf(kgpu_reason, sizeof kgpu_reason, "PIPELINE short read"); return -1; }
  fclose(f);
  struct kgpu_pipeline *p = &kgpu.pipelines[slot];
  VkShaderModuleCreateInfo smi = { .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO, .codeSize = (size_t)n, .pCode = code };
  VkResult r = vkCreateShaderModule(kgpu.device, &smi, NULL, &p->module);
  free(code);
  if (r != VK_SUCCESS) { snprintf(kgpu_reason, sizeof kgpu_reason, "vkCreateShaderModule: %s", kgpu_vk_name(r)); return -1; }
  VkDescriptorSetLayoutBinding lb[KGPU_MAX_BINDINGS];
  for (uint32_t b = 0; b < bindings; b++)
    lb[b] = (VkDescriptorSetLayoutBinding){ .binding = b, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                                            .descriptorCount = 1, .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT };
  VkDescriptorSetLayoutCreateInfo dli = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
                                          .bindingCount = bindings, .pBindings = lb };
  KGPU_VK(vkCreateDescriptorSetLayout(kgpu.device, &dli, NULL, &p->set_layout));
  VkPipelineLayoutCreateInfo pli = { .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
                                     .setLayoutCount = 1, .pSetLayouts = &p->set_layout };
  KGPU_VK(vkCreatePipelineLayout(kgpu.device, &pli, NULL, &p->layout));
  VkComputePipelineCreateInfo cpi = { .sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
                                      .stage = { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                                                 .stage = VK_SHADER_STAGE_COMPUTE_BIT, .module = p->module,
                                                 .pName = "main" },
                                      .layout = p->layout };
  KGPU_VK(vkCreateComputePipelines(kgpu.device, VK_NULL_HANDLE, 1, &cpi, NULL, &p->pipeline));
  p->bindings = bindings;
  p->live = 1;
  *handle = slot;
  return 0;
}

static int kgpu_record_dispatch(struct kgpu_pipeline *p, uint32_t x, uint32_t y, uint32_t z, long *handles) {
  if (kgpu.sets_in_flight_count >= KGPU_MAX_DISPATCHES) {
    snprintf(kgpu_reason, sizeof kgpu_reason, "more than %d dispatches in one command buffer", KGPU_MAX_DISPATCHES);
    return -1;
  }
  VkDescriptorSetAllocateInfo dai = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
                                      .descriptorPool = kgpu.descriptors, .descriptorSetCount = 1,
                                      .pSetLayouts = &p->set_layout };
  VkDescriptorSet set;
  KGPU_VK(vkAllocateDescriptorSets(kgpu.device, &dai, &set));
  kgpu.sets_in_flight[kgpu.sets_in_flight_count++] = set;
  VkDescriptorBufferInfo infos[KGPU_MAX_BINDINGS];
  VkWriteDescriptorSet writes[KGPU_MAX_BINDINGS];
  for (uint32_t b = 0; b < p->bindings; b++) {
    struct kgpu_buffer *buf = kgpu_buffer_at(handles[b]);
    if (buf == NULL) { snprintf(kgpu_reason, sizeof kgpu_reason, "DISPATCH binding %u: no such buffer %ld", b, handles[b]); return -1; }
    infos[b] = (VkDescriptorBufferInfo){ .buffer = buf->buffer, .offset = 0, .range = VK_WHOLE_SIZE };
    writes[b] = (VkWriteDescriptorSet){ .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = set,
                                        .dstBinding = b, .descriptorCount = 1,
                                        .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, .pBufferInfo = &infos[b] };
  }
  vkUpdateDescriptorSets(kgpu.device, p->bindings, writes, 0, NULL);
  if (kgpu.recorded > 0) {
    /* every dispatch after the first sees the previous one's writes */
    VkMemoryBarrier barrier = { .sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER,
                                .srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT,
                                .dstAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT };
    vkCmdPipelineBarrier(kgpu.cmd, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
                         0, 1, &barrier, 0, NULL, 0, NULL);
  }
  vkCmdBindPipeline(kgpu.cmd, VK_PIPELINE_BIND_POINT_COMPUTE, p->pipeline);
  vkCmdBindDescriptorSets(kgpu.cmd, VK_PIPELINE_BIND_POINT_COMPUTE, p->layout, 0, 1, &set, 0, NULL);
  vkCmdDispatch(kgpu.cmd, x, y, z);
  kgpu.recorded++;
  return 0;
}

/* ---- the request line ---------------------------------------------------- */

static int kgpu_hex_nibble(uint8_t c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

/* Split REQ into at most MAX tokens (NUL-terminated copies in BUF). */
static int kgpu_tokens(const uint8_t *req, size_t len, char *buf, size_t bufcap, char **tok, int max) {
  if (len + 1 > bufcap) return -1;
  memcpy(buf, req, len);
  buf[len] = 0;
  int n = 0;
  char *p = buf;
  while (*p != 0 && n < max) {
    while (*p == ' ') p++;
    if (*p == 0) break;
    tok[n++] = p;
    while (*p != 0 && *p != ' ') p++;
    if (*p == ' ') { *p = 0; p++; }
  }
  return n;
}

static int kgpu_parse_u64(const char *s, uint64_t *out) {
  if (s == NULL || *s == 0) return -1;
  errno = 0;
  char *end = NULL;
  unsigned long long v = strtoull(s, &end, 10);
  if (errno != 0 || end == s || *end != 0) return -1;
  *out = (uint64_t)v;
  return 0;
}

/* Handle one request; the answer is written to OUT (capacity CAP), its
 * length returned. Never longer than CAP. */
static size_t kgpu_handle(const uint8_t *req, size_t len, uint8_t *out, size_t cap) {
  static char buf[KGPU_STAGING_BYTES / 4 + 1024];  /* WRITE hex payload fits */
  char *tok[8 + KGPU_MAX_BINDINGS + 8];
  int n = kgpu_tokens(req, len, buf, sizeof buf, tok, (int)(sizeof tok / sizeof tok[0]));
  if (n <= 0) return kgpu_fail(out, cap, "empty request");
  if (kgpu_init() != 0) return kgpu_fail(out, cap, kgpu_reason);
  const char *op = tok[0];

  if (strcmp(op, "INFO") == 0) {
    int w = snprintf((char *)out, cap, "%s|%u.%u.%u|%u|%d", kgpu.device_name,
                     VK_VERSION_MAJOR(kgpu.api_version), VK_VERSION_MINOR(kgpu.api_version),
                     VK_VERSION_PATCH(kgpu.api_version), kgpu.max_wg_x, kgpu.unified_memory);
    return w < 0 ? kgpu_fail(out, cap, "INFO format") : (size_t)w;
  }
  if (strcmp(op, "ALLOC") == 0) {
    uint64_t bytes;
    if (n != 2 || kgpu_parse_u64(tok[1], &bytes) != 0 || bytes == 0) return kgpu_fail(out, cap, "ALLOC <bytes>");
    int h;
    if (kgpu_new_buffer((VkDeviceSize)bytes, &h) != 0) return kgpu_fail(out, cap, kgpu_reason);
    return kgpu_decimal(out, (uint64_t)h);
  }
  if (strcmp(op, "MAP") == 0) {
    /* a copy reuses the one command buffer; inside BEGIN..SUBMIT it would
     * RESET the batch and silently drop every dispatch recorded so far
     * (measured 2026-09-19: a WRITE after BEGIN left a 27-dispatch layer
     * step answering zeros). Refused by name instead. */
    if (kgpu.recording) return kgpu_fail(out, cap, "MAP while recording (BEGIN open): finish with SUBMIT first");
    uint64_t offset, length;
    if (n != 4 || kgpu_parse_u64(tok[2], &offset) != 0 || kgpu_parse_u64(tok[3], &length) != 0 || length == 0)
      return kgpu_fail(out, cap, "MAP <path> <offset> <length>");
    int fd = open(tok[1], O_RDONLY);
    if (fd < 0) return kgpu_fail(out, cap, "MAP cannot open the path");
    int h;
    if (kgpu_new_buffer((VkDeviceSize)length, &h) != 0) { close(fd); return kgpu_fail(out, cap, kgpu_reason); }
    uint64_t done = 0;
    while (done < length) {
      size_t chunk = (size_t)(length - done < KGPU_STAGING_BYTES ? length - done : KGPU_STAGING_BYTES);
      size_t got = 0;
      while (got < chunk) {
        ssize_t r = pread(fd, (uint8_t *)kgpu.staging_map + got, chunk - got, (off_t)(offset + done + got));
        if (r <= 0) { close(fd); return kgpu_fail(out, cap, "MAP short read"); }
        got += (size_t)r;
      }
      if (kgpu_upload_chunk(kgpu.buffers[h].buffer, (VkDeviceSize)done, (VkDeviceSize)chunk) != 0) { close(fd); return kgpu_fail(out, cap, kgpu_reason); }
      done += chunk;
    }
    close(fd);
    return kgpu_decimal(out, (uint64_t)h);
  }
  if (strcmp(op, "WRITE") == 0) {
    /* a copy reuses the one command buffer; inside BEGIN..SUBMIT it would
     * RESET the batch and silently drop every dispatch recorded so far
     * (measured 2026-09-19: a WRITE after BEGIN left a 27-dispatch layer
     * step answering zeros). Refused by name instead. */
    if (kgpu.recording) return kgpu_fail(out, cap, "WRITE while recording (BEGIN open): finish with SUBMIT first");
    uint64_t handle, offset;
    if (n != 4 || kgpu_parse_u64(tok[1], &handle) != 0 || kgpu_parse_u64(tok[2], &offset) != 0)
      return kgpu_fail(out, cap, "WRITE <handle> <offset> <hex>");
    struct kgpu_buffer *b = kgpu_buffer_at((long)handle);
    if (b == NULL) return kgpu_fail(out, cap, "WRITE: no such buffer");
    size_t digits = strlen(tok[3]);
    if ((digits & 1u) != 0 || digits / 2 > KGPU_STAGING_BYTES) return kgpu_fail(out, cap, "WRITE hex length");
    size_t bytes = digits / 2;
    if (offset + bytes > b->size) return kgpu_fail(out, cap, "WRITE past the buffer");
    uint8_t *dst = (uint8_t *)kgpu.staging_map;
    for (size_t i = 0; i < bytes; i++) {
      int hi = kgpu_hex_nibble((uint8_t)tok[3][2 * i]), lo = kgpu_hex_nibble((uint8_t)tok[3][2 * i + 1]);
      if (hi < 0 || lo < 0) return kgpu_fail(out, cap, "WRITE hex digit");
      dst[i] = (uint8_t)((hi << 4) | lo);
    }
    if (kgpu_upload_chunk(b->buffer, (VkDeviceSize)offset, (VkDeviceSize)bytes) != 0) return kgpu_fail(out, cap, kgpu_reason);
    out[0] = '1';
    return 1;
  }
  if (strcmp(op, "READ") == 0) {
    /* a copy reuses the one command buffer; inside BEGIN..SUBMIT it would
     * RESET the batch and silently drop every dispatch recorded so far
     * (measured 2026-09-19: a WRITE after BEGIN left a 27-dispatch layer
     * step answering zeros). Refused by name instead. */
    if (kgpu.recording) return kgpu_fail(out, cap, "READ while recording (BEGIN open): finish with SUBMIT first");
    uint64_t handle, offset, length;
    if (n != 4 || kgpu_parse_u64(tok[1], &handle) != 0 || kgpu_parse_u64(tok[2], &offset) != 0 ||
        kgpu_parse_u64(tok[3], &length) != 0) return kgpu_fail(out, cap, "READ <handle> <offset> <length>");
    struct kgpu_buffer *b = kgpu_buffer_at((long)handle);
    if (b == NULL) return kgpu_fail(out, cap, "READ: no such buffer");
    if (offset + length > b->size) return kgpu_fail(out, cap, "READ past the buffer");
    if (length * 2 > cap || length > KGPU_STAGING_BYTES) return kgpu_fail(out, cap, "READ longer than the answer can carry");
    if (kgpu_download_chunk(b->buffer, (VkDeviceSize)offset, (VkDeviceSize)length) != 0) return kgpu_fail(out, cap, kgpu_reason);
    static const char hex[] = "0123456789abcdef";
    const uint8_t *src = (const uint8_t *)kgpu.staging_map;
    for (uint64_t i = 0; i < length; i++) { out[2 * i] = (uint8_t)hex[src[i] >> 4]; out[2 * i + 1] = (uint8_t)hex[src[i] & 15]; }
    return (size_t)(length * 2);
  }
  if (strcmp(op, "PIPELINE") == 0) {
    uint64_t bindings;
    if (n != 3 || kgpu_parse_u64(tok[2], &bindings) != 0) return kgpu_fail(out, cap, "PIPELINE <spv-path> <bindings>");
    int h;
    if (kgpu_new_pipeline(tok[1], (uint32_t)bindings, &h) != 0) return kgpu_fail(out, cap, kgpu_reason);
    return kgpu_decimal(out, (uint64_t)h);
  }
  if (strcmp(op, "BEGIN") == 0) {
    if (kgpu.recording) return kgpu_fail(out, cap, "BEGIN while recording");
    if (kgpu_begin_cmd() != 0) return kgpu_fail(out, cap, kgpu_reason);
    kgpu.recording = 1;
    kgpu.recorded = 0;
    out[0] = '1';
    return 1;
  }
  if (strcmp(op, "DISPATCH") == 0) {
    uint64_t pipe, x, y, z;
    if (n < 5 || kgpu_parse_u64(tok[1], &pipe) != 0 || kgpu_parse_u64(tok[2], &x) != 0 ||
        kgpu_parse_u64(tok[3], &y) != 0 || kgpu_parse_u64(tok[4], &z) != 0)
      return kgpu_fail(out, cap, "DISPATCH <pipeline> <x> <y> <z> <handle>...");
    if (pipe == 0 || pipe >= KGPU_MAX_PIPELINES || !kgpu.pipelines[pipe].live) return kgpu_fail(out, cap, "DISPATCH: no such pipeline");
    struct kgpu_pipeline *p = &kgpu.pipelines[pipe];
    if ((uint32_t)(n - 5) != p->bindings) return kgpu_fail(out, cap, "DISPATCH: handle count != pipeline bindings");
    long handles[KGPU_MAX_BINDINGS];
    for (uint32_t b = 0; b < p->bindings; b++) {
      uint64_t h;
      if (kgpu_parse_u64(tok[5 + b], &h) != 0) return kgpu_fail(out, cap, "DISPATCH handle");
      handles[b] = (long)h;
    }
    int alone = !kgpu.recording;
    if (alone) { if (kgpu_begin_cmd() != 0) return kgpu_fail(out, cap, kgpu_reason); kgpu.recorded = 0; }
    if (kgpu_record_dispatch(p, (uint32_t)x, (uint32_t)y, (uint32_t)z, handles) != 0) return kgpu_fail(out, cap, kgpu_reason);
    if (alone) {
      uint64_t ns;
      if (kgpu_submit_wait(&ns) != 0) return kgpu_fail(out, cap, kgpu_reason);
      return kgpu_decimal(out, ns);
    }
    out[0] = '1';
    return 1;
  }
  if (strcmp(op, "SUBMIT") == 0) {
    if (!kgpu.recording) return kgpu_fail(out, cap, "SUBMIT without BEGIN");
    kgpu.recording = 0;
    uint64_t ns;
    if (kgpu_submit_wait(&ns) != 0) return kgpu_fail(out, cap, kgpu_reason);
    return kgpu_decimal(out, ns);
  }
  if (strcmp(op, "ZERO") == 0) {
    uint64_t handle;
    if (n != 2 || kgpu_parse_u64(tok[1], &handle) != 0) return kgpu_fail(out, cap, "ZERO <handle>");
    struct kgpu_buffer *b = kgpu_buffer_at((long)handle);
    if (b == NULL) return kgpu_fail(out, cap, "ZERO: no such buffer");
    if (kgpu.recording) return kgpu_fail(out, cap, "ZERO while recording");
    if (kgpu_begin_cmd() != 0) return kgpu_fail(out, cap, kgpu_reason);
    vkCmdFillBuffer(kgpu.cmd, b->buffer, 0, VK_WHOLE_SIZE, 0u);
    if (kgpu_submit_wait(NULL) != 0) return kgpu_fail(out, cap, kgpu_reason);
    out[0] = '1';
    return 1;
  }
  if (strcmp(op, "FREE") == 0) {
    uint64_t handle;
    if (n != 2 || kgpu_parse_u64(tok[1], &handle) != 0) return kgpu_fail(out, cap, "FREE <handle>");
    struct kgpu_buffer *b = kgpu_buffer_at((long)handle);
    if (b == NULL) return kgpu_fail(out, cap, "FREE: no such buffer");
    vkDestroyBuffer(kgpu.device, b->buffer, NULL);
    vkFreeMemory(kgpu.device, b->memory, NULL);
    b->live = 0;
    out[0] = '1';
    return 1;
  }
  return kgpu_fail(out, cap, "unknown :gpu/compute request");
}

/* Tear the device down in order once the guest is gone. Measured 2026-09-19
 * on the Jetson AGX Xavier (nvgpu 1.3.212): leaving a live VkDevice to the
 * process exit segfaulted in the driver's atexit path AFTER the report was
 * already written -- the run was right and the exit code said it was not.
 * Mesa (ANV, RADV) did not care; the order below is what every driver wants. */
static void kgpu_shutdown(void) {
  if (!kgpu.ready) return;
  (void)vkDeviceWaitIdle(kgpu.device);
  for (int i = 1; i < KGPU_MAX_PIPELINES; i++) {
    struct kgpu_pipeline *p = &kgpu.pipelines[i];
    if (!p->live) continue;
    vkDestroyPipeline(kgpu.device, p->pipeline, NULL);
    vkDestroyPipelineLayout(kgpu.device, p->layout, NULL);
    vkDestroyDescriptorSetLayout(kgpu.device, p->set_layout, NULL);
    vkDestroyShaderModule(kgpu.device, p->module, NULL);
    p->live = 0;
  }
  for (int i = 1; i < KGPU_MAX_BUFFERS; i++) {
    struct kgpu_buffer *b = &kgpu.buffers[i];
    if (!b->live) continue;
    vkDestroyBuffer(kgpu.device, b->buffer, NULL);
    vkFreeMemory(kgpu.device, b->memory, NULL);
    b->live = 0;
  }
  vkUnmapMemory(kgpu.device, kgpu.staging_memory);
  vkDestroyBuffer(kgpu.device, kgpu.staging, NULL);
  vkFreeMemory(kgpu.device, kgpu.staging_memory, NULL);
  vkDestroyDescriptorPool(kgpu.device, kgpu.descriptors, NULL);
  vkDestroyFence(kgpu.device, kgpu.fence, NULL);
  vkDestroyCommandPool(kgpu.device, kgpu.pool, NULL);
  vkDestroyDevice(kgpu.device, NULL);
  vkDestroyInstance(kgpu.instance, NULL);
  kgpu.ready = 0;
}

/* ---- the broker: supervisor side ----------------------------------------- */
/* Frame: u32 little-endian length, then the bytes; both directions. */

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

/* Serve one request from the guest on REQ_FD, answer on RESP_FD. 0 = served,
 * -1 = the guest closed its end (it exited). */
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
