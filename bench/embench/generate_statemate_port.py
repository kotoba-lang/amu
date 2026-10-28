#!/usr/bin/env python3
# BOOTSTRAP-TOOL: pinned C AST -> newly authored typed benchmark, no product path.
import argparse,hashlib,json,pathlib,re,subprocess
from pycparser import CParser,c_ast
p=argparse.ArgumentParser();p.add_argument('upstream',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
b=a.upstream.read_bytes()
if hashlib.sha256(b).hexdigest()!='389c4bae5caba79a6f9139e02bf5e61c92921a756ec01200d2d2f16dc1c4ccf5':raise SystemExit('unreviewed Statemate profile')
s=b.decode();prefix=s[:s.index('static int  benchmark_body')];prefix=re.sub(r'^#include.*$','',prefix,flags=re.M)
cpp=subprocess.run(['clang','-E','-P','-x','c','-'],input=prefix,text=True,capture_output=True,check=True).stdout
ast=CParser().parse(cpp);fields=[];slots={};kinds={}
for n in ast.ext:
 if isinstance(n,c_ast.Decl):
  if n.name=='Bitlist':assert isinstance(n.type,c_ast.ArrayDecl) and n.type.dim.value=='64';continue
  assert isinstance(n.type,c_ast.TypeDecl) and n.init is None
  kind='ulong' if n.type.type.names==['unsigned','long'] else 'char' if n.type.type.names==['char'] else 'int'
  assert n.type.type.names in (['unsigned','long'],['char'],['int'])
  slots[n.name]=64+len(fields);kinds[n.name]=kind;fields.append({'name':n.name,'slot':slots[n.name],'kind':kind})
size=64+len(fields);code=[];counter=0
functions={n.decl.name for n in ast.ext if isinstance(n,c_ast.FuncDef)}
def fresh(expr):
 global counter
 name='s-'+str(counter);counter+=1;code.append(f'(defn- {name} [s :vector-i64] :vector-i64 {expr})\n');return name
ops={'+':'+','-':'-','*':'*','==':'=','!=':'not=','<':'<','>':'>','<=':'<=','>=':'>='}
def unsigned(n):
 if isinstance(n,c_ast.ID):return kinds[n.name]=='ulong'
 if isinstance(n,c_ast.BinaryOp):return unsigned(n.left) or unsigned(n.right)
 if isinstance(n,c_ast.UnaryOp):return unsigned(n.expr)
 return False
def truth(n):
 if isinstance(n,c_ast.UnaryOp) and n.op=='!':return '(not '+truth(n.expr)+')'
 if isinstance(n,c_ast.BinaryOp) and n.op in ('&&','||'):return '('+('and' if n.op=='&&' else 'or')+' '+truth(n.left)+' '+truth(n.right)+')'
 if isinstance(n,c_ast.BinaryOp) and n.op in ('==','!=','<','>','<=','>='):return expr(n)
 return '(not= '+expr(n)+' 0)'
def expr(n):
 if isinstance(n,c_ast.ID):return f'(vector-at s {slots[n.name]})'
 if isinstance(n,c_ast.Constant):return str(int(n.value,0))
 if isinstance(n,c_ast.ArrayRef):
  assert isinstance(n.name,c_ast.ID) and n.name.name=='Bitlist';return '(vector-at s '+expr(n.subscript)+')'
 if isinstance(n,c_ast.UnaryOp):
  if n.op=='!':return '(if '+truth(n.expr)+' 0 1)'
  if n.op=='-':return '(- 0 '+expr(n.expr)+')'
  raise ValueError(n.op)
 if isinstance(n,c_ast.BinaryOp):
  if n.op in ('&&','||'):return '(if '+truth(n)+' 1 0)'
  left,right=expr(n.left),expr(n.right)
  if n.op in ('<','>','<=','>=') and (unsigned(n.left) or unsigned(n.right)):
   if n.op in ('>','<='):left,right=right,left
   result='(uless '+left+' '+right+')';return '(not '+result+')' if n.op in ('<=','>=') else result
  return '('+ops[n.op]+' '+left+' '+right+')'
 raise ValueError(type(n).__name__)
def seq(nodes,k,br):
 for node in reversed(nodes or []):k=stmt(node,k,br)
 return k
def stmt(n,k,br):
 if isinstance(n,c_ast.Compound):return seq(n.block_items,k,br)
 if isinstance(n,c_ast.UnaryOp) and n.op in ('p++','++','p--','--'):
  assert isinstance(n.expr,c_ast.ID)
  value=c_ast.BinaryOp('+' if '+' in n.op else '-',n.expr,c_ast.Constant('int','1'))
  return stmt(c_ast.Assignment('=',n.expr,value),k,br)
 if isinstance(n,c_ast.Assignment):
  assert n.op=='=';rhs=expr(n.rvalue)
  if isinstance(n.lvalue,c_ast.ID):idx=str(slots[n.lvalue.name]);kind=kinds[n.lvalue.name]
  else:assert isinstance(n.lvalue,c_ast.ArrayRef) and n.lvalue.name.name=='Bitlist';idx=expr(n.lvalue.subscript);kind='char'
  rhs='('+('s8' if kind=='char' else 's32')+' '+rhs+')' if kind!='ulong' else rhs
  return fresh(f'(let [value {rhs} index {idx}] ({k} (put s index value)))')
 if isinstance(n,c_ast.If):
  yes=stmt(n.iftrue,k,br);no=stmt(n.iffalse,k,br) if n.iffalse else k
  return fresh(f'(if {truth(n.cond)} ({yes} s) ({no} s))')
 if isinstance(n,c_ast.Break):assert br is not None;return br
 if isinstance(n,c_ast.FuncCall):
  assert n.name.name in functions and n.args is None
  return fresh(f'({k} (c-{n.name.name} s))')
 if isinstance(n,c_ast.While):
  loop='loop-'+str(len(code));body=stmt(n.stmt,loop,k)
  code.append(f'(defn- {loop} [s :vector-i64] :vector-i64 (if {truth(n.cond)} ({body} s) ({k} s)))\n');return loop
 if isinstance(n,c_ast.Switch):
  cases=n.stmt.block_items;assert all(isinstance(x,(c_ast.Case,c_ast.Default)) for x in cases)
  fall=k;branches=[];default=k
  for case in reversed(cases):
   fall=seq(case.stmts,fall,k)
   if isinstance(case,c_ast.Default):default=fall
   else:branches.append((expr(case.expr),fall))
  result=f'({default} s)'
  for value,target in branches:result=f'(if (= selector {value}) ({target} s) {result})'
  return fresh(f'(let [selector {expr(n.cond)}] {result})')
 raise ValueError(type(n).__name__)
for n in ast.ext:
 if isinstance(n,c_ast.FuncDef):
  first=stmt(n.body,'done',None);code.append(f'(defn- c-{n.decl.name} [s :vector-i64] :vector-i64 ({first} s))\n')
head='''(ns embench.statemate-full (:export [batch stage-cell test-statemate]))
;; All pinned STARC controller functions and switch/while control flow.
;; Copyright 1998/1999 C-LAB Paderborn, 2014-2019 Embecosm/University of Bristol.
;; SPDX-License-Identifier: GPL-3.0-or-later.
(defn- done [s :vector-i64] :vector-i64 s)
(defn- put [s :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! s i x))
(defn- s8 [x :i64] :i64 (let [v (bit-and x 255)] (if (>= v 128) (- v 256) v)))
(defn- s32 [x :i64] :i64 (let [v (bit-and x 4294967295)] (if (>= v 2147483648) (- v 4294967296) v)))
(defn- uless [a :i64 b :i64] :bool
  (if (< a 0) (if (< b 0) (< a b) false) (if (< b 0) true (< a b))))
(defn- clear-bits [s :vector-i64 i :i64] :vector-i64
  (if (= i 64) s (clear-bits (put s i 0) (+ i 1))))
'''
checks=re.findall(r'(\w+) != ([0-9]+)',s[s.index('  if (tm_entered_',s.index('verify_benchmark')):]);assert len(checks)==19
verify='(and '+' '.join(f'(= (vector-at s {slots[name]}) {value})' for name,value in checks)+')'
tail=f'''(defn- body [s :vector-i64] :vector-i64
  (c-FH_DU (c-interface (c-init (clear-bits s 0)))))
(defn- repeats [s :vector-i64 n :i64] :vector-i64
  (if (= n 0) s (repeats (body s) (- n 1))))
(defn- verify-bits [s :vector-i64 i :i64] :i64
  (if (= i 64) 1 (if (= (vector-at s i) (if (= i 5) 1 0)) (verify-bits s (+ i 1)) 0)))
(defn batch [n :i64] :i64
  (if (<= n 0) 0 (let [result (repeats (vector-alloc {size}) n)] (if {verify.replace('vector-at s','vector-at result')} (verify-bits result 0) 0))))
(defn- stages [s :vector-i64 limit :i64] :vector-i64
  (if (= limit 0) s
    (let [s1 (c-init (clear-bits s 0))]
      (if (= limit 1) s1
        (let [s2 (c-interface s1)] (if (= limit 2) s2 (c-FH_DU s2)))))))
(defn stage-cell [encoded :i64] :i64
  (let [test (quot encoded 4096) code (rem encoded 4096) stage (quot code {size}) cell (rem code {size})
        initial (put (vector-alloc {size}) {slots['time']} test)
        result (stages initial stage)] (vector-at result cell)))
(defn test-statemate [] :i64 (batch 1))
'''
a.output.write_text(head+''.join(code)+tail);a.output.with_suffix('.fields.json').write_text(json.dumps({'size':size,'fields':fields,'functions':sorted(functions),'helpers':counter},indent=2)+'\n');a.output.with_suffix('.preprocessed.c').write_text(cpp)
