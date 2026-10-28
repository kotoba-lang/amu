#!/usr/bin/env python3
"""Observe freshly built old/new native loop planners; Python decides no identities."""
import hashlib
import json
import platform
import struct
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = 'seed/05-source-loops.kotoba'
REFERENCE = 'seed/tests/native-source-loop-reference.kotoba'
DESCRIPTOR = 'seed/tests/native-source-loop-reference.json'
ENTRY = r'''
(defn- dns-plan [source :string] :i64
  (let [S (string-concat source (ck-r6b-lib source)) front (dsb-front-h S (ck-hint-new))
        M (if (= (vector-at front MM-ERR) 0) (dsb-effects front) front)
        C (dsl-new-resource M 1)]
    (if (not= (vector-at M MM-ERR) 0) 2
      (let [plan (dsl-plan M S C) status (vector-at C 0)
            out (io-out (string-concat "PLAN " (string-concat (mem-u2dec status) "\n")))]
        (if (= status 0) 0 1)))))
(defn- seed-main [] :i64
  (cond (and (= (io-argc) 2) (= (io-arg 0) "plan"))
          (dns-plan (io-fs2-text 65 (io-arg 1) ""))
        (and (= (io-argc) 2) (= (io-arg 0) "compiler"))
          (dsb-source-resource (io-fs2-text 65 (io-arg 1) "") false 1)
        (= (io-argc) 1) (dsb-source (io-fs2-text 65 (io-arg 0) "") false)
        :else 2))
'''

def pin(path):
    raw = Path(path).read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def qualify(compiler, out, paths, fixtures, whole, expected_successes, expected_refusals):
    host = platform.machine()
    assert platform.system() == 'Linux' and host in ('aarch64', 'x86_64')
    target, machine = ('aarch64-linux', 183) if host == 'aarch64' else ('x86_64-linux', 62)
    product = json.loads((ROOT/'native-product.json').read_text())
    assert pin(compiler) == product['rootImage' if host == 'aarch64' else 'image']
    descriptor = json.loads((ROOT/DESCRIPTOR).read_text())
    assert pin(ROOT/REFERENCE) == {k:descriptor[k] for k in ('bytes','sha256')}
    assert descriptor['source'] == MODULE and descriptor['frozenReference'] == REFERENCE
    out.mkdir(exist_ok=False)
    (out/'observer.py').write_bytes(Path(__file__).read_bytes())
    env = dict(PATH='/nonexistent', KEXE_STACK_BYTES='8388608', KEXE_FUEL='10000000000',
               KEXE_ALLOW='35,37,38,39', KEXE_CAP_RESOURCES_35=str(out.parent))
    current = (ROOT/MODULE).read_text()
    frozen = (ROOT/REFERENCE).read_text()
    def unity(loop_module):
        return '\n'.join(loop_module if p == MODULE else (ROOT/p).read_text() for p in paths) + ENTRY
    report = dict(schema='amu.native-source-namespace.v1', status='RUNNING',
                  compiler=pin(compiler), observer=pin(Path(__file__)), host=[platform.system(),host],
                  modules={p:pin(ROOT/p) for p in paths+[REFERENCE,DESCRIPTOR]},
                  calls=[], mutations=[], wholeInput=pin(whole), freshNamespaceOnly=True,
                  persistedProof=False, mutableCodeFixProofCached=False,
                  wholeCompilerIdentityQualified=False, sourceResourceProofQualified=False,
                  persistentBuildQualified=False, wholeCiPerformanceQualified=False,
                  quietHostQualified=False, emulation=False, fixtureInputs=[])
    assert report['wholeInput'] == product['sourceUnity']
    def save():
        (out/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(name, argv):
        started = time.monotonic()
        p = subprocess.run(list(map(str,argv)), cwd=out, env=env, capture_output=True, timeout=300)
        for stream in ('stdout','stderr'):
            (out/(name+'.'+stream)).write_bytes(getattr(p,stream))
        report['calls'].append(dict(name=name,exit=p.returncode,seconds=time.monotonic()-started,
            stdout=pin(out/(name+'.stdout')),stderr=pin(out/(name+'.stderr'))))
        save()
        return p.returncode,p.stdout,p.stderr
    def build(name, module):
        source, image = out/(name+'.kotoba'),out/(name+'.elf')
        source.write_text(unity(module))
        code,stdout,stderr = run('build-'+name,[compiler,'compile',source,'--target',target,'--output',image,'--format','static'])
        assert code==0 and not stderr,(name,code,stderr[-500:])
        image.chmod(0o755)
        assert image.read_bytes().startswith(b'\x7fELF') and struct.unpack_from('<H',image.read_bytes(),18)[0]==machine
        return image
    old, new = build('reference',frozen),build('candidate',current)
    report.update(referenceImage=pin(old),candidateImage=pin(new))
    successes, refusals = 0, 0
    for i,path in enumerate(fixtures):
        # The native wire-35 root is the output parent. Transport every input
        # into that declared root; comparing two empty denied reads is no proof.
        staged = out/f'retained-{i}.input'
        staged.write_bytes(path.read_bytes())
        report['fixtureInputs'].append(dict(name=path.name,input=pin(path),staged=pin(staged)))
        assert pin(path)==pin(staged)
        a = run(f'fixture-{i}-old',[old,staged])
        b = run(f'fixture-{i}-new',[new,staged])
        assert a==b,path.name
        assert a[0] in (0,1)
        if a[0]==0:
            assert a[1].startswith(b'DCP1 6 2\n') and len(a[1].splitlines())>1
            successes += 1
        else:
            assert not a[1] and a[2].startswith(b'DSB:')
            refusals += 1
    assert len(fixtures)==expected_successes+expected_refusals
    assert successes==expected_successes and refusals==expected_refusals
    report['retainedFixtureCount'] = len(fixtures)
    report.update(retainedSuccessfulSourceCases=successes,retainedAtomicRefusals=refusals)
    loop = '(defn f [] :i64 (loop [i 0] i))'
    probes = {
        'public-collision':('(defn __kotoba_loop_1 [] :i64 9) '+loop,3),
        'private-collision':('(defn- __kotoba_loop_1 [] :i64 9) '+loop,3),
        'forward-collision':(loop+' (defn __kotoba_loop_1 [] :i64 9)',3),
        'second-collision':('(defn __kotoba_loop_2 [] :i64 9) (defn f [] :i64 (do (loop [i 0] i) (loop [j 0] j)))',3),
        'harmless-prefix':('(defn __kotoba_loop_999999 [] :i64 9) '+loop,0),
        'leading-zero-prefix':('(defn- __kotoba_loop_0001 [] :i64 9) '+loop,0),
        'no-loop-prefix':('(defn __kotoba_loop_1 [] :i64 9)',0),
        'constant-prefix':('(def __kotoba_loop_1 9) '+loop,0),
        'computed-constant-prefix':('(def __kotoba_loop_1 true) '+loop,0),
        'local-prefix':('(defn f [] :i64 (let [__kotoba_loop_1 9] (loop [i 0] (+ i __kotoba_loop_1))))',0),
    }
    inputs = {}
    for name,(source,status) in probes.items():
        path = out/(name+'.input'); path.write_text('(ns namespace-probe) '+source+'\n'); inputs[name]=path
        expected = (0 if status==0 else 1, f'PLAN {status}\n'.encode(), b'')
        for label,image in [('old',old),('new',new)]:
            assert run('plan-'+name+'-'+label,[image,'plan',path]) == expected,name
        assert run('source-'+name+'-old',[old,path]) == run('source-'+name+'-new',[new,path]),name
    report['namespaceProbeCount'] = len(probes)
    guard = '(let [can-collide (dsl-helper-namespace? M S)]'
    start,end = current.index('(defn- dsl-helper-namespace?'),current.index('(defn- dsl-plan')
    namespace = current[start:end]
    both = '(or (= (nm-ff M f FF-KIND) FK-DEFN) (= (nm-ff M f FF-KIND) FK-PRIV))'
    assert namespace.count(both)==1 and current.count(guard)==1
    collision_start = current.index('collision (and can-collide')
    collision_end = current.index(']\n    (if',collision_start)
    mutants = [
        ('missing-proof',current.replace(guard,'(let [can-collide false]'),'public-collision',(0,b'PLAN 0\n',b'')),
        ('private-omission',current[:start]+namespace.replace(both,'(= (nm-ff M f FF-KIND) FK-DEFN)')+current[end:],'private-collision',(0,b'PLAN 0\n',b'')),
        ('prefix-as-collision',current[:collision_start]+'collision can-collide'+current[collision_end:],'harmless-prefix',(1,b'PLAN 3\n',b'')),
    ]
    for name,module,probe,wrong in mutants:
        image = build('mutant-'+name,module)
        assert run('detect-'+name,[image,'plan',inputs[probe]]) == wrong
        report['mutations'].append(dict(name=name,image=pin(image),built=True,executed=True,nativePlanMismatch=True))
    outputs=[]
    for i,(label,image) in enumerate([('old',old),('new',new),('new',new),('old',old)]):
        result = run(f'whole-abba-{i}-{label}',[image,'compiler',whole])
        assert result[0]==1 and not result[1] and result[2].startswith(b'DSB:')
        outputs.append(result)
    assert all(result==outputs[0] for result in outputs)
    report.update(status='PASS_NATIVE_SOURCE_NAMESPACE',sameHostABBA=True,
                  sameHostNativeX86Observed=host=='x86_64',wholeCompilerRefusal=outputs[0][2].decode().strip())
    assert all(pin(ROOT/p)==value for p,value in report['modules'].items())
    assert all(pin(path)==row['input']==pin(out/f'retained-{i}.input')
               for i,(path,row) in enumerate(zip(fixtures,report['fixtureInputs'])))
    assert pin(Path(__file__))==report['observer']
    save()
    return dict(report=pin(out/'observations.json'),retainedFixtureCount=len(fixtures),
                namespaceProbeCount=len(probes),builtExecutedMutants=len(mutants),sameHostABBA=True,
                wholeCiPerformanceQualified=False)
