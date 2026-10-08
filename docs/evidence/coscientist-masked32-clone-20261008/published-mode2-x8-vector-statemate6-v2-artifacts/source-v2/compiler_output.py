"""Exact whole compiler-command output validator, no operational APIs."""
import re,json
def parse_output(raw,case):
 assert isinstance(raw,bytes) and 0<len(raw)<=8388608
 path=json.dumps(case['outputPath'],ensure_ascii=True).encode()
 if case['kind']=='compile':
  pattern=rb'\{:ok true, :target :aarch64-macos, :output '+re.escape(path)+rb', :bytes ([0-9]{1,10})\}\n'
  m=re.fullmatch(pattern,raw);assert m is not None,'whole compile output'
  n=int(m[1]);assert 0<n<=4194560
  return {'kind':'compile','containerBytes':n}
 assert case['kind']=='extract'
 pattern=rb'\{:ok true, :output '+re.escape(path)+rb', :offset ([0-9]{1,10}), :length ([0-9]{1,10}), :arity ([0-9]{1,2})\}\n'
 m=re.fullmatch(pattern,raw);assert m is not None,'whole extract output'
 offset,length,arity=map(int,m.groups());assert offset%4==0 and 0<=offset<length<=4194304 and arity==case['arity']
 return {'kind':'extract','offset':offset,'nativeBytes':length,'arity':arity}
