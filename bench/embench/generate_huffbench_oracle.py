#!/usr/bin/env python3
# BOOTSTRAP-TOOL: diagnostic snapshots; timed C function is included unchanged.
import argparse,pathlib,hashlib
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
b=a.upstream.read_bytes()
if hashlib.sha256(b).hexdigest()!='db93b8ea3c68b178348834e738ba0628c8dbf28c338d4320aebab145683d8162':raise SystemExit('unreviewed Huffbench profile')
s=b.decode();body=s[s.index('void\ncompdecomp ('):s.index('\n\n\nint\nverify_benchmark')]
body=body.replace('compdecomp (byte * data, size_t data_len)','compdecomp_observe (byte * data, size_t data_len)',1)
assert body.count('size_t temp;')==1 and body.count('free_beebs (comp);')==1
body=body.replace('size_t temp;','size_t temp;\n  size_t observed_distinct = n;',1)
snapshot='''for(size_t z=0;z<500;z++) observation[z]=data[z];
  for(size_t z=0;z<501;z++) observation[500+z]=comp[z];
  for(size_t z=0;z<512;z++){observation[1001+z]=(int64_t)freq[z];observation[1769+z]=link[z];}
  for(size_t z=0;z<256;z++){observation[1513+z]=(int64_t)heap[z];observation[2281+z]=(int64_t)code[z];observation[2537+z]=clen[z];observation[2793+z]=(int64_t)heap2[z];observation[3049+z]=(unsigned char)outc[z];}
  observation[3305]=comp_len;observation[3306]=observed_distinct;observation[3307]=maxx;observation[3308]=maxi;
  free_beebs (comp);'''
body=body.replace('free_beebs (comp);',snapshot,1)
head='''/* BOOTSTRAP-TOOL: Embench diagnostic C copy with observation only.
 * Copyright 2014-2019 Embecosm Limited and University of Bristol.
 * Derived from Scott Robert Ladd, contributors James Pallister/Jeremy Bennett.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/huffbench/libhuffbench.c"
#include "../upstream/support/beebsc.c"
static int64_t observation[3309];
'''
tail='''
static void observe(void){init_heap_beebs((void*)heap,HEAP_SIZE);memcpy(test_data,orig_data,TEST_SIZE);memset(observation,0,sizeof observation);compdecomp_observe(test_data,TEST_SIZE);}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t state_cell(int64_t i,EXTRA){observe();return observation[i];}
int64_t oracle_selfcheck(int64_t n,EXTRA){observe();benchmark_body(1,1);if(!verify_benchmark(0))return 0;for(int i=0;i<500;i++)if(test_data[i]!=observation[i])return 0;for(int i=0;i<501;i++)if((unsigned char)heap[i]!=observation[500+i])return 0;return 1;}
int64_t batch(int64_t n,EXTRA){if(n<1||n>UINT_MAX)return 0;return verify_benchmark(benchmark_body(1,(unsigned)n));}
'''
a.output.write_text(head+body+tail)
