import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import t1_lib as gen
# usage: gen2.py copies out [native-subset]
copies=int(sys.argv[1]); out=sys.argv[2]
ports=gen.ports
if len(sys.argv)>3:
    ok=set(sys.argv[3].split(','))
    ports=[p for p in ports if os.path.basename(p)[:-7] in ok]
bodies=[];exports=[];nfn=0
for k in range(copies):
    for f in ports:
        body,exp,names=gen.load(f)
        suf="-%s-%d"%(os.path.basename(f)[:-7],k)
        bodies.append(gen.rename(body,names,suf)); nfn+=len(names)
        exports+=[e+suf for e in exp if e in names]
src="(ns seed.t1 (:export [%s]))\n"%" ".join(exports)+"\n".join(bodies)
open(out,"w").write(src)
print(out,"lines",src.count("\n")+1,"bytes",len(src),"fns",nfn,"exports",len(exports))
