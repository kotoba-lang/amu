from pathlib import Path
import subprocess,os,json,hashlib
D=Path(__file__).resolve().parent;W=D.parent;U=W/'root-proof/gate-build/unit/41-a64gen';R=Path('/Users/junkawasaki/github/wt/amu-seed17');L=W/'implementation/kexe-loader';rows=[]
for cap in [16777216,134217728]:
 e=dict(os.environ,KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(R),KEXE_STRING_POOL='268435456',KEXE_PAIRS='4194304',KEXE_VECTORS='65536',KEXE_VECTOR_ITEMS=str(cap),KEXE_CPU_SECONDS='120',KEXE_WALL_SECONDS='120');q=subprocess.run([str(L),str(U/'unit.bin'),(U/'unit.offset').read_text().strip(),'0','aarch64','35,37,38,39','--',str(R),str(U/'scratch')],env=e,capture_output=True)
 (D/(str(cap)+'.stdout')).write_bytes(q.stdout);(D/(str(cap)+'.stderr')).write_bytes(q.stderr);expect=(R/'seed/tests/unit/41-a64gen.expected').read_bytes();final=q.stdout+b'exit='+str(q.returncode).encode()+b'\n';rows.append({'capacity':cap,'exit':q.returncode,'stdoutLines':len(q.stdout.splitlines()),'goldenMatch':final==expect,'stdoutSha256':hashlib.sha256(q.stdout).hexdigest(),'stderr':q.stderr.decode()});print(rows[-1],flush=True)
(D/'capacity.json').write_text(json.dumps({'unitNativeSha256':hashlib.sha256((U/'unit.bin').read_bytes()).hexdigest(),'rows':rows},indent=2)+'\n')
