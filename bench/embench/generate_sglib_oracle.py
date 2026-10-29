#!/usr/bin/env python3
# BOOTSTRAP-TOOL: pinned original container body plus untimed observations.
import argparse,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('source',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
pins={'src/sglib-combined/combined.c':'7d817bec0dd88d8c462dfd56a026728395498e210dae75658c80ebaf17dff70c','src/sglib-combined/sglib.h':'335eef568a3516b6a9d6edb00b3b0c141ee9a64937fbe6ec030b5485a5d4b96a','support/beebsc.c':'b066ac5ff79fdd591da69264919183d03376f5b78985b0eb310cf629dcf8b42c','support/beebsc.h':'e584f3ef1e39238e44e7242e21fdfa2e77589f4e03f4632476e9f01cb212fb07'}
for f,d in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=d:raise SystemExit('unreviewed SGLIB profile: '+f)
a.directory.mkdir(parents=True,exist_ok=True)
s=a.source.read_text();old='(:export [batch test-sglib observe bounds-probe])';assert s.count(old)==1
s=s.replace(old,'(:export [batch test-sglib observe bounds-probe observe-stage])',1)
s=s.replace('(vector-alloc 1760)','(vector-alloc 1860)')
old='(tree-current (put v 0 (+ (vector-at v 0) (vector-at v (t id 0)))))';assert s.count(old)==1
s=s.replace(old,'(tree-current (put (record-node v id) 0 (+ (vector-at v 0) (vector-at v (t id 0)))))',1)
s+='''(defn- record-node [v :vector-i64 id :i64] :vector-i64
 (put (put v (+ 1760 (vector-at v 10)) id) 10 (+ (vector-at v 10) 1)))
(defn- stages [v :vector-i64 limit :i64] :vector-i64
 (let [a (quick v)] (if (= limit 0) a
  (let [b (list-stage a)] (if (= limit 1) b
   (let [c (hash-stage b)] (if (= limit 2) c
    (let [d1 (queue-stage c)] (if (= limit 3) d1
     (let [e (heap-stage d1)] (if (= limit 4) e (tree-stage e))))))))))))
(defn observe-stage [encoded :i64] :i64
 (let [stage (quot encoded 4096) cell (rem encoded 4096) result (stages (vector-alloc 1860) stage)] (vector-at result cell)))
'''
(a.directory/'stage-audit.kotoba').write_text(s)
source=(a.upstream/'src/sglib-combined/combined.c').read_text();start=source.index('\tint i;',source.index('benchmark_body(unsigned int lsf, unsigned int gsf)\n{'));end=source.index('\n      }\n\n  return cnt;',start);body=source[start:end]
markers=[('\t/* Doubly linked list */','snap(0,0,0,a,0,0,NULL);'),('\t/* Hash table */','snap(1,cnt,2400,a,0,0,NULL);'),('\t/* Queue */','snap(2,cnt,4000,a,0,0,NULL);'),('\t// print parameters','snap(3,cnt,4000,a,ai,aj,NULL);'),('\t/* RB Tree */','snap(4,cnt,4000,a,ai,aj,NULL);')]
for marker,call in markers:
 assert body.count(marker)==1;body=body.replace(marker,call+'\n'+marker,1)
# Record traversal identities in the observation-only copy of the exact body.
old='\t    cnt += te->n;';assert body.count(old)==1;body=body.replace(old,'\t    visit[visit_count++]=tree_id(te);\n'+old,1)
body+='\nsnap(5,cnt,6400,a,ai,aj,the_tree);\n'
c='''/* BOOTSTRAP-TOOL: exact pinned C body with snapshots, no timed instrumentation.
 * Copyright 2014-2019 Embecosm / University of Bristol.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/sglib-combined/combined.c"
static int64_t states[6][1860];static int64_t visit[100];static int visit_count;
static int list_id(dllist *p){return p?(int)(((char*)p-heap)/sizeof(dllist))+1:0;}
static int hash_id(ilist *p){return p?(int)(((char*)p-heap-2400)/sizeof(ilist))+1:0;}
static int tree_id(rbtree *p){return p?(int)(((char*)p-heap-4000)/sizeof(rbtree))+1:0;}
static void snap(int stage,int cnt,int bytes,int *a,int ai,int aj,rbtree *root){int64_t *v=states[stage];
 v[0]=cnt;v[1]=stage>=1?list_id(the_list):0;v[2]=stage==5?tree_id(root):0;v[3]=bytes;
 for(int i=0;i<100;i++)v[100+i]=array2[i];
 if(stage>=1)for(int i=0;i<100;i++){dllist *p=(dllist*)(heap+i*sizeof(dllist));v[200+i*3]=p->i;v[201+i*3]=list_id(p->ptr_to_next);v[202+i*3]=list_id(p->ptr_to_previous);}
 if(stage>=2){for(int i=0;i<100;i++){ilist *p=(ilist*)(heap+2400+i*sizeof(ilist));v[500+i*2]=p->i;v[501+i*2]=hash_id(p->next);}for(int i=0;i<20;i++)v[700+i]=hash_id(htab[i]);}
 if(stage>=3){for(int i=0;i<100;i++)v[720+i]=a[i];v[5]=ai;v[6]=aj;v[7]=stage>=4?ai:0;}
 if(stage==5){for(int i=0;i<100;i++){rbtree *p=(rbtree*)(heap+4000+i*sizeof(rbtree));v[900+i*4]=p->n;v[901+i*4]=p->color_field;v[902+i*4]=tree_id(p->left);v[903+i*4]=tree_id(p->right);}v[8]=0;v[9]=0;v[10]=visit_count;for(int i=0;i<visit_count;i++)v[1760+i]=visit[i];}}
static void observed(unsigned n){memset(states,0,sizeof(states));memset(heap,0,sizeof(heap));visit_count=0;
 volatile int cnt;for(unsigned run=0;run<n;run++){visit_count=0;
'''+body+'''}}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t observe_stage(int64_t encoded,EXTRA){int stage=encoded/4096,cell=encoded%4096;if(encoded<0||stage>5||cell>=1860)return INT64_MIN;observed(1);return states[stage][cell];}
int64_t oracle_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;observed((unsigned)n);int64_t expected[1860];memcpy(expected,states[5],sizeof(expected));int result=benchmark_body(1,(unsigned)n);
 int a[101]={0};snap(5,result,6400,a,0,100,NULL);
 // The original body has no public tree root; compare its public array/list/hash and result.
 for(int i=100;i<720;i++)if(states[5][i]!=expected[i])return 0;
 for(int i=900;i<1300;i++)if(states[5][i]!=expected[i])return 0;
 return result==15050 && verify_benchmark(result);}
int64_t observe_repeat(int64_t encoded,EXTRA){int n=encoded/4096,cell=encoded%4096;if(encoded<0||n<1||n>32||cell>=1760)return INT64_MIN;observed(n);return states[5][cell];}
int64_t batch(int64_t n,EXTRA){if(n<1||n>UINT_MAX)return 0;return verify_benchmark(benchmark_body(1,(unsigned)n));}
'''
(a.directory/'c-bridge.c').write_text(c)
repeat=a.source.read_text().replace('(:export [batch test-sglib observe bounds-probe])','(:export [batch test-sglib observe bounds-probe repeat-observe])',1)
repeat+='''(defn repeat-observe [encoded :i64] :i64
 (let [n (quot encoded 4096) cell (rem encoded 4096) result (repeats (vector-alloc 1760) n)] (vector-at result cell)))
'''
(a.directory/'repeat-audit.kotoba').write_text(repeat)
fields={}
for stage in range(6):
 cells=list(range(100,200))
 if stage>=1:cells+=[0,1,3]+list(range(200,500))
 if stage>=2:cells+=list(range(500,720))
 if stage>=3:cells+=[6]+list(range(720,820))
 if stage==3:cells+=[5]
 if stage>=4:cells+=[7]
 if stage==5:cells+=[2,8,9,10]+list(range(900,1300))+list(range(1760,1860))
 fields[str(stage)]=sorted(cells)
(a.directory/'observed-fields.json').write_text(json.dumps({'capacity':1760,'diagnosticCapacity':1860,'stages':fields,'sourcePins':pins,'representation':'node identities by allocation order; padding and inactive iterator slots excluded'},indent=2)+'\n')
