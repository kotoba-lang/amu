from pathlib import Path
import json,hashlib,subprocess,os,re
D=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
g=json.loads((D/'preregistration.json').read_text());assert g['maximumLoaderCalls']==2
for n,h in g['inputs'].items():assert sha(D/n)==h
for p,h in g['reviews'].items():assert sha(Path(p))==h
assert not(D/'attempts.json').exists(),'No reruns'
rows=[]
def save(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
def call(label,args):
 assert len(rows)<2
 cmd=[str(D/'kexe-loader'),str(D/'producer.bin'),'0','0','aarch64','35,37,38,39','--',*args]
 env=dict(os.environ,KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(D),KEXE_STRING_POOL='268435456',KEXE_VECTORS='4194304',KEXE_PAIRS='16777216',KEXE_VECTOR_ITEMS='134217728',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800')
 r={'index':len(rows)+1,'label':label,'argv':cmd,'state':'started','caps':g['caps']};rows.append(r);save('attempts.json',rows)
 try:q=subprocess.run(cmd,env=env,capture_output=True,timeout=1810);out,err,rc=q.stdout,q.stderr,q.returncode
 except subprocess.TimeoutExpired as e:out,err,rc=e.stdout or b'',e.stderr or b'',None
 (D/(label+'.stdout')).write_bytes(out);(D/(label+'.stderr')).write_bytes(err);r.update(state='terminal',returncode=rc);save('attempts.json',rows)
 assert rc==0 and not err and b':ok true'in out,(label,rc,out[-1000:],err[-1000:]);return out
try:
 call('compile',['compile',str(D/'unity.kotoba'),'--target','aarch64-macos','--output',str(D/'candidate.kseed')])
 out=call('extract',['extract-native',str(D/'candidate.kseed'),'--symbol','main','--output',str(D/'candidate.bin')]);offset=int(re.search(rb':offset (\d+)',out)[1]);(D/'candidate.offset').write_text(str(offset)+'\n')
 b=(D/'candidate.bin').read_bytes();head,payload=(D/'candidate.kseed').read_bytes().split(b'\n\n',1);assert payload==b
 save('report.json',{'status':'PASS_TWO_CALL_NATIVE_BUILD_ONLY','loaderCalls':2,'bytes':len(b),'sha256':sha(D/'candidate.bin'),'offset':offset,'fullKSEEDPayloadEqualsNative':True,'sourceSHA256':sha(D/'unity.kotoba'),'functionalCases':0,'benchmarkBodies':0,'timing':False,'actualEmittedBoundsOmissions':'NOT_YET_VALIDATED','selfbuildGenerations':0,'ComputeCID':'NOT_IMPLEMENTED','ResultCID':'NOT_IMPLEMENTED','productAdopted':False})
except BaseException as e:save('failure.json',{'exception':repr(e),'loaderCalls':len(rows)});raise
finally:save('terminal.json',{'allCallsClosed':all(r['state']=='terminal'for r in rows),'loaderCalls':len(rows),'failure':(D/'failure.json').exists()})
