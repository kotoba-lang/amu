#include <metal_stdlib>
using namespace metal;
kernel void reduce_min(device const float* x [[buffer(0)]],device float* parts [[buffer(1)]],constant uint& n [[buffer(2)]],threadgroup float* s [[threadgroup(0)]],uint i [[thread_position_in_grid]],uint l [[thread_index_in_threadgroup]],uint g [[threadgroup_position_in_grid]],uint width [[threads_per_threadgroup]]){
 s[l]=i<n?x[i]:as_type<float>(0x7F800000u); threadgroup_barrier(mem_flags::mem_threadgroup);
 for(uint d=width/2;d>0;d>>=1){if(l<d){float a=s[l],b=s[l+d];s[l]=min(a,b);}threadgroup_barrier(mem_flags::mem_threadgroup);}
 if(l==0)parts[g]=s[0];
}
