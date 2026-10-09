#!/usr/bin/env python3
# BOOTSTRAP-TOOL: pinned unchanged C regex engine and diagnostic fixtures.
import argparse,hashlib,json,pathlib
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('source',type=pathlib.Path);p.add_argument('fixtures',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);a=p.parse_args()
for name,sha in [('libslre.c','ff918566aa585c665433fecfa1c56ca0136f819df0a5654f2ae98cc696d96056'),('slre.h','87bdc34b18e269c46c13c3e221f2618fa2aac2b4299fe59561810522880e3264')]:
 if hashlib.sha256((a.upstream/name).read_bytes()).hexdigest()!=sha:raise SystemExit('unreviewed SLRE profile')
cases=json.loads(a.fixtures.read_text());cases += [{'regex':'('*100+'a'+')'*100,'text':'a','caps':100},{'regex':'a|'*101+'b','text':'b','caps':1}]
for c in cases:
 if not c['regex'].isascii() or not c['text'].isascii() or not 1<=c['caps']<=100:raise SystemExit('unsupported fixture profile')
a.directory.mkdir(parents=True,exist_ok=True)
(a.directory/'fixtures.json').write_text(json.dumps(cases,indent=2)+'\n')
def choose(key,typ):
 expr=json.dumps(cases[-1][key]) if typ=='string' else str(cases[-1][key])
 for i in reversed(range(len(cases)-1)):
  value=json.dumps(cases[i][key]) if typ=='string' else str(cases[i][key]);expr=f'(if (= i {i}) {value} {expr})'
 return f'(defn- fixture-{key} [i :i64] :{typ} {expr})\n'
s=a.source.read_text();old='(:export [batch test-slre observe bounds-probe])';assert s.count(old)==1
s=s.replace(old,'(:export [batch test-slre observe bounds-probe observe-fixture])',1)
s+=choose('regex','string')+choose('text','string')+choose('caps','i64')
s+='''(defn observe-fixture [encoded :i64] :i64
 (let [i (quot encoded 1024) cell (rem encoded 1024) info (vector-alloc 804)
       answer (slre-match (fixture-regex i) (fixture-text i) info (fixture-caps i))]
  (if (= cell 804) answer (vector-at info cell))))
'''
(a.directory/'fixture-audit.kotoba').write_text(s)
rows=',\n'.join('{'+json.dumps(c['regex'])+'"\\0\\0\\0\\0"'+','+json.dumps(c['text'])+','+str(c['caps'])+'}' for c in cases)
c='''/* BOOTSTRAP-TOOL: unchanged pinned SLRE engine; initialized observation storage.
 * Copyright 2004-2013 Sergey Lyubka/Cesanta; 2014-2019 Embecosm/Bristol.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/slre/libslre.c"
struct fixture { const char *re,*s; int caps; };
static struct fixture fixtures[]={
'''+rows+'''};
static int64_t state[804];
static struct slre_cap captures[100];
static int observed_match(const char *re,const char *s,int caps){
 struct regex_info info;memset(&info,0,sizeof(info));memset(captures,0,sizeof(captures));
 info.num_caps=caps;info.caps=captures;const char *original=re;
 if(strlen(re)>=4 && memcmp(re,"(?i)",4)==0){info.flags|=IGNORE_CASE;re+=4;}
 int result=foo(re,strlen(re),s,strlen(s),&info);
 state[0]=info.num_brackets;state[1]=info.num_branches;state[2]=info.num_caps;state[3]=info.flags;
 for(int i=0;i<100;i++){
 state[4+i*4]=info.brackets[i].ptr?info.brackets[i].ptr-original:0;
 state[5+i*4]=info.brackets[i].len;state[6+i*4]=info.brackets[i].branches;state[7+i*4]=info.brackets[i].num_branches;
 state[404+i*2]=info.branches[i].bracket_index;state[405+i*2]=info.branches[i].schlong?info.branches[i].schlong-original:0;
 state[604+i*2]=captures[i].ptr?captures[i].ptr-s:0;state[605+i*2]=captures[i].len;}
 return result;
}
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
int64_t fixture_selfcheck(int64_t i,EXTRA){if(i<0||i>=sizeof(fixtures)/sizeof(fixtures[0]))return 0;
 struct fixture f=fixtures[i];int a=observed_match(f.re,f.s,f.caps);struct slre_cap old[100];memcpy(old,captures,sizeof(old));
 struct slre_cap actual[100];memset(actual,0,sizeof(actual));int b=slre_match(f.re,f.s,strlen(f.s),actual,f.caps);
 if(a!=b)return 0;for(int j=0;j<100;j++)if(old[j].ptr!=actual[j].ptr||old[j].len!=actual[j].len)return 0;return 1;}
int64_t observe_fixture(int64_t encoded,EXTRA){int i=encoded/1024,cell=encoded%1024;
 if(encoded<0||i>=sizeof(fixtures)/sizeof(fixtures[0])||cell>804)return INT64_MIN;
 struct fixture f=fixtures[i];int result=observed_match(f.re,f.s,f.caps);return cell==804?result:state[cell];}
int64_t observe(int64_t encoded,EXTRA){if(encoded<0||encoded>804)return INT64_MIN;
 int result=0;for(int i=0;i<4;i++)result+=observed_match(regexes[i],text,1);return encoded==804?result:state[encoded];}
int64_t batch(int64_t n,EXTRA){if(n<1||n>UINT_MAX)return 0;return verify_benchmark(benchmark_body(1,(unsigned)n));}
int64_t original_result(int64_t n,EXTRA){if(n<1||n>UINT_MAX)return 0;return benchmark_body(1,(unsigned)n);}
'''
(a.directory/'c-bridge.c').write_text(c)
