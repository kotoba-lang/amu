struct N { value: u32 };
@group(0) @binding(0) var<storage,read> x: array<f32>;
@group(0) @binding(1) var<storage,read_write> parts: array<f32>;
@group(0) @binding(2) var<uniform> n: N;
var<workgroup> scratch: array<f32,1024>;
fn combine(a:f32,b:f32)->f32{return a+b;}
@compute @workgroup_size(1024) fn main(@builtin(global_invocation_id) gid:vec3<u32>,@builtin(local_invocation_id) lid:vec3<u32>,@builtin(workgroup_id) wid:vec3<u32>){
 let i=gid.x; scratch[lid.x]=select(0.0,x[i],i<n.value); workgroupBarrier();
 var stride:u32=512u; loop { if(stride==0u){break;} if(lid.x<stride){scratch[lid.x]=combine(scratch[lid.x],scratch[lid.x+stride]);} workgroupBarrier(); stride=stride/2u;}
 if(lid.x==0u){parts[wid.x]=scratch[0];}
}
