#!/usr/bin/env python3
# BOOTSTRAP-TOOL: snapshots in an untimed copy; timed upstream body unchanged.
import argparse,hashlib,pathlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
b=a.upstream.read_bytes()
if hashlib.sha256(b).hexdigest()!='7d15a238b045f23d5206406fe0d5a15bd4050cf0ccd7e4c3dc49fb71429e2081':raise SystemExit('unreviewed NSichneu profile')
s=b.decode();start=s.index('static int __attribute__ ((noinline))\nbenchmark_body(');end=s.index('\n\n\nint\nverify_benchmark',start);body=s[start:end]
body=body.replace('benchmark_body(', 'benchmark_observe(',1)
pattern=r'(?=/\* Permutation for Place P[12] : [0-9, ]+ \*/)'
body,n=re.subn(pattern,'snapshot(stage++);\n\t',body);assert n==126
needle='\n      }\n\n  return 0;';assert body.count(needle)==1
body=body.replace(needle,'\n        snapshot(stage++);\n      }\n\n  return 0;')
head='''/* BOOTSTRAP-TOOL: pinned NSichneu diagnostic C copy.
 * Copyright 1998/1999 C-LAB Paderborn, 2014-2019 Embecosm/University of Bristol.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/nsichneu/libnsichneu.c"
static int64_t observation[127*17];
static unsigned stage;
static void snapshot(unsigned n){
 observation[n*17]=P1_is_marked;observation[n*17+1]=P2_is_marked;observation[n*17+2]=P3_is_marked;
 for(int i=0;i<3;i++)observation[n*17+3+i]=P1_marking_member_0[i];
 for(int i=0;i<5;i++)observation[n*17+6+i]=P2_marking_member_0[i];
 for(int i=0;i<6;i++)observation[n*17+11+i]=P3_marking_member_0[i];
}
static int64_t seed_value(int test,int i){
 if(test==0)return 0;
 if(test==1)return i==3?-2:i<6?1:i==6?-3:2;
 if(test==2)return i==4?-2:i<6?1:i==7?-3:2;
 if(test==3)return i<6?i-4:(i%3)-1;
 if(test==4)return -7;
 if(test==5)return 5+(i*7)%3;
 if(i<6)return 0;if(i>=11)return 9;
 if(test==6)return i==6?-3:i==9?3:2;
 return i==6?7:i==7?-3:2;
}
static void prepare(int test){
 for(int i=0;i<3;i++)P1_marking_member_0[i]=seed_value(test,i+3);
 for(int i=0;i<5;i++)P2_marking_member_0[i]=seed_value(test,i+6);
 for(int i=0;i<6;i++)P3_marking_member_0[i]=seed_value(test,i+11);
}
'''
tail='''
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t stage_cell(int64_t encoded,EXTRA){
 int test=encoded/4096,code=encoded%4096,n=code/17,cell=code%17;
 if(encoded<0||test>7||n>126)return INT64_MIN;
 prepare(test);stage=0;benchmark_observe(1,1);return observation[n*17+cell];
}
int64_t oracle_selfcheck(int64_t test,EXTRA){
 if(test<0||test>7)return 0;
 prepare(test);stage=0;benchmark_observe(1,1);
 if(stage!=127)return 0;
 prepare(test);benchmark_body(1,1);snapshot(0);
 for(int i=0;i<17;i++)if(observation[i]!=observation[126*17+i])return 0;
 return 1;
}
int64_t batch(int64_t n,EXTRA){
 if(n<1||n>UINT_MAX)return 0;prepare(0);
 return verify_benchmark(benchmark_body(1,(unsigned)n));
}
'''
a.output.write_text(head+body+tail)
