/* BOOTSTRAP-TOOL: full original QR oracle, mask score snapshots and body selfchecks.
 * Copyright 2014-2019 Embecosm/Bristol, qrduino contributors; GPL-3.0-or-later. */
#include <stdint.h>
#include <limits.h>
#include "beebsc.h"
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/qrduino/qrencode.c"
#include "../upstream/src/qrduino/qrtest.c"
static unsigned char obsheap[8192] __attribute__((aligned));
static const char *payloads[]={"http://www.mageec.com","AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA","","0123456789012345678901234567890123456789"};
static unsigned scores[8],selected,minimum,stopped;
static int setup(int c){memset(obsheap,0,sizeof(obsheap));init_heap_beebs(obsheap,8192);initeccsize(1,22);memcpy(strinbuf,payloads[c],strlen(payloads[c])+1);initframe();memset(scores,0,sizeof(scores));return VERSION==2&&WD==25&&WDB==4;}
static void observed_encode(void){

  unsigned mindem = 30000;
  unsigned char best = 0;
  unsigned char i;
  unsigned badness;

  stringtoqr ();
  fillframe ();			// Inisde loop to avoid having separate mask buffer
  memcpy (strinbuf, qrframe, WD * WDB);
  for (i = 0; i < 8; i++)
    {
      applymask (i);		// returns black-white imbalance
      badness = badcheck ();
      scores[i]=badness;
#if 0				//ndef PUREBAD
      if (badness < WD * WD * 5 / 4)
	{			// good enough - masks grow in compute complexity
	  best = i;
	  break;
	}
#endif
      if (badness < mindem)
	{
	  mindem = badness;
	  best = i;
	}
      if (best == 7)
	break;			// don't increment i to avoid redoing mask
      memcpy (qrframe, strinbuf, WD * WDB);	// reset filled frame
    }
  if (best != i)		// redo best mask - none good enough, last wasn't best
    applymask (best);
  selected=best; minimum=mindem; stopped=i;
  addfmt (best);		// add in final format bytes
}
static int64_t cellvalue(int cell){
 if(cell>=0&&cell<100)return strinbuf[cell];if(cell>=768&&cell<868)return qrframe[cell-768];
 if(cell>=1536&&cell<1636)return framebase[cell-1536];if(cell>=1664&&cell<1705)return framask[cell-1664];
 if(cell>=1780&&cell<1788)return scores[cell-1780];if(cell==1790)return selected;if(cell==1791)return minimum;if(cell==1792)return stopped;return INT64_MIN;}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe(int64_t encoded,EXTRA){int c=encoded/1048576,code=encoded%1048576,stage=code/2048,cell=code%2048;
 if(encoded<0||c>3||stage>9||!setup(c))return INT64_MIN;
 if(stage==9)observed_encode();else{stringtoqr();fillframe();memcpy(strinbuf,qrframe,100);if(stage){applymask(stage-1);scores[stage-1]=badcheck();}}
 return cellvalue(cell);}
int64_t repeat_observe(int64_t encoded,EXTRA){int n=encoded/2048,cell=encoded%2048;if(n<1||n>32)return INT64_MIN;
 for(int i=0;i<n;i++){if(!setup(0))return INT64_MIN;observed_encode();freeframe();freeecc();}return cellvalue(cell);}
int64_t oracle_selfcheck(int64_t c,EXTRA){if(c<0||c>3||!setup(c))return 0;observed_encode();unsigned char final[100],data[100];memcpy(final,qrframe,100);memcpy(data,strinbuf,100);
 if(!setup(c))return 0;qrencode();return memcmp(final,qrframe,100)==0&&memcmp(data,strinbuf,100)==0&&check_heap_beebs(obsheap);}
int64_t batch(int64_t n,EXTRA){if(n<0||n>32)return 0;if(!n)return 0;benchmark_body(1,n);return verify_benchmark(0);}
int64_t original_repeat_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;benchmark_body(1,n);unsigned char final[100],data[100];memcpy(final,qrframe,100);memcpy(data,strinbuf,100);int ok=verify_benchmark(0);
 for(int i=0;i<n;i++){if(!setup(0))return 0;observed_encode();freeframe();freeecc();}
 return ok&&memcmp(final,qrframe,100)==0&&memcmp(data,strinbuf,100)==0&&check_heap_beebs(obsheap);}
