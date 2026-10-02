import re,sys,glob,os
P='/Users/junkawasaki/github/kotoba-lang/amu-embench/bench/embench/ports/'
ports=sorted(glob.glob(P+'*.kotoba'))
SYM=r"[A-Za-z0-9_\-\*\+!\?<>=/\.%&]"
def load(f):
    s=open(f).read()
    m=re.match(r"\(ns [^\n]*?\(:export \[([^\]]*)\]\)\)",s)
    exp=m.group(1).split() if m else []
    body=s[m.end():] if m else s
    names=re.findall(r"\((?:defn-?|def)\s+("+SYM+"+)",body)
    return body,exp,names
def rename(body,names,suf):
    for n in sorted(set(names),key=len,reverse=True):
        body=re.sub(r"(?<!"+SYM+")"+re.escape(n)+r"(?!"+SYM+")",n+suf,body)
    return body
def gen(target_lines):
    out=[];exports=[];nfn=0;lines=0;k=0
    while True:
        for f in ports:
            body,exp,names=load(f)
            nl=body.count("\n")
            if lines+nl>target_lines: return finish(out,exports,nfn)
            suf="-%s-%d"%(os.path.basename(f)[:-7],k)
            out.append(rename(body,names,suf)); nfn+=len(names)
            exports+=[e+suf for e in exp if e in names]
            lines+=nl
        k+=1
def finish(out,exports,nfn):
    return "(ns seed.t1 (:export [%s]))\n"%" ".join(exports)+"\n".join(out),nfn,len(exports)
if __name__=="__main__":
    src,nfn,ne=gen(int(sys.argv[1]))
    open(sys.argv[2],"w").write(src)
    print(sys.argv[2],"lines",src.count("\n")+1,"bytes",len(src),"fns",nfn,"exports",ne)
