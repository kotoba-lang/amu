#!/usr/bin/env python3
# BOOTSTRAP-TOOL: original CRC/RNG and repeated body, two table representations.
import argparse,pathlib,hashlib,json,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('directory',type=pathlib.Path);p.add_argument('--representation',choices=['chunks','scalar'],default='chunks');a=p.parse_args()
pins={'src/crc32/crc_32.c':'98966b59550ceed67bef64f0e8968113535bdc5aee95e06432fa5b171438cc41','support/beebsc.c':'b066ac5ff79fdd591da69264919183d03376f5b78985b0eb310cf629dcf8b42c','support/support.h':'3c0862b8279c8d01951b2c8a180f04bd996431c2fb63ffb91773e38895f25e53'}
for f,s in pins.items():
 if hashlib.sha256((a.upstream/f).read_bytes()).hexdigest()!=s:raise SystemExit('unreviewed CRC32 profile: '+f)
s=(a.upstream/'src/crc32/crc_32.c').read_text();table=[int(x,16) for x in re.findall(r'0x[0-9a-fA-F]+',re.search(r'static const UNS_32_BITS crc_32_tab\[\] = \{(.*?)\};',s,re.S).group(1))][1:]
if len(table)!=256:raise SystemExit('unreviewed CRC table shape')
def scalar(xs,start=0):
 if len(xs)==1:return str(xs[0])
 n=len(xs)//2;return '(if (< i '+str(start+n)+') '+scalar(xs[:n],start)+' '+scalar(xs[n:],start+n)+')'
def chunks(xs,start=0):
 if len(xs)==16:return '(vector-at ['+' '.join(map(str,xs))+'] (- i '+str(start)+'))'
 n=len(xs)//2;return '(if (< i '+str(start+n)+') '+chunks(xs[:n],start)+' '+chunks(xs[n:],start+n)+')'
source='''(ns embench.crc32-full (:export [bench prefix-crc prefix-seed table-entry]))
;; Complete original 1024-byte CRC body; verification once after repetition.
;; Copyright 2013-2019 Embecosm/Bristol; SPDX-License-Identifier: GPL-3.0-or-later.
(defn- table-at [i :i64] :i64 '''+(scalar(table) if a.representation=='scalar' else chunks(table))+''')
(defn- next-seed [seed :i64] :i64 (bit-and (+ (* seed 1103515245) 12345) 2147483647))
(defn- checksum [stop :i64] :i64
 (loop [i 0 seed 0 crc 4294967295]
  (if (= i stop) (bit-and (bit-not crc) 4294967295)
   (let [next (next-seed seed) octet (u64-shift-right next 16)
         index (bit-and (bit-xor crc octet) 255) updated (bit-xor (table-at index) (u64-shift-right crc 8))]
    (recur (+ i 1) next updated)))))
(defn- bodies [n :i64] :i64
 (loop [i 0 last 0] (if (= i n) last (recur (+ i 1) (checksum 1024)))))
(defn bench [n :i64] :i64 (if (= n 0) 0 (if (= (bit-and (bodies n) 32767) 11433) 1 0)))
(defn prefix-crc [stop :i64] :i64 (checksum stop))
(defn prefix-seed [stop :i64] :i64
 (loop [i 0 seed 0] (if (= i stop) seed (recur (+ i 1) (next-seed seed)))))
(defn table-entry [i :i64] :i64 (table-at i))
'''
a.directory.mkdir(parents=True,exist_ok=True);(a.directory/'crc32-full.kotoba').write_text(source)
# Copied original CRC function with only the diagnostic loop bound changed.
start=s.index('crc32pseudo ()');end=s.index('\nvoid\ninitialise_benchmark',start);body=s[start:end];needle='i < 1024';
if body.count(needle)!=1:raise SystemExit('unreviewed diagnostic boundary')
body=body.replace('crc32pseudo ()','crc_prefix (int stop)').replace(needle,'i < stop',1)
c='''/* BOOTSTRAP-TOOL: unchanged C body/verifier; untimed prefix copy. */
#define GLOBAL_SCALE_FACTOR 1
#include <stdint.h>
#include "../upstream/support/beebsc.c"
#include "../upstream/src/crc32/crc_32.c"
#define EXTRA int64_t x1,int64_t x2,int64_t x3,int64_t x4,int64_t x5,int64_t x6,int64_t ctx
'''+ 'static DWORD\n'+body+'''
int64_t bench(int64_t n,EXTRA){if(n==0)return 0;return verify_benchmark(benchmark_body(1,n));}
int64_t prefix_crc(int64_t n,EXTRA){srand_beebs(0);return crc_prefix(n)&0xffffffffUL;}
int64_t prefix_seed(int64_t n,EXTRA){srand_beebs(0);crc_prefix(n);return seed;}
int64_t table_entry(int64_t i,EXTRA){return crc_32_tab[i];}
int64_t oracle_selfcheck(int64_t n,EXTRA){if(n<1||n>32)return 0;srand_beebs(0);DWORD r=crc_prefix(1024);unsigned long expected_seed=seed;int result=benchmark_body(1,n);return result==(int)(r%32768)&&verify_benchmark(result)&&seed==expected_seed;}
'''
(a.directory/'c-bridge.c').write_text(c);(a.directory/'profile.json').write_text(json.dumps({'format':'amu.crc32-full-profile/v1','sourcePins':pins,'representation':a.representation,'bytesPerBody':1024,'tableEntries':256,'iterations':[0,1,2,17,32],'diagnosticPrefixes':list(range(1025)),'verification':'once after all bodies','rngReset':'zero at each body','normalization':'C unsigned-long complement to low 32 bits for prefix observations'},indent=2)+'\n')
