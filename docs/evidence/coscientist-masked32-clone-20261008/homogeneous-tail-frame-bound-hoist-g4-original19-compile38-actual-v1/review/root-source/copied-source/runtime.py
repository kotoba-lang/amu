"""Exact report/counter/resource decoder. Import inert."""
import re,json
FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
ARENA_PAT=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in FIELDS)+'}\n').encode())
def counters(b):
 m=ARENA_PAT.fullmatch(b)
 if not m or any(len(x)>20 for x in m.groups()):return {'status':'unavailable-or-invalid','values':None,'entireStderrIsCounterLine':False}
 u=dict(zip(FIELDS,map(int,m.groups())));valid=all(0<=x<2**64 for x in u.values())and u['heap-bytes']==16*u['pairs']+u['string-pool-bytes']+16*u['vectors']+8*u['vector-items']and u['pairs']<=16777216 and u['string-pool-bytes']<=268435456 and u['vectors']<=4194304 and u['vector-items']<=134217728
 return {'status':'valid'if valid else'invalid','values':u,'entireStderrIsCounterLine':True}


"""Offline exact pinned i64 structured-report parser. No operational calls."""
import re
REPORT_PAT=re.compile(rb'\{:status :(ok|trap) :(result|exit) (-?[0-9]{1,20}) :fuel \{:initial ([0-9]{1,20}) :remaining ([0-9]{1,20})( :metered false)?\} :heap \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :string-pool \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :vectors \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\} :vector-items \{:capacity ([0-9]{1,20}) :used ([0-9]{1,20})\}\}\n')
def need(x,m):
 if not x:raise AssertionError(m)
def parse_report(raw):
 need(isinstance(raw,bytes)and 0<len(raw)<=65536,'bounded exact raw structured report')
 m=REPORT_PAT.fullmatch(raw);need(m is not None,'whole i64 structured report/no other output')
 status,field=m[1].decode(),m[2].decode();answer=int(m[3]);initial=int(m[4]);remaining=int(m[5]);metered=m[6]is None
 need((status=='ok'and field=='result'and -(1<<63)<=answer<(1<<63))or(status=='trap'and field=='exit'and 0<=answer<=255),'typed result/trap field')
 need(0<=remaining<=initial<(1<<64),'exact u64 fuel relationship')
 caps=[int(m[k])for k in [7,9,11,13]];used=[int(m[k])for k in [8,10,12,14]]
 need(caps==[16777216,268435456,4194304,134217728]and all(0<=u<=c for u,c in zip(used,caps)),'exact arena capacities and used bounds')
 return {'status':status,'result':answer if status=='ok'else None,'trapExit':answer if status=='trap'else None,'initialFuel':initial,'remainingFuel':remaining,'metered':metered,'arenaCapacities':dict(zip(['pairs','string-pool-bytes','vectors','vector-items'],caps)),'arenaUsed':dict(zip(['pairs','string-pool-bytes','vectors','vector-items'],used))}
def observe_report(raw):
 try:return {'status':'valid','decoded':parse_report(raw)}
 except (AssertionError,ValueError)as ex:return {'status':'unavailable-or-invalid','exception':repr(ex)}
