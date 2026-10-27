#!/usr/bin/env python3
"""Stage vector fixtures; native frontends, identities and executed alias probes decide."""
import argparse
import hashlib
import json
import platform
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRA = ['seed/04-definition-cid.kotoba', 'seed/05-definition-graph.kotoba',
         'seed/05-checked-definition.kotoba', 'seed/06-definition-groups.kotoba',
         'seed/05-checked-source.kotoba', 'seed/05-source-loops.kotoba']
ENTRY = r'''
(defn- seed-main [] :i64
 (if (not= (io-argc) 2) 2
  (let [mode (io-arg 0) text (io-fs2-text 65 (io-arg 1) "")]
   (cond (= mode "source") (dsb-source text false)
         (= mode "kir") (dsb-source text true)
         (= mode "compiler") (dsb-source-resource text false 1)
         (= mode "reference")
           (let [status (dcs-run text)]
            (if (= status 0) 0 (let [out (io-err (string-concat "DCP:E" (string-concat (mem-u2dec status) "\n")))] 1)))
         :else 2))))
'''
def pin(path):
    raw = path.read_bytes()
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
def function(body, params='v x', types=':vector-i64 :i64', result=':vector-i64', name='f'):
    return '{:name ' + name + ' :params [' + params + '] :param-types [' + types + '] :result ' + result + ' :effects #{} :body ' + body + '}'
def module(functions):
    return '{:format :kotoba.kir/v4 :entry nil :exports [] :effects #{} :functions [' + ' '.join(functions) + ']}\n'
def rows(raw):
    lines = raw.decode().splitlines()
    assert lines[0] == 'DCP1 6 2'
    return {p[0]:p[1:] for p in [line.split() for line in lines[1:]]}

def main(compiler, out):
    host = platform.machine()
    assert platform.system() == 'Linux' and host in ['aarch64','x86_64']
    target, machine = ('aarch64-linux',183) if host == 'aarch64' else ('x86_64-linux',62)
    product = json.loads((ROOT/'native-product.json').read_text())
    assert pin(compiler) == product['rootImage' if host == 'aarch64' else 'image']
    out.mkdir(parents=True,exist_ok=False)
    (out/'observer.py').write_bytes(Path(__file__).read_bytes())
    core = [p for p in (ROOT/'seed/CORE-STATIC-MANIFEST').read_text().splitlines() if p and not p.startswith('#')][:-1]
    paths = core + EXTRA
    unity = '\n'.join((ROOT/p).read_text() for p in paths) + ENTRY
    env = dict(PATH='/nonexistent',KEXE_STACK_BYTES='8388608',KEXE_FUEL='10000000000',
               KEXE_ALLOW='35,37,38,39',KEXE_CAP_RESOURCES_35=str(out))
    report = dict(schema='amu.native-source-vectors.v1',status='RUNNING',host=[platform.system(),host],
                  compiler=pin(compiler),observer=pin(Path(__file__)),modules={p:pin(ROOT/p) for p in paths},
                  calls=[],mutations=[],executions=[],productionCompilerClosureChanged=False,
                  wholeCompilerBridgeQualified=False,persistentBuildQualified=False,
                  sourceResourceProofQualified=False,publicKirStaticQualified=False,emulation=False)
    def save():
        (out/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(name, argv, code=0, execution_env=env):
        p = subprocess.run(list(map(str,argv)),cwd=out,env=execution_env,capture_output=True,timeout=300)
        for stream in ['stdout','stderr']:(out/(name+'.'+stream)).write_bytes(getattr(p,stream))
        report['calls'].append(dict(name=name,exit=p.returncode,stdout=pin(out/(name+'.stdout')),stderr=pin(out/(name+'.stderr'))))
        save()
        assert p.returncode == code,(name,p.returncode,p.stdout[-200:],p.stderr[-500:])
        return p
    def build(name, text):
        src,image = out/(name+'.kotoba'),out/(name+'.elf')
        src.write_text(text)
        run('build-'+name,[compiler,'compile',src,'--target',target,'--output',image,'--format','static'])
        image.chmod(0o755)
        assert image.read_bytes().startswith(b'\x7fELF') and struct.unpack_from('<H',image.read_bytes(),18)[0] == machine
        return image
    producer = build('vector-producer',unity)
    report['producer'] = pin(producer)
    oracle_paths = ['seed/00-ns-static.kotoba','seed/01-mem.kotoba','seed/02-io.kotoba',
                    'seed/03-source-sha256.kotoba','seed/04-definition-cid.kotoba','seed/tests/native-source-vector-oracle.kotoba']
    oracle = build('independent-vector-oracle','\n'.join((ROOT/p).read_text() for p in oracle_paths))
    report.update(oracle=pin(oracle),oracleModules={p:pin(ROOT/p) for p in oracle_paths})
    specs = {
        'alloc':('(defn f [x :i64] :vector-i64 (vector-alloc x))',function('(vector-alloc x)','x',':i64')),
        'conj':('(defn f [v :vector-i64 x :i64] :vector-i64 (vector-conj v x))',function('(vector-conj v x)')),
        'assoc':('(defn f [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc v i x))',function('(vector-assoc v i x)','v i x',':vector-i64 :i64 :i64')),
        'assoc!':('(defn f [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))',function('(vector-assoc! v i x)','v i x',':vector-i64 :i64 :i64')),
        'literal':('(defn f [x :i64] :vector-i64 [x 42])',function('[x 42]','x',':i64')),
    }
    observed,inputs = {},{}
    for name,(source,kir) in specs.items():
        source_path,kir_path = out/(name+'.input'),out/(name+'.kir')
        source_path.write_text('(ns vector-source) '+source+'\n')
        kir_path.write_text(module([kir]))
        a=run('source-'+name,[producer,'source',source_path]).stdout
        b=run('reference-'+name,[producer,'reference',kir_path]).stdout
        expected=run('oracle-'+name,[oracle,name]).stdout.decode().strip()
        assert rows(a)==rows(b) and rows(a)['f'][0]==expected
        observed[name]=rows(a);inputs[name]=source_path
    assert observed['assoc']['f'][0] != observed['assoc!']['f'][0]
    negatives = {
        'arity':('source','(ns invalid) (defn f [v :vector-i64] :vector-i64 (vector-assoc! v 0))'),
        'value-type':('source','(ns invalid) (defn f [v :vector-i64 s :string] :vector-i64 (vector-assoc! v 0 s))'),
        'result-type':('source','(ns invalid) (defn f [x :i64] :string (vector-alloc x))'),
        'reserved-name':('reference',module([function('x','x',':i64',':i64','vector-assoc!')])),
        'unknown-primitive':('reference',module([function('(vector-poke! v 0 x)')])),
        'hidden-capability':('reference',module([function('(let [s (typed-cap-call 37 :string :string "x")] (vector-assoc! v 0 x))')])),
    }
    for name,(lane,text) in negatives.items():
        p=out/('refuse-'+name+'.input');p.write_text(text)
        result=run('refuse-'+name,[producer,lane,p],1)
        assert not result.stdout and result.stderr.startswith((b'DSB:',b'DCP:'))
    full = [p for p in (ROOT/'seed/FULL-MANIFEST').read_text().splitlines() if p and not p.startswith('#')]
    execution_path='seed/tests/native-source-loop-execution.kotoba'
    parts=[]
    for name in full:
        text=(ROOT/name).read_text()
        if name=='seed/78-full-entry.kotoba':
            assert text.count('(defn- seed-main [] :i64') == 1
            text=text.replace('(defn- seed-main [] :i64','(defn- dsv-original-main [] :i64')
        parts.append(text)
    driver=build('kir-execution-compiler','\n'.join(parts)+'\n'+(ROOT/execution_path).read_text())
    report.update(executionCompiler=pin(driver),executionCompilerModules={p:pin(ROOT/p) for p in [*full,execution_path]})
    programs = {
        'alloc-count':('(let [v (vector-alloc 3)] (vector-count v))',3),
        'alloc-zero':('(let [v (vector-alloc 2)] (vector-at v 1))',0),
        'mutable-alias':('(let [v (vector-alloc 1) w (vector-assoc! v 0 42)] (vector-at v 0))',42),
        'immutable-alias':('(let [v (vector-alloc 1) w (vector-assoc v 0 42)] (vector-at v 0))',0),
        'conj-alias':('(let [v (vector-alloc 0) w (vector-conj v 7)] (+ (vector-count v) (vector-at w 0)))',7),
        'literal':('(let [v [19 23]] (+ (vector-at v 0) (vector-at v 1)))',42),
        'loop-mutation':('(let [v (vector-alloc 2)] (loop [i 0] (if (< i 2) (let [w (vector-assoc! v i (+ 20 i))] (recur (inc i))) (+ (vector-at v 0) (vector-at v 1)))))',41),
    }
    execution_inputs={}
    def select(raw):
        text=raw.decode()
        assert text.count(':entry nil :exports []') == 1
        return text.replace(':entry nil :exports []',':entry main :exports [main]')
    def kir_image(name,raw):
        kir=out/(name+'.kir');kir.write_text(select(raw));image=out/(name+'.elf')
        run('build-'+name,[driver,'kir',kir,image,target])
        image.chmod(0o755)
        assert struct.unpack_from('<H',image.read_bytes(),18)[0] == machine
        return image
    for name,(body,expected) in programs.items():
        text='(ns vector-runtime (:export [main])) (defn main [] :i64 '+body+')\n'
        src=out/('execute-'+name+'.input');src.write_text(text);execution_inputs[name]=src
        raw=run('serialize-'+name,[producer,'kir',src]).stdout
        source=build('execute-'+name+'-source',text)
        kir=kir_image('execute-'+name+'-kir',raw)
        for lane,image in [('source',source),('kir',kir)]:
            result=run('execute-'+name+'-'+lane,[image],expected,execution_env={})
            assert not result.stdout and not result.stderr
            report['executions'].append(dict(name=name,lane=lane,image=pin(image),expectedI64=expected))
    mutations = [
        ('mutable-copy','HD-VECTOR-ASSOC-BANG "vector-assoc!"','HD-VECTOR-ASSOC-BANG "vector-assoc"','assoc!','mutable-alias',0),
        ('immutable-write','HD-VECTOR-ASSOC "vector-assoc"','HD-VECTOR-ASSOC "vector-assoc!"','assoc','immutable-alias',42),
    ]
    for name,old,new,probe,runtime,wrong_result in mutations:
        assert unity.count(old) == 1
        image=build('mutant-'+name,unity.replace(old,new))
        result=run('detect-cid-'+name,[image,'source',inputs[probe]])
        assert rows(result.stdout) != observed[probe]
        raw=run('serialize-mutant-'+name,[image,'kir',execution_inputs[runtime]]).stdout
        guest=kir_image('mutant-guest-'+name,raw)
        result=run('execute-mutant-'+name,[guest],wrong_result,execution_env={})
        assert not result.stdout and not result.stderr and wrong_result != programs[runtime][1]
        report['mutations'].append(dict(name=name,image=pin(image),guest=pin(guest),built=True,executed=True,cidMismatch=True,aliasingMismatch=True))
    whole=out/'whole-compiler.input'
    whole.write_bytes(b''.join((ROOT/p).read_bytes()+b'\n' for p in full))
    assert pin(whole)==product['sourceUnity']
    result=run('whole-compiler-unbridged-refusal',[producer,'compiler',whole],1)
    assert not result.stdout and result.stderr.startswith(b'DSB:')
    report.update(status='PASS_NATIVE_SOURCE_VECTOR_OPERATIONS',matchedSourceKirCases=len(specs),
                  independentPayloadOracles=len(specs),atomicRefusals=len(negatives),
                  aliasingDistinguished=True,wholeInput=pin(whole),wholeCompilerRefusal=result.stderr.decode().strip())
    assert all(pin(ROOT/p)==v for p,v in {**report['modules'],**report['oracleModules'],**report['executionCompilerModules']}.items())
    save();print(report['status'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.compiler.resolve(),a.output.resolve())
