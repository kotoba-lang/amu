"""k4proto.py IN.bin KSEED OUT.bin -- K4 upper-bound prototype on a K1 image (measurement only).

A context-fuel store `str xS,[x7,#8]` becomes `nop` when, on every path after it, the counter
is stored again before anything can read it. Readers: an exact fuel load that K1 left in
place, any other x7-based load, BL/BLR/RET, and every encoding the word model does not cover.
Trap paths (BRK/UDF) are NOT readers: a real K4 would publish the register in a trap stub, so
this prototype is wrong only on trapping or fuel-exhausting runs. Never ship this rewrite."""
import struct,sys,json,os
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','proto'))
import flf_emul as E
def main():
    img,kseed,outp=sys.argv[1:4]
    raw=open(img,'rb').read(); W=[0]+list(struct.unpack('<%dI'%(len(raw)//4),raw[:len(raw)//4*4]))
    cn=len(W)
    hdr=open(kseed,'rb').read().split(b'\n\n',1)[0].decode().splitlines()[1:]
    roots=[int(l.split()[1])//4+1 for l in hdr]
    # reachability, same CFG as the K1 emulation (BL destinations reached, not successors)
    V=[0]*cn; st=list(roots)
    for r in roots: V[r]=1
    succ={}
    while st:
        i=st.pop(); w=W[i]; s=[]
        if E.bl(w):
            t=E.of_dest(w,i)
            if 1<=t<cn and not V[t]: V[t]=1; st.append(t)
            s=[i+1]
        elif E.of_branch(w)>0:
            s=[E.of_dest(w,i)]+([] if E.stop(w) else [i+1])
        elif not E.stop(w): s=[i+1]
        if E.adr(w):
            b=E.sx(((w>>5)&0x7ffff)<<2|((w>>29)&3),21)
            if b%4==0 and 1<=i+b//4<cn and not V[i+b//4]: V[i+b//4]=1; st.append(i+b//4)
        s=[j for j in s if 1<=j<cn]; succ[i]=s
        for j in s:
            if not V[j]: V[j]=1; st.append(j)
    def reader(w):
        if E.bl(w) or E.blr(w) or (w&0xfffffc1f)==0xd65f0000: return True
        if E.is_ld(w): return True
        if ((w>>5)&31)==7 and (((w&0x3b000000) in (0x39000000,0x38000000) and (w&0x00c00000)!=0) or ((w&0x3a000000)==0x28000000 and (w&0x00400000))): return True
        if E.scn_defs(w)<0 and not E.is_st(w): return True
        return False
    trap=lambda w:(w&0xffe0001f)==0xd4200000 or (w&0xffff0000)==0
    # backward liveness of the published counter: LIVE[i] = live before word i
    LIVE=[False]*cn; order=sorted(succ,reverse=True); ch=True; sweeps=0
    while ch:
        ch=False; sweeps+=1
        for i in order:
            w=W[i]
            if reader(w): v=True
            elif E.is_st(w) or trap(w): v=False
            else: v=any(LIVE[j] for j in succ[i])
            if v!=LIVE[i]: LIVE[i]=v; ch=True
    out=list(W); dead=0; stores=0
    for i in succ:
        if E.is_st(W[i]):
            stores+=1
            if not any(LIVE[j] for j in succ[i]): out[i]=0xd503201f; dead+=1
    open(outp,'wb').write(struct.pack('<%dI'%(cn-1),*out[1:])+raw[len(raw)//4*4:])
    print(json.dumps(dict(image=os.path.basename(img),reached=len(succ),fuelStores=stores,removed=dead,sweeps=sweeps)))
main()
