"""Stdlib data-only portable replay. Never extracts/runs archived code or solver."""
from pathlib import Path,PurePosixPath
import json,hashlib,tarfile,sys,re
D=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def form(text,name):
 start=text.index('(defn- '+name+' ');depth=0;quote=False;escape=False;comment=False
 for i in range(start,len(text)):
  c=text[i]
  if comment:
   if c=='\n':comment=False
   continue
  if quote:
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='"':quote=False
   continue
  if c==';':comment=True
  elif c=='"':quote=True
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if depth==0:return text[start:i+1]
 raise AssertionError('unterminated source form '+name)
def main():
 manifest=json.loads((D/'entry-manifest.json').read_text());assert manifest['readerSHA256']==sha(Path(__file__).read_bytes())
 archive=D/'failure-proof.tgz';raw=archive.read_bytes();assert len(raw)==manifest['archiveBytes'] and sha(raw)==manifest['archiveSHA256']
 assert len(manifest['entries'])<=192 and sum(x['bytes'] for x in manifest['entries'])<=67108864
 assert manifest['conclusion']['qualificationPASS'] is False and manifest['conclusion']['branchDirectlyObserved'] is False
 expected={e['member']:e for e in manifest['entries']};assert len(expected)==len(manifest['entries']);data={}
 with tarfile.open(archive,'r:gz') as tf:
  members=tf.getmembers();assert len(members)==len(expected)
  for m in members:
   p=PurePosixPath(m.name);assert not p.is_absolute() and '..' not in p.parts and m.isfile() and m.name in expected and m.name not in data
   e=expected[m.name];assert m.size==e['bytes'];b=tf.extractfile(m).read();assert len(b)==e['bytes'] and sha(b)==e['sha256'];data[m.name]=b
 origins={e['origin']:e['member'] for e in manifest['entries']};assert len(origins)==len(expected)
 def byorigin(path):return data[origins[path]]
 def role(name):return data[manifest['roles'][name]]
 def obj(name):return json.loads(role(name))
 def check_inputs(name,count):
  pins=obj(name)['inputs'];assert len(pins)==count
  for path,p in pins.items():b=byorigin(path);assert len(b)==p['bytes'] and sha(b)==p['sha256']
 check_inputs('runtimePrereg',31);check_inputs('observationPrereg',15);check_inputs('fixturePrereg',8)
 builds=obj('buildAttempts');assert len(builds)==4 and all(x['state']=='terminal' and x['returncode']==0 for x in builds)
 for label in ['RF','inverse']:
  compiled=obj(label+'ExtractStatus');assert compiled['returncode']==0
  offset=int(role(label+'Offset').strip());assert 0<=offset<len(role(label+'Image')) and offset%4==0
  match=re.search(rb':offset (\d+)',role(label+'ExtractStdout'));assert match and int(match[1])==offset
 attempts=obj('qualificationAttempts');assert len(attempts)==1
 a=attempts[0];assert a['profile']=='RF-core-probe' and a['case']==0 and a['expectedReturn']==0 and a['returncode']==69 and a['PASS'] is False and a['actualReturn'] is None
 assert role('qualificationStdout')==b'' and role('qualificationStderr')==b''
 report=obj('qualificationReport');assert report['guestCalls']==1 and report['returncode']==69 and report['value'] is None and report['status'].startswith('FAIL')
 env=obj('qualificationEnvironment');assert env['KEXE_COMMAND']=='0'
 started=obj('observationStarted');assert started['argv']==a['argv'] and started['KEXE_COMMAND']=='ABSENT' and started['callCap']==1
 value=int(role('observationStdout').strip());observed=obj('observationReport');assert value==12101 and value&255==69
 assert observed['value']==value and observed['low8']==69 and observed['originalCommandExit']==69 and observed['exit']==0 and observed['qualificationPASS'] is False and observed['nativeCalls']==1 and observed['retry'] is False
 assert role('observationStderr')==b''
 auth=obj('observationAuthorization');assert auth['allowFailureObservation'] is True and auth['nativeCallCap']==1 and auth['allowQualificationRetry'] is False
 assert auth['preregistrationSHA256']==sha(role('observationPrereg')) and auth['runnerSHA256']==sha(role('observationRunner'))
 source=role('RFSource').decode();inverse=role('inverseSource').decode();original=role('originalAES').decode()
 for text in [source,inverse]:
  literal_at=text.index('(def cm-source ')+len('(def cm-source ');embedded=json.JSONDecoder().raw_decode(text[literal_at:])[0];assert embedded==original
  lowered=form(text,'cm-lowered');assert '(ck-run ' in lowered and 'ck-run-h' not in lowered and 'ck-hint-again?' not in lowered
 driver=form(role('RFUnity').decode(),'drv-c3h');assert '(ck-run-h M S H)' in driver and '(ck-hint-again? H M1)' in driver and '(drv-reread M1 S)' in driver
 loader=role('loaderSource').decode();assert 'getenv("KEXE_COMMAND") != NULL' in loader and '_exit(command_mode ? (int)((uint64_t)result & 0xffu) : 0);' in loader
 runner=role('observationRunner').decode();assert "'KEXE_COMMAND'" in runner and 'env.pop(k,None)' in runner
 independent=obj('independentFailure');assert sha(role('independentFailure'))=='cb070777aa2904337266118f2109093fc836fa73707c24c208f5a509f5775c8a'
 latest=obj('scopeCorrection');assert latest['qualificationPASS'] is False and latest['fullValue']==value and latest['inverseGuestCalls']==0 and latest['remainingGuestCalls']==0 and latest['performanceGO'] is False
 assert latest['inferredCandidateOrigin']['branchDirectlyObserved'] is False
 # Source interface omission is definite; error branch/2101 origin is inference
 # only. Do not reinterpret original raw failure as a qualified compiler-M test.
 result={'status':'PASS offline retained failure evidence replay','selectedMembers':len(data),'runtimeInputPinsChecked':31,'compilerBuildProcesses':4,'qualificationGuestCalls':1,'qualificationResult':'FAIL','separateObservationGuestCalls':1,'observedFullReturn':value,'observedLow8':value&255,'inverseGuestCalls':0,'remainingGuestCalls':0,'qualificationPASS':False,'branchDirectlyObserved':False,'compilerMOrPerformanceClaim':False,'nativeReplayCalls':0,'solverReplayCalls':0,'sourcePipelineOmissionBound':True}
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
