#include <metal_stdlib>
using namespace metal;
float combine(float a, float b) { return a+b; }
kernel void reduce_sum(device const float* x [[buffer(0)]], device float* parts [[buffer(1)]], constant uint& n [[buffer(2)]], uint i [[thread_position_in_grid]], uint sgid [[thread_index_in_simdgroup]], uint sg [[simdgroup_index_in_threadgroup]], uint sgsize [[threads_per_simdgroup]], uint nsg [[simdgroups_per_threadgroup]], uint g [[threadgroup_position_in_grid]]) {
  threadgroup float partials[64];
  float v = i < n ? x[i] : 0.0f;
  v = simd_sum(v);
  if (sgid == 0u) { partials[sg] = v; }
  threadgroup_barrier(mem_flags::mem_threadgroup);
  for (uint d = nsg / 2u; d > 0u; d >>= 1u) {
    if (sg == 0u) {
      for (uint lid = sgid; lid < d; lid += sgsize) {
        partials[lid] = combine(partials[lid], partials[lid + d]);
      }
    }
    threadgroup_barrier(mem_flags::mem_threadgroup);
  }
  if (sg == 0u && sgid == 0u) { parts[g] = partials[0]; }
}
