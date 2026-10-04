#!/usr/bin/env python3
# BOOTSTRAP-TOOL: pinned input extraction; the codec implementation is Kotoba.
import argparse,pathlib,hashlib,re
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('output',type=pathlib.Path)
p.add_argument('--initialization',choices=['reuse','fresh'],default='reuse');a=p.parse_args()
source=a.upstream.read_bytes()
if hashlib.sha256(source).hexdigest()!='db93b8ea3c68b178348834e738ba0628c8dbf28c338d4320aebab145683d8162':raise SystemExit('unreviewed Huffbench profile')
body=re.search(r'orig_data\[TEST_SIZE\]\s*=\s*\{(.*?)\}',source.decode(),re.S).group(1)
values=[ord(v) for v in re.findall(r"'(.)'",body)];assert len(values)==500
head='(ns embench.huffbench-full (:export [batch state-cell test-huffbench]))\n'
head+='(def RESET-LIMIT '+('500' if a.initialization=='fresh' else '3309')+')\n'
for i in range(4):head+='(def original-'+str(i)+' ['+' '.join(map(str,values[i*128:(i+1)*128]))+'])\n'
head+='''(defn- original-at [i :i64] :i64
  (if (< i 128) (vector-at original-0 i)
    (if (< i 256) (vector-at original-1 (- i 128))
      (if (< i 384) (vector-at original-2 (- i 256)) (vector-at original-3 (- i 384))))))
'''
state='(vector-alloc 3309)' if a.initialization=='fresh' else 's'
repeat='(defn- repeats [s :vector-i64 remaining :i64] :vector-i64\n  (if (= remaining 0) s (repeats (body '+state+') (- remaining 1))))'
template=pathlib.Path(__file__).with_name('huffbench-full-body.kotoba').read_text()
assert template.count(';; @REPEATS@')==1
a.output.write_text(head+template.replace(';; @REPEATS@',repeat))
