extern "C" __global__ void reduce_sum(const float* x,float* parts,unsigned int n){
 extern __shared__ float s[]; unsigned int i=blockIdx.x*blockDim.x+threadIdx.x; unsigned int l=threadIdx.x;
 s[l]=i<n?x[i]:0.0f; __syncthreads();
 for(unsigned int d=blockDim.x/2;d>0;d>>=1){if(l<d){float a=s[l],b=s[l+d];s[l]=a+b;}__syncthreads();}
 if(l==0)parts[blockIdx.x]=s[0];
}
