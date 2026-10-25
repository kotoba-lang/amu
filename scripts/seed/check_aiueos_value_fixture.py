"""Reuse the typed role fixture without importing a hyphenated script name."""
import runpy
from pathlib import Path

def user_source():
 source=runpy.run_path(str(Path(__file__).with_name('check-aiueos-value-call-native.py')))['SOURCE']
 start=source.index('(defn main ')
 return source[:start]+'''(defn main [] :i64
  (let [registered (kernel-register-value-domain 73)
        published (kernel-publish-current-domain 73)
        code (kernel-value-domain-code-page 73)
        stack (kernel-value-domain-stack-page 73)
        a (kernel-store-u8-4k code 4096 0 144)
        b (kernel-store-u8-4k stack 4096 0 0)
        enabled (kernel-value-enable-user)]
    (+ 42 enabled)))
'''
