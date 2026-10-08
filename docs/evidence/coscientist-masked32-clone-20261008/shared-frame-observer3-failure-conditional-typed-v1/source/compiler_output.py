"""Exact command output; observed workload prefix validated as finite saved data."""
import re,json
from pathlib import Path
from validate_observer import split,validate
def parse_output(raw,case):
 assert type(raw)is bytes and 0<len(raw)<=8388608
 observed='ordinaryContainer'in case
 if observed:lines,raw=split(raw)
 path=json.dumps(case['outputPath'],ensure_ascii=True).encode()
 if case['kind']=='compile':
  m=re.fullmatch(rb'\{:ok true, :target :aarch64-macos, :output '+re.escape(path)+rb', :bytes ([0-9]{1,10})\}\n',raw);assert m is not None
  n=int(m[1]);assert 0<n<=4194560
  result={'kind':'compile','containerBytes':n}
  if observed:
   actual=Path(case['outputPath']).read_bytes();ordinary=Path(case['ordinaryContainer']).read_bytes();assert actual==ordinary and len(actual)==n,'whole ordinary container identity'
   cut=actual.find(b'\n\n');assert cut>=0;payload=actual[cut+2:];result['observer']=validate(lines,payload,Path(case['nativeArgv'][8]).read_bytes(),case.get('expectedFNCount'))
  return result
 m=re.fullmatch(rb'\{:ok true, :output '+re.escape(path)+rb', :offset ([0-9]{1,10}), :length ([0-9]{1,10}), :arity ([0-9]{1,2})\}\n',raw);assert m is not None
 off,n,arity=map(int,m.groups());assert 0<=off<n<=4194304 and off%4==0 and arity==case['arity']
 return {'kind':'extract','offset':off,'nativeBytes':n,'arity':arity}
