#version 450
#define ITERMUL 1  /* JUN-59 session 9 knob: per-workgroup fatness */
#extension GL_KHR_shader_subgroup_basic : require
#extension GL_KHR_shader_subgroup_shuffle_relative : require
layout(local_size_x = 256) in;
layout(set = 0, binding = 0, std430) readonly buffer X { float x[]; };
layout(set = 0, binding = 1, std430) writeonly buffer Parts { float parts[]; };
layout(set = 0, binding = 2, std430) readonly buffer N { uint n; };
shared float partials[256];
float combine(float a, float b) { return a+b; }
void main() {
  for (uint it = 0u; it < uint(ITERMUL); it++) { /* ITERMUL wrapper */
  uint i = gl_GlobalInvocationID.x;
  float v = i < n ? x[i] : 0.0;
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
  } /* ITERMUL wrapper end */
}
