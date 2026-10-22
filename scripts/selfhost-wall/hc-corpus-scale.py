import sys,re
TOK=re.compile(r'"(?:\\.|[^"\\])*"|[()\[\]{}]|#\{|[^\s()\[\]{}"]+')
def rename(line,k):
    m=re.match(r'(\[\{f #\{1 2\}\} false )(.*)( nil \[\] \{\} \[\] #\{\} false false\])$',line)
    if not m: return line
    pre,form,post=m.groups()
    toks=TOK.findall(form)
    sym=lambda t: re.match(r'^[A-Za-z_][^\s:"]*$',t) and t not in('nil','true','false','&')
    names=set()
    # defn name, params vector, binding vectors
    i=0
    while i<len(toks):
        t=toks[i]
        if t in('defn','defn-','let','loop','for','doseq','dotimes','fn') and i>0 and toks[i-1]=='(':
            j=i+1
            if t.startswith('defn') and j<len(toks) and sym(toks[j]): names.add(toks[j]); j+=1
            if t=='fn' and j<len(toks) and sym(toks[j]): names.add(toks[j]); j+=1
            if j<len(toks) and toks[j]=='[':
                d=0;idx=0
                while j<len(toks):
                    u=toks[j]
                    if u in('[','{','#{'): d+=1
                    elif u in(']','}'):
                        d-=1
                        if d==0: break
                    elif d>=1 and sym(u):
                        if t.startswith('defn') or t=='fn' or d>1 or idx%2==0: names.add(u)
                    if d==1 and u not in('[',']'): idx+=1
                    j+=1
        i+=1
    out=[]
    for t in toks:
        out.append(t+'_%d'%k if t in names else t)
    # re-join: need original spacing; rebuild by substitution on text
    def sub(m):
        t=m.group(0)
        return t+'_%d'%k if t in names else t
    new=TOK.sub(sub,form)
    return pre+new+post
mult=int(sys.argv[1])
lines=open(sys.argv[2]).read().split('\n')
lines=[l for l in lines if l]
for k in range(mult):
    for l in lines: print(l if k==0 else rename(l,k))
