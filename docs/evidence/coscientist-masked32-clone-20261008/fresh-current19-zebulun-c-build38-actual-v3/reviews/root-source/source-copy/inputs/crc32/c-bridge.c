/* BOOTSTRAP-TOOL: unchanged C body/verifier; untimed prefix copy. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include "../upstream/support/beebsc.c"
#include "../upstream/src/crc32/crc_32.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
static DWORD
crc_prefix (int stop)
{
  int i;
  register DWORD oldcrc32;

  oldcrc32 = 0xFFFFFFFF;

  for (i = 0; i < stop; ++i)
    {
      oldcrc32 = UPDC32 (rand_beebs (), oldcrc32);
    }

  return ~oldcrc32;
}

int64_t bench(int64_t n,EXTRA){if(n==0)return 0;return verify_benchmark(benchmark_body(1,n));}
int64_t prefix_crc(int64_t n,EXTRA){srand_beebs(0);return crc_prefix(n)&0xffffffffUL;}
int64_t prefix_seed(int64_t n,EXTRA){srand_beebs(0);crc_prefix(n);return seed;}
int64_t table_entry(int64_t i,EXTRA){return crc_32_tab[i];}
int64_t oracle_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;srand_beebs(0);DWORD r=crc_prefix(1024);unsigned long expected_seed=seed;int result=benchmark_body(1,n);return result==(int)(r%32768)&&verify_benchmark(result)&&seed==expected_seed;}
