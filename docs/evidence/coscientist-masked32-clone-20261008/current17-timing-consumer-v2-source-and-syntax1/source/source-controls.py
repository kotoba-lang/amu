"""Pure SOURCE/decoder checks; never C compilation or invocation."""
from pathlib import Path
import json,copy,hashlib,re
from qualification import *
from header import header,relative
D=Path(__file__).resolve().parent
R=Path('/Users/junkawasaki/github/workspaces/codex/tc-hft-g4-held-v6-original19-runtime190-source-v1-20261009-dense/run-outputs')
rows=json.loads((D/'packet.json').read_text())['entries']
cs=cases(rows);positives=0;negatives=0
for row in rows:
 for n in row['profiles']:
  for arm in ('OFF','ON'):
   out=(R/f'{row["workload"]}-{arm}-n{n}.stdout').read_bytes();err=(R/f'{row["workload"]}-{arm}-n{n}.stderr').read_bytes()
   expected=native_raw(out,err)
   c={'arm':arm,'calls':1};t={'schema':'CURRENT17_TIMING_V1','arm':('OFF','ON','C').index(arm),'calls':1,'warmup':1,'elapsedNs':100,'nativeObservablesAvailable':True,'resetIncluded':False}
   b=out+(json.dumps(t)+'\n').encode();assert parse(b,err,c,expected,0);positives+=1
   for badout,baderr,rc in [(b,b'',0),(b+b'\n',err,0),(b,err,1),(b.replace(b':remaining ',b':remaining 9',1),err,0)]:
    try:parse(badout,baderr,c,expected,rc)
    except (AssertionError,ValueError):negatives+=1
    else:raise AssertionError('invalid raw accepted')
for p in ('/tmp/a','../a','a/../b',''):
 try:relative(p)
 except AssertionError:negatives+=1
 else:raise AssertionError('bad relative path')
# Exact helper bank construction: author substitution invert and compare every byte.
s=(D/'timing-loader.c').read_text()
s=s.replace('#include "timing-extension.h"\nstatic int timing_loader_main(int argc, char **argv) {','int main(int argc, char **argv) {')
s=s.replace('    result = timing_loop(timing_arm==2?timing_c_fn:fn, shared, args);','    result = fn(args[0], args[1], args[2], args[3], args[4], 0, 0,\n                (int64_t)(uintptr_t)&shared->context);')
s=s.replace('    timing_parent_report(child_status);\n','').removesuffix('\n#include "timing-frontend.h"\n')
assert hashlib.sha256(s.encode()).hexdigest()=='04428f47af807fcb19342d035ce730f980f97c001747c806e059bbc4380c52b2'
assert len(cs)==342 and sum(c['calls']+c['warmup'] for c in cs)==741
# Reference names must exist in exact copied source; no assertion of C syntax/native binding.
base=s
for n in ('kexe_census_pair_sites','kexe_growth_regions','kexe_string_regions','kexe_string_region_cache','kexe_growth_region_marks','kexe_string_region_marks','kexe_append_used','kexe_stdout_used','kexe_vector_region','kexe_use'):
 assert re.search(r'\b'+n+r'\b',base)
# Concrete duplicate and non-integer JSON field refusals.
for kind in ('duplicate','bool-arm','float-calls'):
 tt=copy.deepcopy(t)
 if kind=='bool-arm':tt['arm']=True
 elif kind=='float-calls':tt['calls']=1.0
 tail=(json.dumps(tt)+'\n').encode()
 if kind=='duplicate':tail=tail.replace(b'{',b'{"elapsedNs":100,',1)
 try:parse(out+tail,err,{'arm':arm,'calls':1},expected,0)
 except (AssertionError,ValueError):negatives+=1
 else:raise AssertionError('timing JSON mutation accepted '+kind)
# Synthetic thin Mach-O bytes test generator mechanics only, never fresh-build credit.
import struct
row=copy.deepcopy(rows[0]);off=Path(row['OFF']['native']['path']).read_bytes();on=Path(row['ON']['native']['path']).read_bytes()
c=b'\xcf\xfa\xed\xfe'+struct.pack('<IIIII',0x100000c,0,6,0,0)+bytes(8)
f={'status':'PASS_INDEPENDENT_FRESH_CURRENT19_C_BUILD_SOURCE_IDENTITY_ONLY','workload':row['workload'],'symbol':row['symbol'],'bridgeABI':'I64_8ARGS','artifact':{'bytes':len(c),'sha256':hashlib.sha256(c).hexdigest()}}
assert b'timing_c_bytes' in header(row,off,on,c,f)
for kind in ('offset','type','workload','symbol','c-hash','c-type','proof-status'):
 rr=copy.deepcopy(row);ff=copy.deepcopy(f);cc=c
 if kind=='offset':rr['ON']['offset']=len(on)
 elif kind=='type':rr['ON']['offset']=True
 elif kind=='workload':rr['workload']='../bad'
 elif kind=='symbol':rr['symbol']='unknown'
 elif kind=='c-hash':ff['artifact']['sha256']='0'*64
 elif kind=='c-type':cc=c[:12]+struct.pack('<I',2)+c[16:];ff['artifact']['sha256']=hashlib.sha256(cc).hexdigest()
 elif kind=='proof-status':ff['status']='ROOT_ONLY'
 try:header(rr,off,on,cc,ff)
 except AssertionError:negatives+=1
 else:raise AssertionError('header mutation accepted '+kind)
result={'status' :'PASS_PURE_CURRENT17_SOURCE_AND_DECODER_CONTROLS_ONLY','nativeRawPositives':positives,'negativeControls':negatives,'qualificationChildren':342,'guestInvocationsIncludingWarmup':741,'syntheticHeaderPositive':1,'syntheticHeaderNegatives':7,'syntheticHeaderHasNoBuildCredit':True,'nativeCompilation':0,'helperBankInverseByteIdentity':True}
print(json.dumps(result,indent=2))
