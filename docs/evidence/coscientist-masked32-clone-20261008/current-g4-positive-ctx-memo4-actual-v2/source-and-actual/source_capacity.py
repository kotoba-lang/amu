"""SOURCE capacity contract and pure mem-fits boundary checks, not live M inspection."""
from pathlib import Path
import json,re
WORDS=147680;BASE=6623488;END=8388608

def mem_fits(top,words):
 end=top+words
 return words>=0 and end>=top and end<=END

def source_capacity_contract(D,pr):
 a=json.loads((D/'source-assembly.json').read_bytes());bank={r['module']:r['path']for r in a['modulePins']}
 ns=Path(bank['seed/00-ns.kotoba']).read_text();mem=Path(bank['seed/01-mem.kotoba']).read_text()
 for name,value in [('MM-WORDS',8388608),('MM-HEAP-BASE',BASE),('MM-HEAP-END',END),('MM-FN-CAP',8192),('MM-SIR-CAP',196608)]:
  assert re.search(r'\(def '+re.escape(name)+r' '+str(value)+r'\)',ns)
 assert '(> end MM-HEAP-END) 0'in mem and 'ok (mem-fits top end words)'in mem
 source=(D/'41-memo.kotoba').read_text();assert source.count('(mem-alloc M0 (+ gn-a-lp MM-LABEL-CAP 208))')==1
 assert '(if qm-active (gn-zero M2 qm-base qm-end) M2)'in source and 'qm-active (= (vector-at M2 MM-ERR) 0)'in source
 c=pr['memoCapacityContract'];assert c['generatorBlockWords']==WORDS and c['newTailWords']==208 and c['additionalWords']==128 and c['actualTopKnownBeforeLaunch']is False
 assert END-BASE==1765120 and 0<WORDS<END-BASE
 # Successful native mem-alloc establishes top+WORDS<=END. SOURCE cannot
 # invent a current top or promise all original-capacity executions fit.
 assert mem_fits(BASE,WORDS) and mem_fits(END-WORDS,WORDS)
 assert not mem_fits(END-WORDS+1,WORDS) and not mem_fits(END,WORDS) and not mem_fits(BASE,-1)
 return True
