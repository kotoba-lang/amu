"""Strict direct scalar loader receipt, not a performance receipt."""
import re
RX=re.compile(rb'\{:status :(ok|trap) :(result|exit) (-?[0-9]+) :fuel \{:initial ([0-9]+) :remaining ([0-9]+)\} :heap \{:capacity ([0-9]+) :used ([0-9]+)\} :string-pool \{:capacity ([0-9]+) :used ([0-9]+)\} :vectors \{:capacity ([0-9]+) :used ([0-9]+)\} :vector-items \{:capacity ([0-9]+) :used ([0-9]+)\}\}\n')
SIGNAL=b'KEXE_TRAP {:kind :signal :signal :SIGTRAP}\nKEXE_TRAP {:kind :budget :reason :budget/fuel}\n'
FIELDS=['pairs','string-pool-bytes','vectors','vector-items','heap-bytes','conj','conj-tail','conj-region','conj-copy','copied-words','reserved-words','regions','scope-releases','string-regions','string-region-appends','string-copied-bytes','string-reserved-bytes']
ARENA=re.compile(('KEXE_ARENA_USE {'+' '.join(':'+k+' ([0-9]+)'for k in FIELDS)+'}\n').encode())
def verify(raw,err,fixture,budget):
 assert isinstance(raw,bytes)and isinstance(err,bytes)and len(raw)<=1048576 and len(err)<=1048576 and fixture in ['positive','negative']and budget in ([1,2,3]if fixture=='positive'else[2,3]);m=RX.fullmatch(raw);assert m and all(len(x)<=20 for x in m.groups()[2:]);status,kind=m[1],m[2];z=list(map(int,m.groups()[2:]));value,initial,remaining,*arena=z;assert initial==budget and all(0<=x<(1<<64)for x in z[1:])
 trap=fixture=='positive'and budget==1;assert(status,kind,value,remaining)==(b'trap',b'exit',120,0)if trap else(status,kind,value,remaining)==(b'ok',b'result',16 if fixture=='positive'else 4294967289,budget-2)
 assert arena==[4096,0,1048576,0,65536,0,65536,0]
 if trap:assert err.startswith(SIGNAL);err=err[len(SIGNAL):]
 a=ARENA.fullmatch(err);assert a and all(len(x)<=20 for x in a.groups());assert list(map(int,a.groups()))==[0]*17
 return {'status':status.decode(),'resultOrExit':value,'initialFuel':initial,'remainingFuel':remaining,'arenas':arena,'nonresumingFuelTrap':trap,'arenaCounters':[0]*17}
