import sys,re,glob
def forms(t):
    i=0;n=len(t);out=[]
    while i<n:
        c=t[i]
        if c==';':
            while i<n and t[i]!='\n': i+=1
        elif c=='(':
            d=0;s=i;ok=True
            while i<n:
                c=t[i]
                if c=='"':
                    i+=1
                    while i<n and t[i]!='"':
                        if t[i]=='\\': i+=1
                        i+=1
                elif c==';':
                    while i<n and t[i]!='\n': i+=1
                    continue
                elif c=='\\': i+=1
                elif c=='(': d+=1
                elif c==')':
                    d-=1
                    if d==0: i+=1;break
                i+=1
            out.append(t[s:i])
        else: i+=1
    return out
def allf(t):
    r=[]
    for f in forms(t):
        if re.match(r'\((defn|defn-)\s',f): r.append(f)
        else: r+=allf(f[1:-1])
    return r
lim=int(sys.argv[1])
files=sys.argv[2:]
res=[]
for f in files:
    t=open(f).read()
    for fm in allf(t):
        if not re.match(r'\((defn|defn-)\s',fm): continue
        if '"' in fm and '\n' in re.sub(r'"(\\.|[^"\\])*"','',fm)==False: pass
        # drop forms with strings containing newlines, comments, non-ascii, reader macros
        strs=re.findall(r'"(?:\\.|[^"\\])*"',fm)
        if any('\n' in s for s in strs): continue
        body=re.sub(r'"(?:\\.|[^"\\])*"',lambda m:'\x00'*0+m.group(0),fm)
        if ';' in re.sub(r'"(?:\\.|[^"\\])*"','',fm): continue
        if not fm.isascii() or '#' in re.sub(r'"(?:\\.|[^"\\])*"','',fm).replace('#{','') or '^' in fm or '`' in fm or '@' in re.sub(r'"(?:\\.|[^"\\])*"','',fm): continue
        one=re.sub(r'\s+',' ',fm) if not strs else None
        if one is None:
            parts=re.split(r'("(?:\\.|[^"\\])*")',fm)
            one=''.join(p if p.startswith('"') else re.sub(r'\s+',' ',p) for p in parts)
        res.append('[{f #{1 2}} false %s nil [] {} [] #{} false false]'%one)
        if len(res)>=lim: break
    if len(res)>=lim: break
print('\n'.join(res))
