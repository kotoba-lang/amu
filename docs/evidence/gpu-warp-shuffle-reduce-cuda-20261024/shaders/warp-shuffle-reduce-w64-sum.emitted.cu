__device__ float combine(float a,float b){return a+b;}
extern "C" __global__ void reduce_sum(const float* x,float* parts,unsigned int n){
 extern __shared__ float s[]; unsigned int i=blockIdx.x*blockDim.x+threadIdx.x; unsigned int l=threadIdx.x; unsigned int lane=l%32, warp=l/32;
 float v=i<n?x[i]:0.0f;
 for(unsigned int d=16;d>0;d>>=1){v=combine(v,__shfl_down_sync(0xffffffffu,v,d,32));}
 if(lane==0)s[warp]=v; __syncthreads();
 unsigned int warps=blockDim.x/32;
 if(warp==0){float a=lane<warps?s[lane]:0.0f;
  for(unsigned int d=warps/2;d>0;d>>=1){a=combine(a,__shfl_down_sync(0xffffffffu,a,d,warps));}
  if(lane==0)parts[blockIdx.x]=a;}
}
