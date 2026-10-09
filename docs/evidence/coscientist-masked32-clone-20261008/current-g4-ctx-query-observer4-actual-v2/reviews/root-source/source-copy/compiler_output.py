"""Strict successful compiler command records only; no trap/empty/partial acceptance."""
import re,json
def ordinary_output(raw,case):
 assert type(raw)is bytes and 0<len(raw)<=8388608
 path=json.dumps(case['outputPath'],ensure_ascii=True).encode()
 if case['kind']=='compile':
  m=re.fullmatch(rb'\{:ok true, :target :aarch64-macos, :output '+re.escape(path)+rb', :bytes ([0-9]{1,10})\}\n',raw);assert m is not None
  n=int(m[1]);assert 0<n<=4194560;return {'kind':'compile','containerBytes':n}
 m=re.fullmatch(rb'\{:ok true, :output '+re.escape(path)+rb', :offset ([0-9]{1,10}), :length ([0-9]{1,10}), :arity ([0-9]{1,2})\}\n',raw);assert m is not None
 off,n,arity=map(int,m.groups());assert 0<=off<n<=4194304 and off%4==0 and arity==case['arity'];return {'kind':'extract','offset':off,'nativeBytes':n,'arity':arity}

from decode_protocol import decode

def parse_output(out,case):
 if not case['observer']:return ordinary_output(out,case)
 assert len(out)<=8388608 and out.endswith(b'\n')
 lines=out.splitlines(keepends=True);assert 4<=len(lines)<=16932
 prefix=lines[:-1];assert all(len(x)<=256 for x in prefix)
 summary=decode([x.decode('ascii')for x in prefix])
 ordinary=ordinary_output(lines[-1],case)
 return dict(ordinary,observerSummary=summary)
