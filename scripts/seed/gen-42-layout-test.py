#!/usr/bin/env python3
# scripts/seed/gen-42-layout-test.py -- regenerates seed/tests/unit/42-layout_t.kotoba (BOOTSTRAP-TOOL, test generator only).
# The expected words are computed here, independently of 42-layout, from the AArch64 immediate layouts
# (b/bl imm26 bits 25:0, b.cond/cbz imm19 bits 23:5, movz/movk imm16 bits 20:5) and the pool rule (8-byte aligned).
# Run: python3 scripts/seed/gen-42-layout-test.py ; then scripts/seed/unit.sh 42-layout
def m(x): return x & 0xFFFFFFFF
def p19(w,d): return m((w & 0xFF00001F) | ((d & 0x7FFFF)<<5)) if -262144<=d<262144 else -1
def p26(w,d): return m((w & 0xFC000000) | (d & 0x3FFFFFF)) if -(1<<25)<=d<(1<<25) else -1
def p16(w,v): return m((w & 0xFFE0001F) | ((v&0xFFFF)<<5))
L=[]
def chk(name,expr,want): L.append((name,expr,want))
BC=0x54000000; B=0x14000000; BL=0x94000000; CBZ=0xB4000003; MZ1=0xD2800001; MK1=0xF2A00001; MZ2=0xD2800002; MK2=0xF2A00002
pure=[("p19 +5",f"(ly-patch19 {BC} 5)",p19(BC,5)),
("p19 -1",f"(ly-patch19 {BC} -1)",p19(BC,-1)),
("p19 max",f"(ly-patch19 {BC} 262143)",p19(BC,262143)),
("p19 max+1",f"(ly-patch19 {BC} 262144)",-1),
("p19 min",f"(ly-patch19 {BC} -262144)",p19(BC,-262144)),
("p19 min-1",f"(ly-patch19 {BC} -262145)",-1),
("p19 keeps cond",f"(ly-patch19 {BC|1} 3)",p19(BC|1,3)),
("p19 cbz +7",f"(ly-patch19 {CBZ} 7)",p19(CBZ,7)),
("p26 +3",f"(ly-patch26 {B} 3)",p26(B,3)),
("p26 -1",f"(ly-patch26 {B} -1)",p26(B,-1)),
("p26 max",f"(ly-patch26 {B} 33554431)",p26(B,33554431)),
("p26 max+1",f"(ly-patch26 {B} 33554432)",-1),
("p26 min",f"(ly-patch26 {B} -33554432)",p26(B,-33554432)),
("p26 min-1",f"(ly-patch26 {B} -33554433)",-1),
("p26 bl -2",f"(ly-patch26 {BL} -2)",p26(BL,-2)),
("p16 movz",f"(ly-patch16 {MZ1} 4660)",p16(MZ1,0x1234)),
("p16 movk",f"(ly-patch16 {MK1} 43981)",p16(MK1,0xABCD)),
("align8 0",'(ly-align8 0)',0),("align8 1",'(ly-align8 1)',8),("align8 8",'(ly-align8 8)',8),("align8 17",'(ly-align8 17)',24),
("is-movz",f"(t-b2i (ly-is-movz {MZ1}))",1),("is-movz w",f"(t-b2i (ly-is-movz {MZ1&0x7FFFFFFF}))",1),("is-movk",f"(t-b2i (ly-is-movk {MK1}))",1),("movz not movk",f"(t-b2i (ly-is-movk {MZ1}))",0),("add not movz","(t-b2i (ly-is-movz 2332033025))",0)]
# scenario 1
N=41
prog={}
for i in range(1,41): prog[i]=0xD503201F+0  # nop placeholder
prog[2]=B; prog[30]=BC; prog[4]=CBZ; prog[6]=BL; prog[8]=MZ1; prog[9]=MK1; prog[11]=MZ2; prog[12]=MK2
fx=[(2,1,2),(30,2,1),(4,3,3),(6,4,3),(8,5,1),(11,5,2)]
labels={1:5,2:30,3:41}
fns={1:(1,2,1),2:(10,0,0),3:(21,0,1)}
lits={1:5,2:8,3:3}
def lay():
    cb=(N-1)*4; po=(cb+7)//8*8; pos={}; cur=po
    for k in sorted(lits): pos[k]=cur; cur=(cur+lits[k]+7)//8*8
    return cb,po,pos
cb,po,pos=lay()
exp={}
for i,w in prog.items(): exp[i]=w
exp[2]=p26(B,30-2); exp[30]=p19(BC,5-30); exp[4]=p19(CBZ,41-4); exp[6]=p26(BL,21-6)
exp[8]=p16(MZ1,pos[1]); exp[9]=p16(MK1,pos[1]>>16); exp[11]=p16(MZ2,pos[2]); exp[12]=p16(MK2,pos[2]>>16)
end=pos[3]+lits[3]
s1=[]
for i in (2,30,4,6,8,9,11,12,7): s1.append((f"s1 code[{i}]",f"(vector-at M1 (+ MM-CODE-BASE {i}))",exp[i]))
s1+= [("s1 ERR","(vector-at M1 MM-ERR)",0),("s1 R0","(vector-at M1 MM-R0)",end),("s1 CODE-BYTES","(vector-at M1 MM-CODE-BYTES)",end),("s1 POOL-OFF","(vector-at M1 MM-POOL-OFF)",po),
("s1 pool1","(vector-at M1 (+ (+ MM-LIT-BASE (* 1 MM-LIT-W)) LF-POOL))",pos[1]),("s1 pool2","(vector-at M1 (+ (+ MM-LIT-BASE (* 2 MM-LIT-W)) LF-POOL))",pos[2]),("s1 pool3","(vector-at M1 (+ (+ MM-LIT-BASE (* 3 MM-LIT-W)) LF-POOL))",pos[3]),
("s1 EXP-N","(vector-at M1 MM-EXP-N)",3),
("s1 exp1 fn","(vector-at M1 (+ (+ MM-EXP-BASE (* 1 MM-EXP-W)) EF-FN))",1),("s1 exp1 off","(vector-at M1 (+ (+ MM-EXP-BASE (* 1 MM-EXP-W)) EF-OFFSET))",0),("s1 exp1 arity","(vector-at M1 (+ (+ MM-EXP-BASE (* 1 MM-EXP-W)) EF-ARITY))",2),
("s1 exp2 fn","(vector-at M1 (+ (+ MM-EXP-BASE (* 2 MM-EXP-W)) EF-FN))",3),("s1 exp2 off","(vector-at M1 (+ (+ MM-EXP-BASE (* 2 MM-EXP-W)) EF-OFFSET))",80),("s1 exp2 arity","(vector-at M1 (+ (+ MM-EXP-BASE (* 2 MM-EXP-W)) EF-ARITY))",0)]
import json
NOP=0xD503201F
def CODE(i): return f"(+ MM-CODE-BASE {i})"
def FIX(k,f): return f"(+ (+ MM-FIX-BASE (* {k} MM-FIX-W)) {f})"
def LIT(k,f): return f"(+ (+ MM-LIT-BASE (* {k} MM-LIT-W)) {f})"
def FNF(k,f): return f"(+ (+ MM-FN-BASE (* {k} MM-FN-W)) {f})"
def LAB(l): return f"(+ MM-LABEL-BASE {l})"
def EXPF(k,f): return f"(+ (+ MM-EXP-BASE (* {k} MM-EXP-W)) {f})"
def fixw(k,at,kind,tgt): return [(FIX(k,'XF-AT'),at),(FIX(k,'XF-KIND'),kind),(FIX(k,'XF-TARGET'),tgt)]
KIND={'B26':'FX-B26','BC19':'FX-BC19','CB19':'FX-CB19','BL26':'FX-BL26','LIT32':'FX-LIT32'}
scen=[]  # (name, writes, checks)
def reset(ncode,nfix,nlit,nfn,erase_labels=()):
    w=[("MM-CODE-N",ncode),("MM-FIX-N",nfix),("MM-LIT-N",nlit),("MM-FN-N",nfn),("MM-EXP-N",1),("MM-ERR",0),("MM-ERR-POS",0),("MM-ERR-N",0),("MM-R0",0),("MM-POOL-OFF",0),("MM-CODE-BYTES",0)]
    return w
# scenario 1
w=reset(41,7,4,4)
for i in range(1,41): w.append((CODE(i),NOP))
for i,v in prog.items(): w.append((CODE(i),v))
for k,(at,kind,tgt) in enumerate(fx,1): w+=fixw(k,at,KIND[{1:'B26',2:'BC19',3:'CB19',4:'BL26',5:'LIT32'}[kind]],tgt)
# fixup 7 does not exist: nfix = 7 means indices 1..6
for l,v in labels.items(): w.append((LAB(l),v))
for f,(code,np_,ex) in fns.items(): w+= [(FNF(f,'FF-CODE'),code),(FNF(f,'FF-NPARAMS'),np_),(FNF(f,'FF-EXPORT'),ex)]
for k,ln in lits.items(): w+= [(LIT(k,'LF-LEN'),ln)]
scen.append(("s1",w,s1))
def errsc(name,ncode,fxl,labels_,errcode,errn=None,extra=[],nlit=1,nfn=1):
    w=reset(ncode,len(fxl)+1,nlit,nfn)
    for k,(at,kind,tgt) in enumerate(fxl,1): w+=fixw(k,at,kind,tgt)
    for l,v in labels_.items(): w.append((LAB(l),v))
    w+=extra
    ck=[(f"{name} ERR","(vector-at M1 MM-ERR)",errcode)]
    if errn is not None: ck.append((f"{name} ERR-N","(vector-at M1 MM-ERR-N)",errn))
    scen.append((name,w,ck))
# range errors / boundaries through ly-run
errsc("e-b26-range",100,[(2,'FX-B26',1)],{1:2+33554432},4201,33554432,[(CODE(2),B)])
errsc("e-b26-far-in-range",100,[(2,'FX-B26',1)],{1:2+33554431},4203,None,[(CODE(2),B)])
errsc("e-bc19-range",300000,[(2,'FX-BC19',1)],{1:2+262144},4201,262144,[(CODE(2),BC)])
errsc("e-bc19-range-neg",300000,[(262147,'FX-BC19',1)],{1:1},4201,-262146,[(CODE(262147),BC)])
errsc("e-cb19-range",300000,[(2,'FX-CB19',1)],{1:2+262144},4201,262144,[(CODE(2),CBZ)])
errsc("e-undef-label",100,[(2,'FX-B26',1)],{1:0},4203,0,[(CODE(2),B)])
errsc("e-label-beyond",100,[(2,'FX-B26',1)],{1:101},4203,101,[(CODE(2),B)])
errsc("e-lit-not-movz",100,[(2,'FX-LIT32',1)],{},4202,None,[(CODE(2),NOP),(CODE(3),NOP),(LIT(1,'LF-LEN'),4)],nlit=2)
errsc("e-lit-bad-index",100,[(2,'FX-LIT32',5)],{},4202,None,[(CODE(2),MZ1),(CODE(3),MK1),(LIT(1,'LF-LEN'),4)],nlit=2)
errsc("e-bad-kind",100,[(2,9,1)],{},4202,None,[(CODE(2),NOP)])
errsc("e-bl-bad-fn",100,[(2,"FX-BL26",7)],{},4203,0,[(CODE(2),BL)])
errsc("e-first-wins",100,[(2,'FX-B26',1),(3,'FX-B26',2)],{1:0,2:3+33554432},4203,0,[(CODE(2),B),(CODE(3),B)])
errsc("e-export-no-code",100,[],{},4203,None,[(FNF(1,'FF-CODE'),0),(FNF(1,'FF-EXPORT'),1)],nfn=2)
# accepted boundaries
def oksc(name,ncode,fxl,labels_,checks,extra=[],nlit=1,nfn=1):
    w=reset(ncode,len(fxl)+1,nlit,nfn)
    for k,(at,kind,tgt) in enumerate(fxl,1): w+=fixw(k,at,kind,tgt)
    for l,v in labels_.items(): w.append((LAB(l),v))
    w+=extra
    scen.append((name,w,[(f"{name} ERR","(vector-at M1 MM-ERR)",0)]+checks))
oksc("ok-bc19-max",262200,[(2,'FX-BC19',1)],{1:2+262143},[("ok-bc19-max word",f"(vector-at M1 {CODE(2)})",p19(BC,262143))],[(CODE(2),BC)])
oksc("ok-bc19-min",300000,[(262145,'FX-BC19',1)],{1:1},[("ok-bc19-min word",f"(vector-at M1 {CODE(262145)})",p19(BC,-262144))],[(CODE(262145),BC)])
oksc("ok-b26-self",100,[(5,'FX-B26',1)],{1:5},[("ok-b26-self word",f"(vector-at M1 {CODE(5)})",B)],[(CODE(5),B)])
oksc("ok-bl-backward",100,[(60,'FX-BL26',1)],{},[("ok-bl-back word",f"(vector-at M1 {CODE(60)})",p26(BL,-49))],[(CODE(60),BL),(FNF(1,'FF-CODE'),11)],nfn=2)
oksc("ok-label-at-end",100,[(2,'FX-CB19',1)],{1:100},[("ok-label-end word",f"(vector-at M1 {CODE(2)})",p19(CBZ,98))],[(CODE(2),CBZ)])
# pool shapes
oksc("pool-empty",1,[],{},[("empty R0","(vector-at M1 MM-R0)",0),("empty POOL-OFF","(vector-at M1 MM-POOL-OFF)",0),("empty EXP-N","(vector-at M1 MM-EXP-N)",1)],[],nlit=1)
oksc("pool-nolit",3,[],{},[("nolit R0","(vector-at M1 MM-R0)",8),("nolit CODE-BYTES","(vector-at M1 MM-CODE-BYTES)",8),("nolit POOL-OFF","(vector-at M1 MM-POOL-OFF)",8)])
oksc("pool-odd",4,[],{},[("odd R0","(vector-at M1 MM-R0)",33),("odd POOL-OFF","(vector-at M1 MM-POOL-OFF)",16),("odd pool1",f"(vector-at M1 {LIT(1,'LF-POOL')})",16),("odd pool2",f"(vector-at M1 {LIT(2,'LF-POOL')})",24)],[(LIT(1,'LF-LEN'),1),(LIT(2,'LF-LEN'),9)],nlit=3)
# lit32 beyond 16 bits: big pool: a literal of 70000 bytes then another => pos2 > 65535
oksc("lit32-hi16",100,[(10,'FX-LIT32',2)],{},[("hi movz",f"(vector-at M1 {CODE(10)})",p16(MZ1,(400+70000+7)//8*8 & 0xFFFF)),("hi movk",f"(vector-at M1 {CODE(11)})",p16(MK1,((400+70000+7)//8*8)>>16))],[(CODE(10),MZ1),(CODE(11),MK1),(LIT(1,'LF-LEN'),70000),(LIT(2,'LF-LEN'),3)],nlit=3)
# note: 100 code words -> ncode=100 -> 99 words -> 396 bytes -> poff 400
out=[]
out.append(''';; seed/tests/unit/42-layout_t.kotoba -- GENERATED by scripts/seed/gen-42-layout-test.py (hand-checked expectations
;; computed independently in Python from the AArch64 immediate layouts). Unit test of 42-layout.
;; deps:
(defn- t-digit [d :i64] :string
  (cond (= d 0) "0" (= d 1) "1" (= d 2) "2" (= d 3) "3" (= d 4) "4"
        (= d 5) "5" (= d 6) "6" (= d 7) "7" (= d 8) "8" :else "9"))
(defn- t-dec-pos [n :i64] :string
  (if (< n 10) (t-digit n)
    (string-concat (t-dec-pos (quot n 10)) (t-digit (- n (* 10 (quot n 10)))))))
(defn- t-dec [n :i64] :string
  (if (< n 0) (string-concat "-" (t-dec-pos (- 0 n))) (t-dec-pos n)))
(defn- t-say [s :string] :i64
  (let [o (typed-cap-call :io/write :string :string s)] 0))
(defn- t-verdict [got :i64 want :i64] :string
  (if (= got want) "ok" "FAIL"))
(defn- t-b2i [b :bool] :i64
  (if b 1 0))
(defn- t-bad [got :i64 want :i64] :i64
  (if (= got want) 0 1))
;; M[200] counts failures
(defn- t-chk [M :vector-i64 name :string got :i64 want :i64] :vector-i64
  (let [o (t-say (string-concat name (string-concat " " (string-concat (t-dec got) (string-concat " " (string-concat (t-dec want) (string-concat " " (string-concat (t-verdict got want) "\\n"))))))))
        f (vector-at M 200)]
    (vector-assoc! M 200 (+ f (t-bad got want)))))
;; pure checks need no M: they return 1 on failure
(defn- t-pure [name :string got :i64 want :i64] :i64
  (let [o (t-say (string-concat name (string-concat " " (string-concat (t-dec got) (string-concat " " (string-concat (t-dec want) (string-concat " " (string-concat (t-verdict got want) "\\n"))))))))]
    (t-bad got want)))
(defn- t-init [] :vector-i64
  (vector-alloc MM-WORDS))
''')
# pure
lets=[]
for i,(n,e,w) in enumerate(pure):
    lets.append(f'a{i} (t-pure "{n}" {e} {w})')
sums=[]
acc="0"
for i in range(len(pure)):
    lets.append(f"s{i} (+ {acc} a{i})"); acc=f"s{i}"
src="\n        ".join(lets)
out.append(f"(defn- t-pures [] :i64\n  (let [{src}]\n    {acc}))\n")
names=[]
for si,(name,w,ck) in enumerate(scen):
    lets=[]; cur="M0"
    for j,(a,v) in enumerate(w):
        nxt=f"W{j+1}"; lets.append(f"{nxt} (vector-assoc! {cur} {a} {v})"); cur=nxt
    lets.append(f"M1 (ly-run {cur})")
    for j,(n,e,x) in enumerate(ck): lets.append(f"g{j} {e}")
    cur2="M1"
    for j,(n,e,x) in enumerate(ck):
        nxt=f"C{j}"; lets.append(f"{nxt} (t-chk {cur2} \"{n}\" g{j} {x})"); cur2=nxt
    src="\n        ".join(lets)
    fn="t-"+name
    out.append(f"(defn- {fn} [M0 :vector-i64] :vector-i64\n  (let [{src}]\n    {cur2}))\n")
    names.append(fn)
# main: thread M through scenarios
lets=[]; cur="A0"
for k,fn in enumerate(names):
    nxt=f"A{k+1}"; lets.append(f"{nxt} ({fn} {cur})"); cur=nxt
out.append(f"""(defn- t-all [A0 :vector-i64] :i64
  (let [{chr(10).join(['        '+l if i else l for i,l in enumerate(lets)])}
        fails (vector-at {cur} 200)]
    fails))
(defn- seed-main [] :i64
  (let [o (t-say "42-layout unit test\\n")
        p (t-pures)
        n (t-all (t-init))
        o2 (t-say (string-concat "pure failures " (string-concat (t-dec p) (string-concat ", scenario failures " (string-concat (t-dec n) "\\n")))))]
    (+ p n)))
""")
open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'../../seed/tests/unit/42-layout_t.kotoba'),'w').write("".join(out))
print(len(names),"scenarios")
