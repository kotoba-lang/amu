/* BOOTSTRAP-TOOL: unchanged original full body and verifier. */
#define observe observe_headers
#include "headers-bridge.c"
#undef observe
static int64_t full_value(int cell){if(cell>=1536&&cell<1600)return gCoeffBuf[cell-1536];if(cell>=2048&&cell<2304)return gMCUBufR[cell-2048];if(cell>=2304&&cell<2560)return gMCUBufG[cell-2304];if(cell>=2560&&cell<2816)return gMCUBufB[cell-2560];return cellvalue(cell);}
int64_t bench(int64_t n,EXTRA){if(n<1||n>32)return 0;benchmark_body(1,n);return verify_benchmark(0);}
int64_t repeated_state(int64_t encoded,EXTRA){int n=encoded/4096,cell=encoded%4096;if(encoded<0||n<1||n>32)return INT64_MIN;
 reset();memset(gCoeffBuf,0,sizeof(gCoeffBuf));memset(gMCUBufR,0,sizeof(gMCUBufR));memset(gMCUBufG,0,sizeof(gMCUBufG));memset(gMCUBufB,0,sizeof(gMCUBufB));benchmark_body(1,n);lastStatus=pjpeg_decode_mcu();if(!verify_benchmark(0)||lastStatus!=PJPG_NO_MORE_BLOCKS)return INT64_MIN;return full_value(cell);}
