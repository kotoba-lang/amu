__device__ float combine(float a, float b) { return a+b; }
extern "C" __global__ void reduce_sum(const float* x, float* parts, unsigned int n){
  __shared__ float partials[256];
  unsigned int i = blockIdx.x*blockDim.x + threadIdx.x;
  unsigned int sgsize = warpSize;
  unsigned int sgid = threadIdx.x % sgsize;
  unsigned int sg = threadIdx.x / sgsize;
  float v = i < n ? x[i] : 0.0f;
  unsigned int fold = sgsize < blockDim.x ? sgsize : blockDim.x;
  unsigned int mask = __activemask();
  for (unsigned int d = fold / 2u; d > 0u; d >>= 1u) {
    float s = __shfl_down_sync(mask, v, d, fold);
    if (sgid + d < fold) { v = combine(v, s); }
  }
  if (sgid == 0u) { partials[sg] = v; }
  __syncthreads();
  unsigned int nsg = (blockDim.x + sgsize - 1) / sgsize;
  for (unsigned int d = nsg / 2u; d > 0u; d >>= 1u) {
    if (sg == 0u) {
      for (unsigned int lid = sgid; lid < d; lid += sgsize) {
        partials[lid] = combine(partials[lid], partials[lid + d]);
      }
    }
    __syncthreads();
  }
  if (sg == 0u && sgid == 0u) { parts[blockIdx.x] = partials[0]; }
}
