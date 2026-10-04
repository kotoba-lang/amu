#!/usr/bin/env python3
# BOOTSTRAP-TOOL: extract the pinned C profile; product algorithm is Kotoba.
import argparse,hashlib,re,pathlib
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('output',type=pathlib.Path)
p.add_argument('--short-strategy',choices=['branch','shifts'],default='branch');a=p.parse_args()
source=a.upstream.read_bytes()
if hashlib.sha256(source).hexdigest()!='2604a80fbe70e2b6bc4276649bfb5974d02e18f70b84fc804c7d52bf47f6a20e':raise SystemExit('unreviewed EDN source profile')
def array(name):
 body=re.search(r'\b'+name+r'\[200\]\s*=\s*\{(.*?)\}',source.decode(),re.S).group(1)
 values=[int(s,0) for s in re.findall(r'-?0x[0-9a-fA-F]+|-?\d+',body)]
 assert len(values)==200,(name,len(values))
 return values
def signed(v):return v-65536 if v>32767 else v
tables={'input-a':list(map(signed,array('in_a'))),'input-b':list(map(signed,array('in_b'))),'expected-output':array('exp_output')}
head='(ns embench.edn-full (:export [batch stage-hash stage-cell test-edn]))\n;; Complete Embench 2.0rc2 EDN fixed workload. SPDX-License-Identifier: GPL-3.0-or-later.\n'
for name,values in tables.items():
 # The recorded r6m compiler admits constant vectors of at most 128 items.
 # Keep all 200 items; two checked table reads implement this pinned profile.
 for part,chunk in enumerate((values[:128],values[128:])):
  head+='(def '+name+'-'+str(part)+' ['+' '.join(map(str,chunk))+'])\n'
 head+='(defn- '+name+'-at [i :i64] :i64 (if (< i 128) (vector-at '+name+'-0 i) (vector-at '+name+'-1 (- i 128))))\n'
short=('(defn- short-value [x :i64] :i64\n  (let [v (bit-and x 65535)] (if (> v 32767) (- v 65536) v)))\n'
       if a.short_strategy=='branch' else
       '(defn- short-value [x :i64] :i64\n  (i64-shift-right (i64-shift-left x 48) 48))\n')
a.output.write_text(head+short+pathlib.Path(__file__).with_name('edn-full-body.kotoba').read_text())
