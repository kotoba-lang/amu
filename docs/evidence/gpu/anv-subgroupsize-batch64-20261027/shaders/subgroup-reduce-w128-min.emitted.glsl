#version 450
#extension GL_KHR_shader_subgroup_basic : require
#extension GL_KHR_shader_subgroup_shuffle_relative : require
layout(local_size_x = 128) in;
layout(set = 0, binding = 0, std430) readonly buffer X { float x[]; };
layout(set = 0, binding = 1, std430) writeonly buffer Parts { float parts[]; };
layout(set = 0, binding = 2, std430) readonly buffer N { uint n; };
shared float partials[128];
float combine(float a, float b) { return min(a,b); }
void main() {
  uint i = gl_GlobalInvocationID.x;
  float v = i < n ? x[i] : uintBitsToFloat(0x7F800000u);
  uint fold = min(gl_SubgroupSize, gl_WorkGroupSize.x);
  for (uint d = fold / 2u; d > 0u; d >>= 1u) {
    float s = subgroupShuffleDown(v, d);
    if (gl_SubgroupInvocationID + d < fold) { v = combine(v, s); }
  }
  if (gl_SubgroupInvocationID == 0u) { partials[gl_SubgroupID] = v; }
  barrier();
  for (uint d = gl_NumSubgroups / 2u; d > 0u; d >>= 1u) {
    if (gl_SubgroupID == 0u) {
      for (uint lid = gl_SubgroupInvocationID; lid < d; lid += gl_SubgroupSize) {
        partials[lid] = combine(partials[lid], partials[lid + d]);
      }
    }
    barrier();
  }
  if (gl_SubgroupID == 0u && gl_SubgroupInvocationID == 0u) { parts[gl_WorkGroupID.x] = partials[0]; }
}
