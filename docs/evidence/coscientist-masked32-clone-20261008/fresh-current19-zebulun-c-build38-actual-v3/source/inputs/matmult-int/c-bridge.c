/* BOOTSTRAP-TOOL: original initialization, body, verifier and actual globals. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/src/matmult-int/matmult-int.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t bench(int64_t n,EXTRA){if(n==0)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t observe(int64_t encoded,EXTRA){int n=encoded/2048,i=encoded%2048;memset(ArrayA,0,sizeof(ArrayA));memset(ArrayB,0,sizeof(ArrayB));memset(ResultArray,0,sizeof(ResultArray));initialise_benchmark();if(n)benchmark_body(1,n);
 if(i<400)return ArrayA_ref[i/20][i%20];if(i<800){i-=400;return ArrayB_ref[i/20][i%20];}if(i<1200){i-=800;return ArrayA[i/20][i%20];}if(i<1600){i-=1200;return ArrayB[i/20][i%20];}if(i<2000){i-=1600;return ResultArray[i/20][i%20];}if(i==2000)return Seed;return INT64_MIN;}
