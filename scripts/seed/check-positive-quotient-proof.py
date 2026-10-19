#!/usr/bin/env python3
"""Native compiler-local positive interval, entry and scratch refusal controls."""
import argparse,hashlib,importlib.util,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selfbuild-output',type=Path,required=True);a=ap.parse_args()
 out=a.selfbuild_output.resolve();host=out/'host';D=out/'artifacts/positive-quotient-proof-controls';D.mkdir(exist_ok=False)
 spec=importlib.util.spec_from_file_location('adopted_inputs',ROOT/'scripts/seed/build-adopted.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 receipt,unity,_,_=m.inputs(ROOT/'seed/adoption-20261017.json')
 loader=host/'kexe-loader';producer=host/'positive-quotient-proof-producer.bin';shutil.copy2(out/'artifacts/G2.bin',producer)
 assert sha(producer)==receipt['nativeImageSHA256']
 paths=[p.strip()for p in(ROOT/'seed/MANIFEST').read_text().splitlines()if p.strip()and not p.startswith('#')]
 fixture=ROOT/'seed/tests/unit/positive_quotient_t.kotoba';source=D/'controls.kotoba'
 # Internal generator controls omit the separately qualified CLI driver.
 source.write_bytes(b''.join((ROOT/p).read_bytes()+b'\n'for p in paths if p not in {'seed/90-drv.kotoba','seed/99-entry.kotoba'})+fixture.read_bytes()+b'\n')
 pins={p:sha(p)for p in[loader,producer,source,fixture]};env={k:v for k,v in os.environ.items()if not k.startswith('KEXE_')}
 env.update(KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(D),KEXE_FUEL='off',KEXE_VECTORS='4194304',KEXE_VECTOR_ITEMS='134217728',KEXE_STRING_POOL='268435456',KEXE_PAIRS='16777216',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',TMPDIR=str(D))
 calls=[]
 def call(name,p,args):
  z=subprocess.run(list(map(str,[loader,p,'0','0','aarch64','35,37,38,39','--',*args])),cwd=D,env=env,capture_output=True,timeout=1800)
  (host/(name+'.stdout')).write_bytes(z.stdout);(host/(name+'.stderr')).write_bytes(z.stderr);calls.append(dict(name=name,exit=z.returncode))
  (host/'positive-quotient-proof-calls.json').write_text(json.dumps(calls,indent=2)+'\n');assert z.returncode==0 and not z.stderr and all(sha(p)==h for p,h in pins.items()),name
  return z.stdout
 call('positive-proof-compile',producer,['compile',source,'--target','aarch64-macos','--output',D/'controls.kseed'])
 call('positive-proof-extract',producer,['extract-native',D/'controls.kseed','--symbol','main','--output',D/'controls.bin'])
 h,payload=(D/'controls.kseed').read_bytes().split(b'\n\n',1);assert payload==(D/'controls.bin').read_bytes()and h.decode().splitlines()[1:]==['main 0 0']
 result=call('positive-proof-execute',D/'controls.bin',[])
 assert result==b'PASS_NATIVE_POSITIVE_QUOTIENT_RANGE_ROOT_SCRATCH_REFUSALS\n'
 r=dict(status='PASS_NATIVE_POSITIVE_QUOTIENT_RANGE_ROOT_SCRATCH_REFUSALS',compilerCalls=2,controlInvocations=1,positiveAdmission=True,wordRefusals=6,incomingRootRefusals=5,rangeWorkBudgetRefusal=True,signed64OverflowRefusal=True,compilerImageSHA256=sha(producer),fixtureSHA256=sha(fixture),performanceMeasured=False)
 (host/'positive-quotient-proof-controls-report.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
if __name__=='__main__':main()
