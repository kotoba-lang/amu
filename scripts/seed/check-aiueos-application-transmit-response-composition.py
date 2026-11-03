#!/usr/bin/env python3
"""Stage the pinned real Kekkai response corpus on the explicit transmit profile.

Only the fixture's builder allocation/lifetime and post-response transmit
overwrite change. All native library bodies, capacity and observer checks
are retained. This is not a product app/backend or a consent mechanism.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PROOF_SHA='229e71f56531d646353c79df0fb3bddf9dff9c1a61d91eb798ec96e205702fa8'
GATE_SHA='58801d5361f7aef5658382bbcb1c7251de1e955c4f27bd4f83d71c905571edb0'
def pin(p):
    b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main(a):
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    k=a.fixture_source.resolve(strict=True);build=a.mac_build.resolve(strict=True)
    proof=k/'lib/kotoba.kekkai/docs/evidence/native-application-response-20261103/receipt.json'
    assert pin(proof)['sha256']==PROOF_SHA
    p=json.loads(proof.read_text());source=k/'lib/kotoba.kekkai/tools/application_response_link_gate.kotoba'
    assert pin(source)['sha256']==GATE_SHA
    for rel,v in p['productionSources'].items():assert pin(k/rel)==v
    original_observer=k/'scripts/check-kekkai-application-response-os.py'
    assert pin(original_observer)==p['observerVersions']['observer-current']['original']
    receipt=build/'mac-aiueos-user-target.json';b=json.loads(receipt.read_text())
    assert b['status']=='PASS_MAC_NATIVE_USER_TARGET_SELFHOST' and b['generations'][-1]['container']==b['generations'][-2]['container']
    for row in b['sources']:assert pin(ROOT/row['name'])=={f:row[f] for f in ['bytes','sha256']}
    compiler=build/f"F{b['generations'][-1]['number']}-signed.macho";assert pin(compiler)==b['generations'][-1]['signed']
    s=source.read_text();start=s.index('(defn builder-byte');end=s.index('(defn bootstrap-local-request')
    s=s[:start]+s[start:end].replace('(kernel-application-pool) 8388608','(kernel-application-transmit-pool) 1048576')+s[end:]
    s=replace(s,'''      (check (= (bridge/detach-empty (kernel-application-pool) 8388608 (kernel-value-domain-request-page 73) 262144
                  (kernel-value-domain-request-page 74) 262144 (clock)) 1))
''','')
    s=replace(s,'''      (check (= (bridge/initialize (kernel-application-pool) 8388608 (kernel-value-domain-request-page 73) 262144
                  (kernel-value-domain-request-page 74) 262144 (clock)) 1))
      (check (= (bridge/synchronize (kernel-application-pool) 8388608 (kernel-value-domain-request-page 73) 262144
                  (kernel-value-domain-request-page 74) 262144 (clock)) 2))
''','      (clear-io 225280 237568)\n')
    s=replace(s,'(kernel-subregion (kernel-application-pool) 8388608 i 8)','(kernel-subregion (kernel-application-transmit-pool) 1048576 i 8)')
    s=replace(s,'(kernel-subregion (kernel-application-pool) 8388608 0 1048576) 1048576 used','(kernel-subregion (kernel-application-transmit-pool) 1048576 0 1048576) 1048576 used')
    s=replace(s,'(accepted-context)','(accepted-context) (exercise-transmit-owner) (accepted-context)')
    s+='''
;; Overwrite all transmit bytes while the real1MiB authenticated input is held.
(defn exercise-transmit-owner [] :i64
  (do (loop [i 0] (if (>= i 1048576) 1
        (let [w (kernel-store-u32 (kernel-subregion (kernel-application-transmit-pool) 1048576 i 4) 4 0
                                 (bit-xor i 0x728fa35c))] (recur (+ i 4)))))
      (loop [i 0] (if (>= i 1048576) 1
        (let [v (kernel-load-u32 (kernel-subregion (kernel-application-transmit-pool) 1048576 i 4) 4 0)
              z (check (= v (bit-xor i 0x728fa35c)))] (recur (+ i 4)))))
      (check (= (assembly/completed-size (kernel-application-pool) 8388608) 1048576))))
'''
    gate=out/'application_response_link_gate.kotoba';gate.write_text(s)
    s=original_observer.read_text()
    s=replace(s,'ROOT = Path(__file__).resolve().parents[1]','ROOT = Path('+repr(str(k))+')')
    s=replace(s,"'pool-v4-main-2f842': 'efec34486903fc189eb9e3a6d45e02edeaa7f7edf73a9e3e12586c8de048b225'","'pool-v5-transmit': '"+pin(compiler)['sha256']+"'")
    s=replace(s,'bytes=3826784','bytes='+str(pin(compiler)['bytes']))
    s=replace(s,"flags[3] = 'x86_64-aiueos-kernel-v4'","flags[3] = 'x86_64-aiueos-kernel-v5'")
    s=replace(s,"shutil.copyfile(ROOT/'lib/kotoba.kekkai/tools/application_response_link_gate.kotoba',new_gate)",'shutil.copyfile(Path('+repr(str(gate))+'),new_gate)')
    s=replace(s,"schema='kekkai.native-application-response.v1'","schema='amu.native-application-transmit-response-composition.v1'")
    s=replace(s,"report['receiveResult'] = result",'''report['receiveResult'] = result
            private=q.dump(0x400000,65536,directory,'private-final.bin')
            app,total,ready=struct.unpack_from('<3Q',private,33536)
            assert total==9437184 and ready==0x324d5041
            tx=q.dump(app+8388608,1048576,directory,'transmit-final.bin')
            expected_tx=b''.join(struct.pack('<I',i^0x728fa35c) for i in range(0,1048576,4))
            assert tx==expected_tx
            leaves=[]
            registers=q.hmp('info registers'); assert 'CR3=0000000000530000' in registers
            for leaf in range(app//2097152,(app+total-1)//2097152+1):
                value=struct.unpack('<Q',q.dump(0x532000+leaf*8,8,directory,'leaf-final.bin'))[0]
                assert value&(1<<63) and not(value&4) and value&0x83==0x83
                leaves.append(dict(index=leaf,pde=value))
            report['transmitComposition']=dict(bytes=1048576,wholeTransmitSHA256=digest(tx),receiveBytes=8388608,totalBytes=total,overwroteWhileAccepted=True,supervisorNXLeaves=leaves,userCodeExecuted=False)''')
    observer=out/'observer.py';observer.write_text(s)
    (out/'adapter.json').write_text(json.dumps(dict(schema='amu.transmit-response-fixture-adapter.v1',producer=pin(compiler),producerReceipt=pin(receipt),originalProof=pin(proof),originalGate=pin(source),originalObserver=pin(original_observer),gate=pin(gate),observer=pin(observer),stager=pin(Path(__file__)),role=a.role,changes=['explicit transmit root for local builder/input; no empty-receive-pool detach/reinitialization','outbound caller clears its codec scratch explicitly; receiver checks remain','overwrite and verify all transmit1MiB while actual authenticated response1MiB is accepted; exact old full-response/context checks retained','after full corpus independently read transmit bytes and supervisor/NX leaf permissions'],appInstalled=False,serviceExecution=False,trustedConsent=False,hostileUserExecution=False),indent=2)+'\n')
    argv=[sys.executable,str(observer),'--compiler',str(compiler),'--compiler-profile','pool-v5-transmit','--role',a.role,'--amu-source',str(ROOT),'--baseline',str(a.baseline.resolve(strict=True)),'--qemu',str(a.qemu.resolve(strict=True)),'--qemu-sha256',a.qemu_sha256,'--firmware',str(a.firmware.resolve(strict=True)),'--firmware-sha256',a.firmware_sha256,'--output',str(out/'run')]
    result=subprocess.run(argv,cwd=ROOT);raise SystemExit(result.returncode)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['fixture-source','mac-build','baseline','qemu','firmware','output']:p.add_argument('--'+key,type=Path,required=True)
    for key in ['qemu-sha256','firmware-sha256']:p.add_argument('--'+key,required=True)
    p.add_argument('--role',choices=['responder','initiator'],required=True);main(p.parse_args())
