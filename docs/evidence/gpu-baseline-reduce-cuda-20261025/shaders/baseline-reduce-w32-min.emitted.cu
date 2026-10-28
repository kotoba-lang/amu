extern "C" __global__ void reduce_min(const float* x,float* parts,unsigned int n){
 extern __shared__ float s[]; unsigned int i=blockIdx.x*blockDim.x+threadIdx.x; unsigned int l=threadIdx.x;
 s[l]=i<n?x[i]:__uint_as_float(0x7F800000u); __syncthreads();
 for(unsigned int d=blockDim.x/2;d>0;d>>=1){if(l<d){float a=s[l],b=s[l+d];s[l]=fminf(a,b);}__syncthreads();}
 if(l==0)parts[blockIdx.x]=s[0];
}
