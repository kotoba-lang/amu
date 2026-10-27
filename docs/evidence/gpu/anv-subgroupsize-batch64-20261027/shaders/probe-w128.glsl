#version 450
#extension GL_KHR_shader_subgroup_basic : require
// INSTRUMENT-LOCAL PROBE (verification channel, hand-written -- NOT the
// measured arm; the measured arm is the committed emitter's bytes). Writes
// the FORCED-SUBGROUP-SIZE reality check: what gl_SubgroupSize actually is
// under the pipeline's requiredSubgroupSize, plus the realized
// gl_NumSubgroups and workgroup size. JUN-59 subgroup 8/16/32 session,
// 2026-10-27.
layout(local_size_x = 128) in;
layout(set = 0, binding = 0, std430) writeonly buffer O { uint o[]; };
void main() {
  if (gl_SubgroupID == 0u && gl_SubgroupInvocationID == 0u) {
    o[0] = gl_SubgroupSize;
    o[1] = gl_NumSubgroups;
    o[2] = gl_WorkGroupSize.x;
  }
}
