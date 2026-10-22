from pathlib import Path
import hashlib,json
import z3 as z
D=Path(__file__).resolve().parent; R=Path('/Users/junkawasaki/github/wt/amu-seed17');rows=[]
u,h,cl,co,ix,newlen,newoff=z.Ints('used key cachedLength cachedOffset index newLength newOffset');lens=z.Array('lengths',z.IntSort(),z.IntSort());offs=z.Array('offsets',z.IntSort(),z.IntSort());items=z.Array('items',z.IntSort(),z.IntSort())
valid=z.Bool('valid')
def inv(count,ls,os,v=valid):return z.Implies(v,z.And(h>0,h<=count,cl==z.Select(ls,h),co==z.Select(os,h),cl>=0,co>=0))
def query(name,claims,expected):
 s=z.Solver();s.add(*claims);result=str(s.check());assert result==expected,(name,result);p=D/(name+'.smt2');p.write_text(s.sexpr()+'\n(check-sat)\n');row={'name':name,'result':result,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 if result=='sat':row['witness']=str(s.model())
 rows.append(row)
base=[u>=0,inv(u,lens,offs)]
query('descriptor-append-preserves-old-entry',base+[newlen>=0,newoff>=0,z.Not(inv(u+1,z.Store(lens,u+1,newlen),z.Store(offs,u+1,newoff)))],'unsat')
query('descriptor-reset-clears-witness',[u>=0,z.Not(inv(u,lens,offs,z.BoolVal(False)))],'unsat')
original=z.And(h>0,h<=u,ix>=0,ix<z.Select(lens,h));hit=z.And(ix>=0,ix<cl)
query('descriptor-hit-preserves-bounds-outcome',base+[valid,original!=hit],'unsat')
value,writeat=z.Ints('newValue writeAt');updated=z.Store(items,writeat,value)
query('descriptor-content-write-loads-fresh-item',base+[valid,original,z.Select(updated,co+ix)!=z.Select(updated,z.Select(offs,h)+ix)],'unsat')
u2,q=z.Ints('returnedUsed quantifiedOldKey');lens2=z.Array('returnedLengths',z.IntSort(),z.IntSort());offs2=z.Array('returnedOffsets',z.IntSort(),z.IntSort())
oldrows=z.ForAll(q,z.Implies(z.And(q>0,q<=u),z.And(z.Select(lens2,q)==z.Select(lens,q),z.Select(offs2,q)==z.Select(offs,q))))
query('descriptor-no-reset-return-summary',base+[valid,u2>=u,oldrows,z.Not(inv(u2,lens2,offs2))],'unsat')
# Deliberately unsafe retained key after release/reuse: one valid old row and new shorter row.
query('descriptor-recycle-key-only-is-unsafe',[h==1,cl==3,ix==2,u==1,z.Select(lens,h)==1,hit,z.Not(original)],'sat')
query('descriptor-release-key-only-is-unsafe',[h==1,cl==3,ix==0,u==0,hit,z.Not(original)],'sat')
olditem=z.Int('cachedItem');query('descriptor-caching-element-is-unsafe',[olditem==0,value==99,z.Select(z.Store(items,writeat,value),writeat)!=olditem],'sat')
ns,w,j=z.Ints('oldSavedRegisters writeRegister bankIndex');regs=z.Array('registers',z.IntSort(),z.IntSort());bank=19+ns+j
query('descriptor-new-bank-disjoint-from-original-operands',[ns>=0,ns<=7,j>=0,j<3,z.Or(z.And(w>=0,w<19),z.And(w>=19,w<19+ns)),z.Select(z.Store(regs,w,value),bank)!=z.Select(regs,bank)],'unsat')
out={'status':'PASS fresh stated-assumption descriptor lifetime SMT laws and unsafe controls','solver':z.get_version_string(),'sourcePins':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'tools/kexe_loader.c',R/'seed/41-a64gen.kotoba']},'queries':rows,'unsat':sum(r['result']=='unsat' for r in rows),'satControls':sum(r['result']=='sat' for r in rows),'assumptions':['Runtime append writes only a fresh row; content write modifies items only; reset or unknown barrier clears validity.','Backing pointer stable within no-reset context; returned-call summary assumes monotone count and unchanged all old descriptor rows, requiring source closure binding; trusted native ABI preserves new saved banks.','Source and machine binding for proposed optimization remains required; finite models do not prove arbitrary runtime/callback/compiler soundness.','No native candidate implementation, native execution, profiling or timing by this proof.'],'nativeExecutions':0,'newMeasurements':0};(D/'descriptor-lifetime-laws.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS9 SMT obligations:',out['unsat'],'UNSAT,',out['satControls'],'unsafe SAT controls')
