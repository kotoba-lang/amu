#!/usr/bin/env python3
# BOOTSTRAP-TOOL: unchanged STARC calls and globals, untimed observation only.
import argparse,pathlib,hashlib,json
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('fields',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
if hashlib.sha256(a.upstream.read_bytes()).hexdigest()!='389c4bae5caba79a6f9139e02bf5e61c92921a756ec01200d2d2f16dc1c4ccf5':raise SystemExit('unreviewed Statemate profile')
m=json.loads(a.fields.read_text());assert m['size']==169 and len(m['fields'])==105
head='''/* BOOTSTRAP-TOOL: pinned STARC oracle; original functions unchanged.
 * Copyright 1998/1999 C-LAB Paderborn, 2014-2019 Embecosm/University of Bristol.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/statemate/libstatemate.c"
static int64_t observation[4*169];
static void prepare(unsigned test){memset(Bitlist,0,64);
'''+''.join(f'{x["name"]}=0;\n' for x in m['fields'])+'''time=test;}
static void snapshot(unsigned stage){int64_t *v=observation+stage*169;
for(int i=0;i<64;i++)v[i]=Bitlist[i];
'''+''.join(f'v[{x["slot"]}]=(int64_t){x["name"]};\n' for x in m['fields'])+'''}
static void observe(unsigned test){prepare(test);snapshot(0);memset(Bitlist,0,64);init();snapshot(1);interface();snapshot(2);FH_DU();snapshot(3);}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t stage_cell(int64_t encoded,EXTRA){unsigned test=encoded/4096,code=encoded%4096,stage=code/169,cell=code%169;
 if(encoded<0||test>2||stage>3)return INT64_MIN;observe(test);return observation[stage*169+cell];}
int64_t oracle_selfcheck(int64_t test,EXTRA){if(test<0||test>2)return 0;observe(test);prepare(test);benchmark_body(1,1);snapshot(0);
 for(int i=0;i<169;i++)if(observation[i]!=observation[3*169+i])return 0;return test==0?verify_benchmark(0):1;}
int64_t repeat_cell(int64_t encoded,EXTRA){unsigned n=encoded/169,cell=encoded%169;
 if(encoded<0||n<1||n>32)return INT64_MIN;prepare(0);benchmark_body(1,n);snapshot(0);return observation[cell];}
int64_t batch(int64_t n,EXTRA){if(n<1||n>UINT_MAX)return 0;prepare(0);return verify_benchmark(benchmark_body(1,(unsigned)n));}
'''
a.output.write_text(head)
