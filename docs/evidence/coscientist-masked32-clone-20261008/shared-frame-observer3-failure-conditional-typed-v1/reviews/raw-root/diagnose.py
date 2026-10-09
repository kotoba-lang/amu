from pathlib import Path
import sys,json,re,hashlib
W=Path('/Users/junkawasaki/github/workspaces/codex');S=W/'shared-frame-currenttyped-observer3-source-v1-20261009';O=S/'run-outputs';D=Path(__file__).resolve().parent
sys.path.insert(0,str(S));from validate_observer import split,validate
pr=json.loads((S/'preregistration.json').read_bytes());case=pr['cases'][-1];src=(O/'nsichneu.kotoba').read_bytes();raw=(O/'nsichneu-compile.stdout').read_bytes();a=(O/'nsichneu.kseed').read_bytes();baseline=Path(case['ordinaryContainer']).read_bytes();assert a==baseline
primary=Path('/Users/junkawasaki/github/wt/amu-seed17/seed/21-check.kotoba').read_text();m=re.search(r'\(defn- ck-r6b-t-rem0 \[\] :string\s+("(?:\\.|[^"\\])*")\)',primary);assert m
suffix=b'\n'+json.loads(m[1]).encode();expanded=src+suffix
lines,_=split(raw);assert sum(x.startswith(b'ST ')for x in lines)==8910
outside=[]
for x in lines:
 if x.startswith(b'ST '):
  phase,index,kind,start,end,value=map(int,x.split()[1:]);assert 0<=start<=end<=len(expanded)
  if end>len(src):outside.append(index)
assert outside==list(range(8886,8910))
assert len(re.findall(rb'^\(defn',src,re.M))==265 and suffix.count(b'(defn- ')==1
(D/'expanded-source-diagnostic.kotoba').write_bytes(expanded)
r={'status':'ROOT_SAVED_OBSERVER3_SOURCE_RANGE_DIAGNOSIS_ONLY','originalCampaign':'FAIL','closedWait0':3,'originalParserExpectedFNCount':265,'actualFNCount':267,'nullSentinel':1,'onDiskDefns':265,'implicitLibraryDefinitions':1,'libraryGroup':'rem','sourceBytes':len(src),'expandedSourceBytes':len(expanded),'outsideTokens':outside,'wholeOrdinaryContainerEqual':True,'originalRefusalReclassified':False,'diagnosticSourceOnlyNotCompleteScanProof':True,'nativeCalls':0,'safeRewriteQualified':False}
try:r['conditionalParser']=validate(lines,a[a.index(b'\n\n')+2:],expanded,267)
except Exception as e:r['conditionalParserFailure']=str(e)
(D/'report.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items()if k!='conditionalParser'})
