"""Exactly one registered trusted Clang command with lower inherited limits preserved."""
from pathlib import Path
import sys,os,resource
from run import load,need,scope,go_guard,argv,save,receipt,environment_admission
D=Path(__file__).resolve().parent
need(len(sys.argv)==3,'GO,index only');g=load(sys.argv[1]);pr=load(D/'preregistration.json');sp=load(D/'source-pins.json');ip=load(D/'input-pins.json');rs=load(D/'recipes.json')['commands'];scope(pr,ip,rs);root,h=go_guard(g,pr,sp,ip)
n=int(sys.argv[2]);need(str(n)==sys.argv[2]and 1<=n<=38,'finite index');O=root/pr['outputRelative'];phase='dependencies'if n<=19 else'build';r=rs[(n-1)%19];a=argv(r,root,O,h,n<=19);env=pr['environment']|{'TMPDIR':str(O/'tmp'),'SDKROOT':h['sdk']};witness=environment_admission(env,dict(os.environ))
limits={}
for name,target in [('RLIMIT_CPU',(180,181)),('RLIMIT_FSIZE',(16777216,16777216)),('RLIMIT_CORE',(0,0))]:
 kind=getattr(resource,name);old=resource.getrlimit(kind)
 def lower(x,y):return y if x==resource.RLIM_INFINITY else min(x,y)
 hard=lower(old[1],target[1]);soft=min(lower(old[0],target[0]),hard);resource.setrlimit(kind,(soft,hard));actual=resource.getrlimit(kind);need(actual==(soft,hard),'limit readback');limits[name]={'inherited':old,'actual':actual}
save(O/f'{n:02d}.resources.json',{'index':n,'phase':phase,'argv':a,'environment':env,'environmentWitness':witness,'limits':limits,'GO':{'path':sys.argv[1],**receipt(sys.argv[1])},'regularFileCapBytes':16777216,'noLimitEnlargement':True})
os.execve(a[0],a,env)
