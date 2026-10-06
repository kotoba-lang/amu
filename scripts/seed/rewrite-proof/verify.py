#!/usr/bin/env python3
"""Excluded diagnostic tooling. Z3 must be supplied explicitly by its environment.
No solver, Python, JVM or Node dependency is added to an Amu product path.
"""
import argparse, collections, copy, hashlib, json, os, re, subprocess
from pathlib import Path
import z3
from translation import controls

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def validate_rules(rules):
    # Bind the proved laws to exact supported schemas. New patterns/conditions
    # require new obligations; a familiar obligation name is not a certificate.
    supported = [
        ('i64/add-zero','pure-value',['add-i64','x',['const-i64',0]],'x',
         ['wrapping-i64','same-type','no-effect-or-trap-removal','retain-fuel'],'add-zero'),
        ('a64/closed-vector-constant-index','target-lowering',
         ['checked-vector-access','handle',['proved-local-constant','index']],
         'checked-scaled-offset-access',
         ['closed-mode2-contract','index-0-through-4095','straightline-local-fact',
          'invalidate-explicit-and-coalesced-writes','invalidate-control-and-unknown-effects',
          'retain-runtime-local-assignments','retain-original-handle-check',
          'unsigned-bound-at-original-access','retain-fuel-traps-memory-order',
          'proved-register-liveness'],'constant-index')]
    if rules.get('format') != 'amu.rewrite-experiment/v1' or len(rules.get('rules',[])) != len(supported):
        raise ValueError('unsupported rule format or count')
    for rule,spec in zip(rules['rules'],supported):
        fields=('id','phase','match','replace','requires','obligation')
        if tuple(rule.get(k) for k in fields) != spec:
            raise ValueError('unproved rule pattern, replacement, guard or phase')
        allowed=set(fields)|({'productImplementation'} if spec[0].startswith('a64/') else set())
        if set(rule) != allowed:raise ValueError('unsupported rule field')
    expected={'rootDispatch':'opcode','strategy':'deterministic bounded worklist',
              'maxMatchesPerNode':1,'onBudgetExhaustion':'retain original lowering',
              'decrease':'unresolved eligible roots'}
    if rules.get('execution') != expected:raise ValueError('unproved execution strategy')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', type=Path, required=True)
    p.add_argument('--offset', type=Path, required=True)
    p.add_argument('--loader', type=Path, required=True)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    rules = json.loads((HERE/'rules.json').read_text())
    validate_rules(rules)
    schema_mutations=[]
    for field,value in [('replace','zero'),('requires',[]),('phase','memory')]:
        mutant=copy.deepcopy(rules); mutant['rules'][0][field]=value
        try:validate_rules(mutant)
        except ValueError:schema_mutations.append(field)
        else:raise AssertionError('schema mutation accepted: '+field)
    obligations = []
    def solve(name, bad, expected, scope):
        s = z3.Solver(); s.set(timeout=30000); s.add(bad)
        (a.out/(name+'.smt2')).write_text(s.to_smt2())
        result = s.check(); assert str(result) == expected, (name,result,s.reason_unknown())
        row = dict(name=name, result=str(result), scope=scope)
        if result == z3.sat: row['counterexample'] = str(s.model())
        obligations.append(row); print('PASS',name,result,flush=True)
    x,k,length,base,offset = z3.BitVecs('x index length base offset',64)
    small = z3.ULE(k,z3.BitVecVal(4095,64))
    good = z3.ULT(k,length)
    solve('add-zero',x+0 != x,'unsat','all 64-bit wrapping integers; operands already evaluated')
    solve('constant-index-bound',z3.And(small,good != z3.UGT(length,k)), 'unsat','all unsigned 64-bit lengths and admitted indices')
    solve('constant-index-address',z3.And(small,base+((offset+k)<<3) != (base+(offset<<3))+(k<<3)), 'unsat','64-bit address arithmetic; valid allocation and same original bounds required externally')
    mem = z3.Array('memory',z3.BitVecSort(64),z3.BitVecSort(64))
    solve('store-load-law',z3.Select(z3.Store(mem,x,k),x) != k,'unsat','same address in abstract sequential memory; no intervening effects, trap or concurrency claim')
    compiler,request,delegation,policy,runtime = z3.BitVecs('compiler request delegation policy runtime',64)
    effective = compiler & request & delegation & policy & runtime
    solve('authority-no-expansion',z3.Or(*[(effective & ~mask) != 0 for mask in [compiler,request,delegation,policy,runtime]]), 'unsat','all 64-bit permission masks; intersection cannot expand authority; not actual runtime verification')
    current,issued,cached = z3.Bools('current issued cached')
    solve('revoke-rechecked',z3.And(z3.Not(current),z3.And(issued,current)), 'unsat','atomic use rechecks current validity; concurrency/linearization must match this model')
    n = z3.Int('remainingEligibleRoots')
    solve('strict-decrease',z3.And(n>0,z3.Or(n-1<0,n-1>=n)), 'unsat','each accepted rewrite removes one eligible root, adds none; dependency updates cannot restore it')
    solve('mutation-signed-bounds',z3.And(small,good != (k<length)), 'sat','bad signed comparison; mutation must be caught')
    solve('mutation-omit-zero-bound',z3.And(k==0,z3.Not(good)), 'sat','bad omission of length check for zero index')
    solve('mutation-wrong-scale',z3.And(small,base+(k<<3) != base+(k<<2)), 'sat','bad scaled address emission')
    fuel = z3.BitVec('fuel',64)
    solve('mutation-drop-fuel',fuel-1 != fuel, 'sat','a rewrite cannot erase a semantic charge')
    solve('mutation-stale-authority',z3.And(cached,z3.Not(current)), 'sat','cached issue witness alone cannot authorize a current use')

    # Explicit state search includes the observable violation bit, unlike kernel
    # enumeration which counts violating transitions over all 64 input states.
    def explore(mutate):
        start=(0,False); todo=collections.deque([start]); paths={start:[]}; edges=0; counter=None
        while todo:
            state,bad=todo.popleft(); permitted=(state&31)==31
            for action in range(13):
                q=state; b=bad
                if action<5:q |= 1<<action
                elif action<10:q &= ~(1<<(action-5))
                elif action==10:
                    if not permitted:continue
                    q |= 32
                elif action==11:q &=31
                else:b |= bool(state&32) if mutate and not permitted else False
                edges+=1; nxt=(q,b)
                if nxt not in paths:
                    paths[nxt]=paths[(state,bad)]+[action];todo.append(nxt)
                    if b and counter is None:counter=paths[nxt]
        assert bool(counter)==mutate
        return dict(mutation=mutate,reachableStates=len(paths),edges=edges,counterexample=counter,
                    scope='five Boolean authority inputs, cached witness, atomic use; no liveness or concurrent interleaving guarantee')
    models=[explore(False),explore(True)]
    # Independent arithmetic oracle for all state/transition pairs in native kernel.
    counts=[]
    for mutate in [0,1]:
        count=0
        for state in range(64):
            for action in range(12):
                if action<5:q=state|2**action
                elif action<10:q=state&~2**(action-5)
                elif action==10:q=state|32 if state%32==31 else state
                else:q=state%32
                count+= int((bool(q&32) if mutate else q%32==31) and q%32!=31)
        counts.append(count)
    assert counts[0]==0 and counts[1]>0
    env=dict(os.environ,KEXE_COMMAND='1',KEXE_CAP_RESOURCES_35=str(HERE)+':'+str(a.out),
             KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800',KEXE_STRING_POOL='268435456',
             KEXE_VECTORS='65536',KEXE_PAIRS='16777216',KEXE_VECTOR_ITEMS='134217728')
    runs=[]
    for kernel,expected_counts in [('kernel',counts),('graph',[0,257,258,258])]:
        compiled=a.out/(kernel+'.kseed'); image=a.out/(kernel+'.bin')
        args=[('compile',['compile',str(HERE/(kernel+'.kotoba')),'--target','aarch64-macos','--output',str(compiled)]),
              ('extract',['extract-native',str(compiled),'--symbol','batch','--output',str(image)])]
        for stage,extra in args:
            q=subprocess.run([str(a.loader),str(a.seed),a.offset.read_text().strip(),'0','aarch64','35,37,38,39','--',*extra],env=env,text=True,capture_output=True)
            (a.out/(kernel+'-'+stage+'.log')).write_text(q.stdout+q.stderr); assert q.returncode==0,(stage,q.stdout[-1000:],q.stderr)
        off=int(re.search(r':offset (\d+)',q.stdout)[1]);(a.out/(kernel+'.offset')).write_text(str(off)+'\n')
        for mutation,expected in enumerate(expected_counts):
            runenv=dict(os.environ,KEXE_STRUCTURED_REPORT='1',KEXE_FUEL='16777216')
            runenv.pop('KEXE_COMMAND',None)
            q=subprocess.run([str(a.loader),str(image),str(off),'1','aarch64','-',str(mutation)],env=runenv,text=True,capture_output=True)
            (a.out/f'{kernel}-native-{mutation}.log').write_text(q.stdout+q.stderr)
            assert q.returncode==0,(mutation,q.stdout,q.stderr)
            result=int(re.search(r':result (-?\d+)',q.stdout)[1]);assert result==expected,(mutation,result,expected)
            runs.append(dict(kernel=kernel,mutation=mutation,expected=expected,result=result,exit=q.returncode,imageSha256=sha(image)))
            print('PASS native',kernel,mutation,result,flush=True)
    pins={str(p.relative_to(HERE)):sha(p) for p in HERE.iterdir() if p.is_file()}
    recipe={'domain':'amu.rewrite-proof-recipe/v1','sources':pins,'solver':z3.get_version_string(),
            'seedSha256':sha(a.seed),'loaderSha256':sha(a.loader),'seedEntryOffset':a.offset.read_text().strip(),
            'rulesSha256':sha(HERE/'rules.json'),'nativeImages':{r['kernel']:r['imageSha256'] for r in runs},'target':'aarch64-macos',
            'semanticDefCID':'not-derived-by-this-diagnostic','productEmitterChanged':False}
    recipeHash=hashlib.sha256(json.dumps(recipe,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    report=dict(status='abstract-laws-and-native-finite-model-qualified',obligations=obligations,models=models,native=runs,schemaMutationsRefused=schema_mutations,
                recipe=recipe,recipeSha256=recipeHash,translationValidation=controls(),
                tla='specification saved; TLC/TLAPS not run',performance='no new timing or speedup claim',
                adoption='not eligible: generator, translation, fixed-point, timing and integrated gates remain')
    (a.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS proof experiment; NOT product-emitter proof or performance promotion',recipeHash,flush=True)
if __name__=='__main__':main()
