"""Strict saved-output qualification, no subprocesses. C has no fuel/arena semantics."""
import json,re
COUNTERS=('pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes')
REPORT=re.compile(r'\{:status :ok :result (-?\d+) :fuel \{:initial (\d+) :remaining (\d+)\} :heap \{:capacity (\d+) :used (\d+)\} :string-pool \{:capacity (\d+) :used (\d+)\} :vectors \{:capacity (\d+) :used (\d+)\} :vector-items \{:capacity (\d+) :used (\d+)\}\}\n')
def native_raw(stdout,stderr):
 assert len(stdout)<=16384 and len(stderr)<=16384
 m=REPORT.fullmatch(stdout.decode('ascii'));assert m
 nums=list(map(int,m.groups()));assert nums[1]==16777216 and 0<=nums[2]<=nums[1] and nums[3::2]==[2097152,65536,4096,65536]
 pattern='KEXE_ARENA_USE {'+' '.join(':'+k+r' (\d+)' for k in COUNTERS)+'}\n'
 a=re.fullmatch(pattern,stderr.decode('ascii'));assert a
 counters=list(map(int,a.groups()));assert counters[4]==16*counters[0]+counters[1]+16*counters[2]+8*counters[3]
 return {'result':nums[0],'fuelInitial':nums[1],'fuelRemaining':nums[2],'arena17':counters,'finalUsed':nums[4::2]}
def unique_object(pairs):
 d={}
 for k,v in pairs:
  assert k not in d
  d[k]=v
 return d
def parse(stdout,stderr,case,expected,rc):
 assert rc==0 and len(stdout)<=16384 and len(stderr)<=16384
 lines=stdout.splitlines(keepends=True);assert len(lines)==2
 got=native_raw(lines[0],stderr)
 t=json.loads(lines[1],object_pairs_hook=unique_object);assert set(t)=={'schema','arm','calls','warmup','elapsedNs','nativeObservablesAvailable','resetIncluded'}
 assert all(type(t[k]) is int for k in ('arm','calls','warmup','elapsedNs'))
 assert all(type(t[k]) is bool for k in ('nativeObservablesAvailable','resetIncluded'))
 assert t['schema']=='CURRENT17_TIMING_V1' and t['arm']==('OFF','ON','C').index(case['arm']) and t['calls']==case['calls'] and t['warmup']==1
 assert type(t['elapsedNs']) is int and 0<t['elapsedNs']<=30_000_000_000 and t['resetIncluded'] is False
 assert t['nativeObservablesAvailable'] is (case['arm']!='C')
 assert got['result']==expected['result']
 if case['arm']!='C':assert got==expected
 else:assert got['fuelRemaining']==16777216 and got['arena17']==[0]*17 and got['finalUsed']==[0]*4
 return {'timing':t,'observables':got if case['arm']!='C' else {'result':got['result'],'fuel':None,'arena17':None}}
def cases(rows):
 assert len(rows)==19 and len({r['workload'] for r in rows})==19
 out=[]
 for r in rows:
  assert len(r['profiles'])==5 and len(set(r['profiles']))==5
  for n in r['profiles']:
   for arm in ('OFF','ON','C'):out.append({'workload':r['workload'],'arm':arm,'n':n,'calls':1,'warmup':1,'phase':'fresh'})
 for r in rows:
  for arm in ('OFF','ON','C'):out.append({'workload':r['workload'],'arm':arm,'n':max(r['profiles']),'calls':2,'warmup':1,'phase':'repeat-reset'})
 assert len(out)==342
 return out
