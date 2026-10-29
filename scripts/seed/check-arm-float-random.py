#!/usr/bin/env python3
"""Compare ARM floats against fixed-seed host numeric expectations."""
import argparse,hashlib,json,math,platform,random,struct,subprocess
from pathlib import Path
parser=argparse.ArgumentParser(description='Synthetic fixed-seed comparison diagnostic, not compiler qualification')
parser.add_argument('--compiler',type=Path,required=True);parser.add_argument('--compiler-sha256',required=True)
parser.add_argument('--negative-compiler',type=Path,required=True);parser.add_argument('--negative-compiler-sha256',required=True)
parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
if platform.system()!='Linux' or platform.machine() not in ('aarch64','arm64'):raise SystemExit('native Linux AArch64 host required')
cc=args.compiler.resolve(strict=True);negative=args.negative_compiler.resolve(strict=True)
for f,h in ((cc,args.compiler_sha256),(negative,args.negative_compiler_sha256)):
 if hashlib.sha256(f.read_bytes()).hexdigest()!=h:raise SystemExit('compiler pin mismatch')
if args.compiler_sha256==args.negative_compiler_sha256:raise SystemExit('negative control must differ')
p=args.output.absolute();p.mkdir(parents=True,exist_ok=False,mode=0o700)
env={'PATH':'/nonexistent','KEXE_ALLOW':'35,37,38,39','KEXE_CAP_RESOURCES_35':str(p),'KEXE_STACK_BYTES':'8388608'}
rng=random.Random(16120261029);checks=[];pairs_count=0
for n in (32,64):
 sign=1<<(n-1); inf=(0xff<<23) if n==32 else (0x7ff<<52);quiet=inf|(1<<(22 if n==32 else 51)); snan=inf|1
 pairs=[(0,sign),(1,0),(sign|1,0),(inf,inf|sign),(quiet,1),(1,quiet),(snan,0),(0,snan)]+[(rng.getrandbits(n),rng.getrandbits(n)) for _ in range(64)]
 def signed(x):return x-(1<<n) if x&sign else x
 def value(x):return struct.unpack('>f' if n==32 else '>d',x.to_bytes(n//8,'big'))[0]
 for a,b in pairs:
  pairs_count+=1;x,y=value(a),value(b)
  expected={'eq':x==y,'lt':x<y,'le':x<=y,'gt':x>y,'ge':x>=y,'unordered':math.isnan(x) or math.isnan(y)}
  for op,expect in expected.items():
   call=f'(f{n}-{op} (f{n}-from-bits {signed(a)}) (f{n}-from-bits {signed(b)}))'
   checks.append(call if expect else f'(not {call})')
chunks=[checks[i:i+36] for i in range(0,len(checks),36)]
functions=['(defn- c%d [] :bool (and %s))'%(i,' '.join(c)) for i,c in enumerate(chunks)]
main='42'
for i in range(len(chunks)-1,-1,-1):main='(if (c%d) %s %d)'%(i,main,100+i)
source='(ns native.arm-float-random (:export [main]))\n'+'\n'.join(functions)+'\n(defn main [] :i64 '+main+')\n';src=p/'cases.kotoba';src.write_text(source); rows=[]
for name,compiler in [('candidate',cc),('negative',negative)]:
 out=p/(name+'-cases.elf');out.unlink(missing_ok=True)
 r=subprocess.run([str(compiler),'compile',str(src),'--target','aarch64-linux','--output',str(out),'--format','static'],env=env,capture_output=True,timeout=300);(p/(name+'.stdout')).write_bytes(r.stdout);(p/(name+'.stderr')).write_bytes(r.stderr)
 row={'name':name,'compileExit':r.returncode,'elfExists':out.exists()}
 if name=='candidate':
  assert r.returncode==0 and out.exists(),(row,r.stderr);out.chmod(0o700);g=subprocess.run([str(out)],env={'KEXE_ALLOW':'-','KEXE_FUEL':'1000000','KEXE_STRUCTURED_REPORT':'1'},capture_output=True,timeout=120);(p/'guest.stdout').write_bytes(g.stdout);(p/'guest.stderr').write_bytes(g.stderr);row.update(guestExit=g.returncode,guestStdout=g.stdout.decode());assert g.returncode==0 and b':result 42 ' in g.stdout,row
 else:assert r.returncode!=0 and b'E7101' in r.stderr and not out.exists(),(row,r.stderr)
 rows.append(row);print(json.dumps(row),flush=True)
receipt={'status':'PASS_LIMITED_RANDOM_COMPARISONS','seed':16120261029,'pairs':pairs_count,'checks':len(checks),'sourceSHA256':hashlib.sha256(src.read_bytes()).hexdigest(),'compilerSHA256':hashlib.sha256(cc.read_bytes()).hexdigest(),'rows':rows};(p/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
