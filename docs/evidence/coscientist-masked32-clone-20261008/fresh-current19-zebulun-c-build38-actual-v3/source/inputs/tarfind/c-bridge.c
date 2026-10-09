/* BOOTSTRAP-TOOL: unchanged original C body, actual heap and RNG state. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include <limits.h>
#include "../upstream/support/beebsc.c"
#include "../upstream/src/tarfind/tarfind.c"
_Static_assert(sizeof(tar_header_t)==257,"unreviewed header layout");
_Static_assert(offsetof(tar_header_t,isLink)==156,"unreviewed link layout");
_Static_assert(offsetof(tar_header_t,size)==124,"unreviewed size layout");
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t bench(int64_t n,EXTRA){srand_beebs(0);if(!n)return 0;initialise_benchmark();return verify_benchmark(benchmark_body(1,n));}
int64_t observe(int64_t encoded,EXTRA){int n=encoded/2048,f=encoded%2048;memset(heap,0,sizeof(heap));srand_beebs(0);int r=n?benchmark_body(1,n):0;if(f==1125)return seed;if(f==1126)return r;if(f>=1125)return INT64_MIN;int64_t acc=0;for(int i=0;i<8;i++){int index=f*8+i;unsigned char byte=index<8995?(unsigned char)heap[index]:0;acc=acc*256+byte;}return acc;}
