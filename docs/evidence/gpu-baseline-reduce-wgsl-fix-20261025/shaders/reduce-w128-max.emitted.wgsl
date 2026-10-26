struct N { value: u32 };
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> parts: array<f32>;
@group(0) @binding(2) var<uniform> n: N;
var<workgroup> scratch: array<f32,128>;
fn combine(a:f32,b:f32)->f32{return max(a,b);}
@compute @workgroup_size(128) fn main(@builtin(global_invocation_id) gid:vec3<u32>,@builtin(local_invocation_id) lid:vec3<u32>,@builtin(workgroup_id) wid:vec3<u32>){
 let i=gid.x; scratch[lid.x]=x[min(i,n.value-1u)]; workgroupBarrier();
 var stride:u32=64u; loop { if(stride==0u){break;} if(lid.x<stride){scratch[lid.x]=combine(scratch[lid.x],scratch[lid.x+stride]);} workgroupBarrier(); stride=stride/2u;}
 if(lid.x==0u){parts[wid.x]=scratch[0];}
}
