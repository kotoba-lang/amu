/* BOOTSTRAP-TOOL: unchanged pinned SLRE engine; initialized observation storage.
 * Copyright 2004-2013 Sergey Lyubka/Cesanta; 2014-2019 Embecosm/Bristol.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdint.h>
#include <limits.h>
#define GLOBAL_SCALE_FACTOR 1
#include "../upstream/src/slre/libslre.c"
struct fixture { const char *re,*s; int caps; };
static struct fixture fixtures[]={
{"(ab)+""\0\0\0\0","abbbababaabccababcacbcbcbabbabcbabcabcbbcbbac",1},
{"(b.+)+""\0\0\0\0","abbbababaabccababcacbcbcbabbabcbabcabcbbcbbac",1},
{"a[ab]*""\0\0\0\0","abbbababaabccababcacbcbcbabbabcbabcabcbbcbbac",1},
{"([ab^c][ab^c])+""\0\0\0\0","abbbababaabccababcacbcbcbabbabcbabcabcbbcbbac",1},
{"^ab""\0\0\0\0","abc",1},
{"ab$""\0\0\0\0","xxab",1},
{"^ab$""\0\0\0\0","ab",1},
{"^ab$""\0\0\0\0","xab",1},
{".""\0\0\0\0","",1},
{"a?b""\0\0\0\0","b",1},
{"a?b""\0\0\0\0","ab",1},
{"a*b""\0\0\0\0","aaab",1},
{"a*b""\0\0\0\0","b",1},
{"a+b""\0\0\0\0","b",1},
{"a+b""\0\0\0\0","aaab",1},
{"a.*?b""\0\0\0\0","axxbxxb",1},
{"(ab|cd)+""\0\0\0\0","cdabab",1},
{"(a)(b)""\0\0\0\0","ab",2},
{"(a(b))""\0\0\0\0","ab",2},
{"(ab)c""\0\0\0\0","abc",1},
{"(a|ab)c""\0\0\0\0","abc",1},
{"[a-z]+""\0\0\0\0","ABCdef",1},
{"(?i)[a-z]+""\0\0\0\0","ABCdef",1},
{"\\d+""\0\0\0\0","12ab",1},
{"\\s+""\0\0\0\0"," \t\nx",1},
{"\\S+""\0\0\0\0","a b",1},
{"\\x41+""\0\0\0\0","AA",1},
{"\\.""\0\0\0\0",".",1},
{"[^ab]+""\0\0\0\0","ccab",1},
{"[""\0\0\0\0","x",1},
{"a\\""\0\0\0\0","a",1},
{"\\q""\0\0\0\0","q",1},
{"\\xGG""\0\0\0\0","G",1},
{"\\x4""\0\0\0\0","4",1},
{"(""\0\0\0\0","a",1},
{")""\0\0\0\0","a",1},
{"()""\0\0\0\0","a",1},
{"*a""\0\0\0\0","a",1},
{"(a)(b)""\0\0\0\0","ab",1},
{"""\0\0\0\0","",1},
{"((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((((a))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))""\0\0\0\0","a",100},
{"a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|a|b""\0\0\0\0","b",1}};
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
