# NOTE (JUN-974): retained only because check-aiueos-kernel-tier-maximum.py loads its SOURCE;
# the maintained version is check-aiueos-owned-page-native.cljc. Delete with that importer.
#!/usr/bin/env python3
"""Observe the bounded slot constructor and immutable pre-main metadata seal."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True

SOURCE='''(ns entry (:export [main]))
(defn main [] :i64
 (let [header (kernel-subregion (kernel-boot-info) 16544 0 160)
       original (kernel-load-u64 header 160 80)
       changed (kernel-store-u64 header 160 80 0)
       first (kernel-owned-page 0) last (kernel-owned-page 14)
       saved (kernel-load-u64-4k first 4096 0)
       stored (kernel-store-u8-4k first 4096 0 42)
       readback (kernel-load-u8-4k first 4096 0)
       restored (kernel-store-u64-4k first 4096 0 saved)
       metadata (kernel-store-u64 header 160 80 original)]
  (if (and (> original 0) (= first original) (= (- last first) 57344)
           (= (bit-and first 4095) 0) (= changed 0) (= stored 42)
           (= readback 42) (= restored saved) (= metadata original)) 42 0)))
'''
