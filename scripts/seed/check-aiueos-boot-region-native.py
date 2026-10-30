#!/usr/bin/env python3
"""Observe the fixed loader-owned boot region, never arbitrary physical roots."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from aiueos_native_proof import load_native_producers


def pin(p):
    raw = p.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main(build, out, complete=None):
    graph, producers, _ = load_native_producers(build=build, complete=complete)
    out.mkdir(parents=True, exist_ok=False)
    results = []
    boot = '(ns entry (:export [main]))\n(defn main [] :i64 (let [h (kernel-subregion (kernel-boot-info) 16544 0 160)] (if (= (kernel-load-u8 h 160 0) 65) 42 0)))\n'
    rows = []
    for tier in ['', '-4k', '-16k', '-64k']:
        for width, want in [(8, 239), (16, 52719), (32, 2309737967), (64, 81985529216486895)]:
            rows.append((f'kernel-store-u{width}{tier}', f'kernel-load-u{width}{tier}', want))
    bindings = ['r (kernel-subregion (kernel-boot-info) 16544 152 8)', 'saved (kernel-load-u64 r 8 0)']
    conditions = []
    for i, (store, load, want) in enumerate(rows):
        bindings.extend([f's{i} ({store} r 8 0 81985529216486895)', f'v{i} ({load} r 8 0)'])
        conditions.extend([f'(= s{i} 81985529216486895)', f'(= v{i} {want})'])
    bindings.append('restored (kernel-store-u64 r 8 0 saved)')
    widths = '(ns entry (:export [main]))\n(defn main [] :i64 (let ['+'\n'.join(bindings)+'] (if (and '+' '.join(conditions)+' (= restored saved)) 42 0)))\n'
    for producer in producers:
        scope = out / producer.stem
        scope.mkdir()
        src, lock = scope/'entry.kotoba', scope/'source.ksl'
        calls, artifacts = [], {}
        def compile_(name, text, ok=True, refusal=b'E7106'):
            src.write_text(text)
            lock.write_text(f'KSL1\nentry {src}\nroot {scope}\nfile {pin(src)["sha256"]} {src}\n')
            image = scope/(name+'.elf')
            args = [str(producer), 'compile', str(src), '--target','x86_64-aiueos-kernel-v1','--artifact','image','--output',str(image),'--fuel','1000000','--source-path',str(scope),'--source-lock',str(lock),'--source-lock-sha256',pin(lock)['sha256']]
            env = dict(PATH='/nonexistent',KEXE_CAP_RESOURCES_35=str(scope),KEXE_STACK_BYTES='8388608')
            r = subprocess.run(args,env=env,capture_output=True,timeout=240)
            calls.append(dict(name=name,exit=r.returncode,stderr=r.stderr.decode(),source=pin(src),sourceText=text))
            (scope/'calls.json').write_text(json.dumps(calls,indent=2)+'\n')
            if ok:
                assert r.returncode==0 and not r.stderr and image.is_file(),calls[-1]
                efi=scope/(name+'.efi')
                p=subprocess.run([str(producer),'package-aiueos-boot',str(image),'--output',str(efi)],env=env,capture_output=True,timeout=180)
                assert p.returncode==0 and not p.stderr,p.stderr
                artifacts[name]=dict(kernel=pin(image),efi=pin(efi))
            else:
                assert r.returncode==1 and refusal in r.stderr and not image.exists(),calls[-1]
        compile_('boot-region',boot)
        compile_('widths',widths)
        # JUN-483: a plain-tier access over the 16544-byte boot block can only reach its ud2 at run time; it is
        # now refused at compile time, naming the intrinsic, the size and the tier maximum
        compile_('oversized-tier', '(ns entry (:export [main]))\n(defn main [] :i64 (kernel-load-u8 (kernel-boot-info) 16544 0))\n',
                 ok=False, refusal=b'E7108 kernel-load-u8 size 16544 is above its tier maximum 512')
        compile_('valid-tier', '(ns entry (:export [main]))\n(defn main [] :i64 (- (kernel-load-u8-64k (kernel-boot-info) 16544 0) 23))\n')
        for name,text in [
            ('wrong-boot-length',boot.replace('16544','16480')),
            ('computed-root',boot.replace('(kernel-boot-info)','(+ (kernel-boot-info) 0)')),
            ('literal-root',boot.replace('(kernel-boot-info)','1089536')),
            ('wrong-sub-length',boot.replace('(kernel-load-u8 h 160 0)','(kernel-load-u8 h 64 0)')),
            ('loaded-root',boot.replace('(kernel-load-u8 h 160 0)','(kernel-load-u8 (kernel-load-u64 h 160 0) 160 0)')),
        ]:
            compile_(name,text,ok=False)
        results.append(dict(producer=pin(producer),artifacts=artifacts,compileRefusals=6))
    assert results[0]['artifacts']==results[1]['artifacts']
    report=dict(status='PASS_NATIVE_BOOT_REGION_PACKAGING',source=graph,results=results,guestExecution=False,fullKernel=False,nativeCDCI=False)
    (out/'native-boot-region.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['status'],'fixed boot ABI, all32 memory ops and 6 refusal controls; guest gates separate')

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--build',type=Path);g.add_argument('--complete',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.build.resolve() if a.build else None, a.output.resolve(), a.complete.resolve() if a.complete else None)
