/* JUN-714 measurement oracle only: a Vulkan empty compute dispatch on Xavier.
 * Compile on the measurement host with: cc -O2 this.c -lvulkan -o oracle
 * Pass the SPIR-V compiled from c-nvgpu-vulkan-empty.comp as argv[1].
 * Neither this C source nor the Vulkan loader is in route C's product path. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <vulkan/vulkan.h>

#define OK(call) do { VkResult r_ = (call); if (r_ != VK_SUCCESS) { \
    fprintf(stderr, "%s:%d: %s = %d\n", __FILE__, __LINE__, #call, r_); return 1; \
} } while (0)

static uint64_t now_ns(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return 0;
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    FILE *f = fopen(argv[1], "rb");
    if (!f) return 2;
    if (fseek(f, 0, SEEK_END)) return 2;
    long len = ftell(f);
    if (len <= 0 || len % 4 || len > 65536 || fseek(f, 0, SEEK_SET)) return 2;
    uint32_t *code = malloc((size_t)len);
    if (!code || fread(code, 1, (size_t)len, f) != (size_t)len) return 2;
    fclose(f);

    VkInstance instance;
    VkApplicationInfo app = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
                              .apiVersion = VK_API_VERSION_1_0 };
    VkInstanceCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
                                 .pApplicationInfo = &app };
    OK(vkCreateInstance(&ici, NULL, &instance));
    uint32_t nd = 0;
    OK(vkEnumeratePhysicalDevices(instance, &nd, NULL));
    if (!nd || nd > 32) return 2;
    VkPhysicalDevice devices[32];
    OK(vkEnumeratePhysicalDevices(instance, &nd, devices));
    VkPhysicalDevice gpu = VK_NULL_HANDLE;
    uint32_t family = UINT32_MAX;
    VkPhysicalDeviceProperties props;
    for (uint32_t d = 0; d < nd && !gpu; d++) {
        vkGetPhysicalDeviceProperties(devices[d], &props);
        if (props.vendorID != 0x10de) continue;
        uint32_t nq = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(devices[d], &nq, NULL);
        if (!nq || nq > 32) continue;
        VkQueueFamilyProperties q[32];
        vkGetPhysicalDeviceQueueFamilyProperties(devices[d], &nq, q);
        for (uint32_t i = 0; i < nq; i++) {
            if ((q[i].queueFlags & VK_QUEUE_COMPUTE_BIT) && q[i].queueCount) {
                gpu = devices[d]; family = i; break;
            }
        }
    }
    if (!gpu) { fprintf(stderr, "no NVIDIA compute queue\n"); return 2; }
    printf("device %s\nqueue_family %u\n", props.deviceName, family);
    float priority = 1.0f;
    VkDeviceQueueCreateInfo qi = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                                   .queueFamilyIndex = family, .queueCount = 1,
                                   .pQueuePriorities = &priority };
    VkDeviceCreateInfo dci = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
                               .queueCreateInfoCount = 1, .pQueueCreateInfos = &qi };
    VkDevice device;
    OK(vkCreateDevice(gpu, &dci, NULL, &device));
    VkQueue queue;
    vkGetDeviceQueue(device, family, 0, &queue);
    VkShaderModuleCreateInfo smci = { .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
                                      .codeSize = (size_t)len, .pCode = code };
    VkShaderModule shader;
    OK(vkCreateShaderModule(device, &smci, NULL, &shader));
    VkPipelineLayoutCreateInfo plci = { .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO };
    VkPipelineLayout layout;
    OK(vkCreatePipelineLayout(device, &plci, NULL, &layout));
    VkPipelineShaderStageCreateInfo stage = { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                                              .stage = VK_SHADER_STAGE_COMPUTE_BIT,
                                              .module = shader, .pName = "main" };
    VkComputePipelineCreateInfo pci = { .sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
                                        .stage = stage, .layout = layout };
    VkPipeline pipeline;
    OK(vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &pci, NULL, &pipeline));
    VkCommandPoolCreateInfo cpci = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
                                     .queueFamilyIndex = family };
    VkCommandPool pool;
    OK(vkCreateCommandPool(device, &cpci, NULL, &pool));
    VkCommandBufferAllocateInfo cbai = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
                                         .commandPool = pool,
                                         .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
                                         .commandBufferCount = 1 };
    VkCommandBuffer cmd;
    OK(vkAllocateCommandBuffers(device, &cbai, &cmd));
    VkCommandBufferBeginInfo bi = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
    OK(vkBeginCommandBuffer(cmd, &bi));
    vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline);
    vkCmdDispatch(cmd, 1, 1, 1);
    OK(vkEndCommandBuffer(cmd));
    VkFenceCreateInfo fci = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
    VkFence fence;
    OK(vkCreateFence(device, &fci, NULL, &fence));
    VkSubmitInfo submit = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
                            .commandBufferCount = 1, .pCommandBuffers = &cmd };
    for (int i = 0; i < 17; i++) {
        uint64_t start = now_ns();
        OK(vkQueueSubmit(queue, 1, &submit, fence));
        OK(vkWaitForFences(device, 1, &fence, VK_TRUE, 1000000000ull));
        uint64_t elapsed = now_ns() - start;
        if (i) printf("rt_ns %llu\n", (unsigned long long)elapsed);
        OK(vkResetFences(device, 1, &fence));
    }
    OK(vkDeviceWaitIdle(device));
    vkDestroyFence(device, fence, NULL);
    vkDestroyCommandPool(device, pool, NULL);
    vkDestroyPipeline(device, pipeline, NULL);
    vkDestroyPipelineLayout(device, layout, NULL);
    vkDestroyShaderModule(device, shader, NULL);
    vkDestroyDevice(device, NULL);
    vkDestroyInstance(instance, NULL);
    free(code);
    return 0;
}
