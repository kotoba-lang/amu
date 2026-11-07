# NOTE (JUN-974): retained only because Python gates still load its SOURCE (check_aiueos_value_fixture.py);
# the maintained, CI-run version is check-aiueos-value-call-native.cljc. Delete with its last Python importer.
#!/usr/bin/env python3
"""Observe typed role/range admission; actual guest call execution is separate."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROLES = [
 ('aiueos-value-runtime-entry','a :i64 p :i64 u :i64 r :i64 c :i64',
  '(+ (kernel-load-u8-4k a 4096 0) (kernel-load-u8-4k u 4096 0) (kernel-load-u8 r 96 0) (kernel-load-u8-4k c 4096 0))'),
 ('aiueos-value-runtime-syscall-plan','n :i64 d :i64 p :i64 i :i64 s :i64','0'),
 ('aiueos-value-runtime-publish-domain','d :i64','0'),
 ('aiueos-value-runtime-provider-status','g :i64 a :i64','0'),
 ('aiueos-value-runtime-capability-grant','a :i64 s :i64 g :i64 r :i64 o :i64','0'),
 ('aiueos-value-runtime-provider-claim','','0'),
 ('aiueos-value-runtime-provider-complete','t :i64 r :i64 b :i64 n :i64 d :i64','(kernel-load-u8-16k b n 0)'),
 ('aiueos-value-runtime-cas-verify','b :i64 n :i64 e :i64 o :i64 w :i64',
  '(+ (kernel-load-u8-16k b n 0) (kernel-load-u8 e 32 0) (kernel-load-u8 o 32 0) (kernel-load-u8 w 352 0))')]
SOURCE = '(ns entry (:export [main '+' '.join(r[0] for r in ROLES)+']))\n'+''.join(
 f'(defn {name} [{args}] :i64 {body})\n' for name,args,body in ROLES)+\
 '(defn main [] :i64 (let [r (kernel-value-runtime-invoke 5 0 0 0 0 0)] (+ 42 r)))\n'
