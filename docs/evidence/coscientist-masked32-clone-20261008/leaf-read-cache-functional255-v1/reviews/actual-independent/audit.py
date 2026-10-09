"""Read stored evidence only after root closure. No author modules, native or driver calls."""
import hashlib,json,re,stat,sys
from pathlib import Path
D=Path('/Users/junkawasaki/github/workspaces/codex/vector-leaf-straight-read-cache-functional255-plan-v1-width')
A=Path(__file__).resolve().parent
G=Path('/Users/junkawasaki/github/workspaces/codex/vector-leaf-straight-read-cache-functional255-go-v1-root/root-go.json')
GO_HASH='5f55914074ae687a5eb55ae34fd157652f64fe19e68a00348fb54ef1a3a5671e'
cache={};pins={}; checks=[]
def require(x,m):
 if not x: raise AssertionError(m)
def digest(b):return hashlib.sha256(b).hexdigest()
def read(path):
 p=str(Path(path));
 if p not in cache:
  st=Path(p).lstat();require(stat.S_ISREG(st.st_mode),'regular file '+p)
  cache[p]=Path(p).read_bytes();pins[p]={'bytes':len(cache[p]),'sha256':digest(cache[p])}
 return cache[p]
def unique(items):
 d={}
 for k,v in items:require(k not in d,'duplicate JSON key '+k);d[k]=v
 return d
def obj(path):return json.loads(read(path),object_pairs_hook=unique)
def checkpin(v):
 b=read(v['path']);require(len(b)==v['bytes'] and digest(b)==v['sha256'],'pin '+v['path']);return b
def stage(m):checks.append(m)
def native(b,e,n):
 require(e==b'' and b.endswith(b'\n') and b.count(b'\n')==1,'native one line no stderr')
 text=b.decode('ascii'); toks=re.findall(r'\{|\}|:[a-z-]+|[0-9]+|\S+',text)
 i=0
 def parse():
  nonlocal i
  require(i<len(toks),'native eof');t=toks[i];i+=1
  if t=='{':
   d={}
   while i<len(toks) and toks[i]!='}':
    k=toks[i];i+=1;require(k.startswith(':') and k not in d,'native map key');d[k]=parse()
   require(i<len(toks) and toks[i]=='}','native map close');i+=1;return d
  if t.startswith(':'):return t
  require(t.isdecimal() and int(t)<2**64,'native uint64');return int(t)
 q=parse();require(i==len(toks),'native complete parse')
 require(set(q)=={':status',':result',':fuel',':heap',':string-pool',':vectors',':vector-items'},'native schema')
 require(q[':status']==':ok' and type(q[':result']) is int and q[':result']==(n!=0),'native boolean')
 f=q[':fuel'];require(set(f)=={':initial',':remaining'} and f[':initial']==16777216 and 0<f[':remaining']<=16777216,'native fuel')
 aa={}
 for k,c in [('heap',2097152),('string-pool',65536),('vectors',4096),('vector-items',65536)]:
  x=q[':'+k];require(set(x)=={':capacity',':used'} and x[':capacity']==c and 0<=x[':used']<=c,'native '+k);aa[k]={'capacity':c,'used':x[':used']}
 return {'status':'ok','result':q[':result'],'fuel':{'initial':f[':initial'],'remaining':f[':remaining']},'terminalArenas':aa}
def cresult(b,e,n):
 require(e==b'' and b.endswith(b'\n') and b.count(b'\n')==1,'C one line no stderr');q=json.loads(b,object_pairs_hook=unique)
 ints={'calls','warmupCalls','elapsedNanoseconds','result','maxRssBytes','fuelPerCall','contextFuelBefore','contextFuelAfter','contextFuelConsumed'}
 require(set(q)==ints|{'format','nativeArtifactAbi','artifactKind','nativeArenaStatus','nativeArenas'},'C schema')
 require(all(type(q[k]) is int and 0<=q[k]<2**64 for k in ints),'C uint64')
 require(q['format']=='kotoba.runtime-sample/v1' and q['calls']==1 and q['warmupCalls']==0 and q['result']==(n!=0),'C boolean')
 require(all(q[k]==16777216 for k in ['fuelPerCall','contextFuelBefore','contextFuelAfter']) and q['contextFuelConsumed']==0,'C no fuel debit')
 require(q['nativeArtifactAbi']=='kotoba.native-artifact-i64x8-to-i64-indirect/v1' and q['artifactKind']=='dylib' and q['nativeArenaStatus']=='unavailable-C' and q['nativeArenas'] is None,'C unavailable arenas')
 return {k:v for k,v in q.items() if k not in {'elapsedNanoseconds','maxRssBytes'}}
def container(case,arm):
 b=checkpin(case[arm+'Container']);head,payload=b.split(b'\n\n',1);ls=head.decode('ascii').splitlines();h=ls[0].split()
 require(h==['KSEED1',str(len(payload)),str(len(ls)-1)],'container full payload length')
 exports=[]
 for line in ls[1:]:
  t=line.split();require(len(t)==3 and re.fullmatch('[A-Za-z0-9_-]+',t[0]) and t[1].isdigit() and t[2].isdigit(),'export syntax');name,off,arity=t[0],int(t[1]),int(t[2]);require(off%4==0 and off+4<=len(payload),'export bounds');exports.append((name,off,arity))
 require(len(exports)==len(set(x[0] for x in exports)) and (case['symbol'],case[arm+'Offset'],1) in exports,'selected export exact')
 require(payload==checkpin(case[arm]),'whole container payload native bytes')
def main():
 require(len(sys.argv)==2 and sys.argv[1]=='--root-terminal-closure-confirmed','explicit root closure gate')
 closure=obj(A/'root-terminal-closure.json');require(closure['terminalClosureConfirmed'] is True and closure['sessionId']==63436,'specific root closure')
 g=obj(G);require(digest(read(G))==GO_HASH,'exact root GO hash');pr=obj(D/'preregistration.json');sp=obj(D/'source-pins.json');cl=obj(D/'input-closure.json');sr=obj(D/'source-report.json')
 require(len(cl)==2787 and sum(v['bytes'] for v in cl.values())==408593973,'frozen input closure count/bytes')
 require(pr['maximumInputFiles']==3072 and pr['maximumInputLogicalBytes']==448*1024*1024,'exact cap')
 require(g['status']==pr['rootGOStatus'] and g['maximumChildCalls']==255 and g['functionalAuthorized'] is True and g['timingAuthorized'] is False and g['compilerSSHAuthorized'] is False and g['noRetry'] is True,'finite GO scope')
 require(g['outputRoot']==pr['outputRoot']==str(D/'run-outputs'),'output path')
 for f,k in [('run.py','driverSHA256'),('source-pins.json','sourcePinsSHA256'),('preregistration.json','preregistrationSHA256'),('input-closure.json','inputClosureSHA256')]:require(digest(read(D/f))==g[k]==sr[k],'frozen source '+f)
 allpins={p:{'path':p,**v} for p,v in cl.items()}
 for f,v in sp.items():allpins[str(D/f)]={'path':str(D/f),**v}
 for v in g['sourceReviews']+[g['LC40RootAcceptance']]:allpins[v['path']]=v
 allpins[str(G)]={'path':str(G),**pins[str(G)]}
 require(len(allpins)<=3072 and sum(v['bytes'] for v in allpins.values())<=448*1024*1024,'combined cap before hash')
 for p,v in allpins.items():
  s=Path(p).lstat();require(stat.S_ISREG(s.st_mode) and s.st_size==v['bytes'],'full closure stat '+p)
 for v in allpins.values():checkpin(v)
 stage('Full input closure, source registry and root GO independently read and hashed once')
 require(len(g['sourceReviews'])==2 and len({v['path'] for v in g['sourceReviews']})==2,'two distinct reviews')
 for v in g['sourceReviews']:
  q=obj(v['path']);require(q['status']==pr['sourceReviewStatus'] and all(q[k]==g[k] for k in ['sourcePinsSHA256','driverSHA256','preregistrationSHA256']),'exact source review binding')
 proofs={}
 for name,v in pr['proofs'].items():
  q=obj(v['report']['path']);proofs[name]=q;require(q['status']==v['status'] and q['inputPinsSHA256']==v['inputPins']['sha256'],'proof '+name)
  for p,pv in obj(v['inputPins']['path']).items():require(cl[p]==pv,'inherited proof closure')
 a40=obj(g['LC40RootAcceptance']['path']);require(a40['status']==pr['root40AcceptanceRequired'] and a40['independentReport']==pr['proofs']['LC40']['report'] and a40['originalWorkloads']==19 and a40['closedLoaderCalls']==40,'root actual40 acceptance')
 a30=obj(pr['LC30Acceptance']['path']);require(a30['status']=='ROOT_ACCEPTED_FINITE_LC_MD5_SHA30_FUNCTIONAL_ONLY' and a30['actualCalls']==30 and a30['independentReport']==pr['proofs']['LC30']['report'] and a30['OFFONFuelAndFourTerminalArenasParity'] is True,'root retained30 acceptance')
 require(proofs['LC40']['counts']['closedLoaderCalls']==40 and proofs['LC40']['G1G2G3WholeContainerAndNativeByteFixedpoint'] is True,'actual40 facts')
 matrix=obj(pr['canonicalMatrix']['path'])['entries'];expected=[e for e in matrix if e['workload'] not in ['md5sum','nettle-sha256']]
 require(len(matrix)==19 and len(expected)==len(pr['cases'])==17,'remaining original17')
 profiles=obj(pr['resourceProfiles']['path'])
 for c,e in zip(pr['cases'],expected):
  require(c['workload']==e['workload'] and c['symbol']==e['symbol'] and c['iterations']==e['iterations'] and len(c['iterations'])==5 and c['source']['sha256']==e['expectedSourceSha256'],'original source/body/profiles');checkpin(c['source'])
  require(c['resourceReferenceProfiles']==[v for v in profiles if v['workload']==c['workload']],'resource profiles exact')
  off=next(v for v in (proofs['SR4']['images'] if c['workload']=='nettle-aes' else proofs['SR40']['remaining17']) if v.get('workload',v.get('label'))==c['workload'])
  on=next(v for v in proofs['LC40']['images'] if v['workload']==c['workload'])
  for arm,z in [('OFF',off),('ON',on)]:
   require(c[arm]==z['native'] and c[arm+'Container']==z['container'] and c[arm+'Offset']==z['offset'],'accepted exact copied artifact '+arm);container(c,arm)
  cb=checkpin(c['C']);rb=checkpin(c['CRunner']);ci=next(v for v in proofs['C19']['images'] if v['workload']==c['workload']);ri=next(v for v in proofs['CConsumer19']['images'] if v['workload']==c['workload'])
  require(c['C']['sha256']==ci['sha256'] and c['C']['bytes']==ci['bytes'] and c['CSymbol']==ci['cSymbolPlannedOnly'],'current C identity')
  require(c['CRunner']['sha256']==ri['runnerSHA256'] and c['CRunner']['bytes']==ri['runnerBytes'] and rb.count(cb)==1 and rb.find(cb)==ri['immutableImageByteAnchors']['C'],'whole current C embedded position')
 stage('Exact original17 complement, profiles, whole OFF/ON container payloads, exports and historical current C byte anchors')
 o=D/'run-outputs';term=obj(o/'terminal.json');rawreport=obj(o/'report.json');rows=obj(o/'attempts.json');env=obj(o/'effective-environment.json')
 require(term=={'calls':255,'allCallsClosed':True,'failure':False,'noRetry':True},'driver terminal closure')
 require(not (o/'failure.json').exists() and len(rows)==255,'finite255 no failure')
 base={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':str(o/'tmp'),'LANG':'C','LC_ALL':'C','TZ':'UTC'}
 ne={**base,'KEXE_ARG_TYPES':'i64','KEXE_RESULT_TYPE':'i64','KEXE_STRUCTURED_REPORT':'1','KEXE_FUEL':'16777216','KEXE_PAIRS':'2097152','KEXE_STRING_POOL':'65536','KEXE_VECTORS':'4096','KEXE_VECTOR_ITEMS':'65536','KEXE_CPU_SECONDS':'30','KEXE_WALL_SECONDS':'30'}
 require(env=={'native':ne,'C':base,'allInheritedRemoved':True},'exact literal environment')
 parsed=[];idx=0
 for c in pr['cases']:
  for n in c['iterations']:
   arms={}
   for arm in ['OFF','ON','C']:
    r=rows[idx];idx+=1;label=c['workload']+'-'+arm+'-n'+str(n)
    argv=[c['CRunner']['path'],'dylib',c['C']['path'],c['CSymbol'],'aarch64',str(n),'1','0','16777216'] if arm=='C' else [pr['loader']['path'],c[arm]['path'],str(c[arm+'Offset']),'1','aarch64','-',str(n)]
    require(set(r)=={'index','label','argv','environment','state','timeoutSeconds','returncode','failure','cleanupException','stdoutSHA256','stderrSHA256'},'ledger schema')
    require(r['index']==idx and r['label']==label and r['argv']==argv and r['environment']==(base if arm=='C' else ne),'exact ordered argv/env')
    require(r['state']=='terminal' and r['returncode']==0 and r['failure'] is None and r['cleanupException'] is None and r['timeoutSeconds']==40,'closed success no cleanup failure')
    b=read(o/(label+'.stdout'));e=read(o/(label+'.stderr'));require(len(b)<=1048576 and len(e)<=1048576 and digest(b)==r['stdoutSHA256'] and digest(e)==r['stderrSHA256'],'raw first SHA binding')
    arms[arm]=(cresult if arm=='C' else native)(b,e,n)
   require(arms['OFF']==arms['ON'] and arms['C']['result']==arms['ON']['result'],'OFFON exact fuel four arenas and C boolean parity')
   parsed.append({'workload':c['workload'],'n':n,'arms':arms})
 require(len(parsed)==85 and obj(o/'comparisons.json')==parsed,'independent actual85 matches saved summaries')
 require(rawreport['status']=='PASS_FINITE_LC_REMAINING17_FUNCTIONAL255_ONLY' and rawreport['calls']==255 and rawreport['completedTriples']==85 and rawreport['comparisons']==parsed and rawreport['joinedOriginal19Calls']==285 and rawreport['retainedAcceptedCalls']==30,'author report corroborates parsed raw')
 require(rawreport['timingQualified'] is False and rawreport['officialScore'] is False and rawreport['registerCanaryQualified'] is False,'qualification boundaries')
 require(proofs['LC30']['counts']['closedChildCalls']==30 and proofs['LC30']['counts']['completeTriples']==10 and len(proofs['LC30']['comparisons'])==10 and proofs['LC30']['nativeResultFuelFourTerminalArenaPairsExact'] is True,'retained accepted30')
 require({v['workload'] for v in parsed+proofs['LC30']['comparisons']}=={e['workload'] for e in matrix},'joined original19 exact coverage')
 stage('255 closed calls / 85 independent raw triples; native booleans and 16M fuel, exact OFFON four terminal arenas, C same boolean and unavailable null arenas')
 stage('Join with root accepted retained MD5/SHA30 yields original19 / 95 profiles / 285 calls')
 report={'status':'PASS_INDEPENDENT_ACTUAL_LC_REMAINING17_FUNCTIONAL255_ONLY','sourcePinsSHA256':g['sourcePinsSHA256'],'driverSHA256':g['driverSHA256'],'preregistrationSHA256':g['preregistrationSHA256'],'rootGOSHA256':GO_HASH,'counts':{'closedChildCalls':255,'nativeCalls':170,'historicalCCalls':85,'completeTriples':85,'newWorkloads':17,'retainedAcceptedCalls':30,'joinedOriginalWorkloads':19,'joinedCalls':285,'frozenInputFiles':2787,'frozenInputLogicalBytes':408593973,'combinedPrerequisiteFiles':len(allpins),'combinedPrerequisiteBytes':sum(v['bytes'] for v in allpins.values())},'checks':checks,'exactArgvEnvironmentRawSHA':True,'nativeResultFuelFourTerminalArenaPairsExact':True,'historicalCEmbeddedWholeBytePositionExact':True,'CZeroFuelUnavailableNullArenas':True,'comparisons':parsed,'nativeCallsByAuditor':0,'authorValidatorReplay':False,'timingQualified':False,'officialScore':False,'runtimeRegisterCanaryQualified':False,'G3Original19CorrespondenceQualified':False,'limits':['Terminal arena used values are not peak RSS.','Original19 native images emitted by G0; fixedpoint does not establish G3 original19 correspondence.','Retained accepted30 is joined from its exact root accepted independent audit.','Finite original source profiles only; no timing, official score, universal trap or ABI register canary qualification.']}
 ip=json.dumps(pins,indent=2,sort_keys=True)+'\n';(A/'input-pins.json').write_text(ip);report['inputPinsSHA256']=digest(ip.encode());(A/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k in ['status','counts','inputPinsSHA256']}))
if __name__=='__main__':
 try:main()
 except Exception as ex:
  (A/'hold.json').write_text(json.dumps({'status':'HOLD_INDEPENDENT_ACTUAL_LC_REMAINING17_FUNCTIONAL255','exception':repr(ex),'checksCompleted':checks,'nativeCallsByAuditor':0},indent=2)+'\n');raise
