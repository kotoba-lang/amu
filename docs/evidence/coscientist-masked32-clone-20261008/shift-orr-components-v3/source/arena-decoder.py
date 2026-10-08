import re
FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
PAT=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in FIELDS)+'}\n').encode())
def counters(err):
 matches=[PAT.fullmatch(line)for line in err.splitlines(keepends=True)];matches=[m for m in matches if m is not None]
 if len(matches)!=1:return {'status':'unavailable-or-not-exactly-one-counter-line','matchingLines':len(matches),'values':None,'entireStderrIsCounterLine':False}
 if any(len(x)>20 for x in matches[0].groups()):return {'status':'invalid','matchingLines':1,'values':None,'entireStderrIsCounterLine':PAT.fullmatch(err)is not None}
 u=dict(zip(FIELDS,map(int,matches[0].groups())));valid=all(type(v)is int and 0<=v<2**64 for v in u.values()) and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items'] and u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
 return {'status':'valid'if valid else 'invalid','matchingLines':1,'values':u,'entireStderrIsCounterLine':PAT.fullmatch(err)is not None}
