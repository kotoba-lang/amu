#!/usr/bin/env python3
"""Stage vector/byte/string fixtures; native checking, identities and executions decide."""
import argparse
import hashlib
import json
import platform
import struct
import subprocess
import time
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
                  calls=[],mutations=[],executions=[],runtimeRefusals=[],productionCompilerClosureChanged=False,
                  wholeCompilerBridgeQualified=False,persistentBuildQualified=False,
                  sourceResourceProofQualified=False,publicKirStaticQualified=False,emulation=False)
    def save():
        (out/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
    def run(name, argv, code=0, execution_env=env):
        started = time.monotonic()
        p = subprocess.run(list(map(str,argv)),cwd=out,env=execution_env,capture_output=True,timeout=300)
        for stream in ['stdout','stderr']:(out/(name+'.'+stream)).write_bytes(getattr(p,stream))
        report['calls'].append(dict(name=name,exit=p.returncode,seconds=time.monotonic()-started,stdout=pin(out/(name+'.stdout')),stderr=pin(out/(name+'.stderr'))))
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
    buffer_paths = oracle_paths[:-1] + ['seed/tests/native-source-buffer-oracle.kotoba']
    buffer_oracle = build('independent-buffer-oracle','\n'.join((ROOT/p).read_text() for p in buffer_paths))
    report.update(bufferOracle=pin(buffer_oracle),bufferOracleModules={p:pin(ROOT/p) for p in buffer_paths})
    specs = {
        'alloc':('(defn f [x :i64] :vector-i64 (vector-alloc x))',function('(vector-alloc x)','x',':i64')),
        'conj':('(defn f [v :vector-i64 x :i64] :vector-i64 (vector-conj v x))',function('(vector-conj v x)')),
        'assoc':('(defn f [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc v i x))',function('(vector-assoc v i x)','v i x',':vector-i64 :i64 :i64')),
        'assoc!':('(defn f [v :vector-i64 i :i64 x :i64] :vector-i64 (vector-assoc! v i x))',function('(vector-assoc! v i x)','v i x',':vector-i64 :i64 :i64')),
        'literal':('(defn f [x :i64] :vector-i64 [x 42])',function('[x 42]','x',':i64')),
    }
    buffer_specs = {
        'bytes-from-vector-i64': ('v :vector-i64', 'v', ':vector-i64', ':bytes'),
        'vector-i64-from-bytes': ('b :bytes', 'b', ':bytes', ':vector-i64'),
        'string-from-utf8': ('b :bytes', 'b', ':bytes', ':string'),
        'string-compare': ('s :string t :string', 's t', ':string :string', ':i64'),
        'string-index-of': ('s :string t :string', 's t', ':string :string', ':i64'),
        'bytes-empty': ('', '', '', ':bytes'),
        'bytes-count': ('b :bytes', 'b', ':bytes', ':i64'),
        'bytes-at': ('b :bytes i :i64', 'b i', ':bytes :i64', ':i64'),
        'bytes-concat': ('b :bytes c :bytes', 'b c', ':bytes :bytes', ':bytes'),
        'bytes-slice': ('b :bytes s :i64 e :i64', 'b s e', ':bytes :i64 :i64', ':bytes'),
    }
    for op,(typed,params,types,result) in buffer_specs.items():
        body='('+op+(' '+params if params else '')+')'
        specs[op]=('(defn f ['+typed+'] '+result+' '+body+')',function(body,params,types,result))
    observed,inputs = {},{}
    for name,(source,kir) in specs.items():
        source_path,kir_path = out/(name+'.input'),out/(name+'.kir')
        source_path.write_text('(ns vector-source) '+source+'\n')
        kir_path.write_text(module([kir]))
        a=run('source-'+name,[producer,'source',source_path]).stdout
        b=run('reference-'+name,[producer,'reference',kir_path]).stdout
        expected=run('oracle-'+name,[buffer_oracle if name in buffer_specs else oracle,name]).stdout.decode().strip()
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
        'bytes-from-wrong-type':('source','(ns invalid) (defn f [b :bytes] :bytes (bytes-from-vector-i64 b))'),
        'vector-from-wrong-type':('source','(ns invalid) (defn f [v :vector-i64] :vector-i64 (vector-i64-from-bytes v))'),
        'utf8-wrong-type':('source','(ns invalid) (defn f [v :vector-i64] :string (string-from-utf8 v))'),
        'utf8-arity':('source','(ns invalid) (defn f [b :bytes] :string (string-from-utf8 b b))'),
        'compare-wrong-type':('source','(ns invalid) (defn f [s :string] :i64 (string-compare s 1))'),
        'compare-arity':('source','(ns invalid) (defn f [s :string] :i64 (string-compare s))'),
        'index-result-type':('source','(ns invalid) (defn f [s :string] :bool (string-index-of s s))'),
        'empty-arity':('source','(ns invalid) (defn f [] :bytes (bytes-empty 0))'),
        'count-result-type':('source','(ns invalid) (defn f [b :bytes] :string (bytes-count b))'),
        'at-index-type':('source','(ns invalid) (defn f [b :bytes] :i64 (bytes-at b "0"))'),
        'slice-end-type':('source','(ns invalid) (defn f [b :bytes] :bytes (bytes-slice b 0 true))'),
        'concat-right-type':('source','(ns invalid) (defn f [b :bytes v :vector-i64] :bytes (bytes-concat b v))'),
        'buffer-reserved-name':('reference',module([function('0','b',':bytes',':i64','bytes-count')])),
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
        'bytes-empty':('(bytes-count (bytes-empty))',0),
        'bytes-binary':('(let [v [0 127 128 255] b (bytes-from-vector-i64 v)] (if (and (= (bytes-count b) 4) (= (bytes-at b 0) 0) (= (bytes-at b 1) 127) (= (bytes-at b 2) 128) (= (bytes-at b 3) 255)) 42 9))',42),
        'bytes-roundtrip':('(let [b (bytes-from-vector-i64 [0 128 255]) v (vector-i64-from-bytes b)] (if (and (= (vector-count v) 3) (= (vector-at v 0) 0) (= (vector-at v 1) 128) (= (vector-at v 2) 255)) 42 9))',42),
        'bytes-slice':('(let [b (bytes-from-vector-i64 [0 19 23 255]) s (bytes-slice b 1 3)] (if (and (= (bytes-count s) 2) (= (bytes-at s 0) 19) (= (bytes-at s 1) 23) (= (bytes-at b 0) 0) (= (bytes-at b 3) 255)) 42 9))',42),
        'bytes-concat':('(let [b (bytes-from-vector-i64 [19]) c (bytes-from-vector-i64 [23]) d (bytes-concat b c)] (if (and (= (bytes-count b) 1) (= (bytes-count c) 1) (= (bytes-count d) 2)) (+ (bytes-at d 0) (bytes-at d 1)) 9))',42),
        'bytes-empty-slice':('(bytes-count (bytes-slice (bytes-from-vector-i64 [42]) 1 1))',0),
        'utf8-empty':('(string-byte-length (string-from-utf8 (bytes-empty)))',0),
        'utf8-ascii':('(let [s (string-from-utf8 (bytes-from-vector-i64 [97 98 99]))] (if (and (= s "abc") (= (string-byte-length s) 3)) 42 9))',42),
        'utf8-unicode':('(let [s (string-from-utf8 (bytes-from-vector-i64 [227 129 130]))] (if (and (= (string-byte-length s) 3) (= (string-code-point-at s 0) 12354)) 42 9))',42),
        'compare-order':('(if (> (string-compare "b" "a") 0) 42 7)',42),
        'compare-equal':('(string-compare "same" "same")',0),
        'compare-prefix':('(if (< (string-compare "a" "ab") 0) 42 7)',42),
        'index-match':('(if (= (string-index-of "abc" "b") 1) 42 9)',42),
        'index-missing':('(if (= (string-index-of "abc" "z") -1) 42 9)',42),
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
    # Preserve the existing runtime's explicit empty-needle refusal (<=nm0),
    # range checks and named UTF-8 guards, on both original source and KIR.
    refused_programs = {
        'index-empty':('(string-index-of "abc" "")', b':signal :SIGILL'),
        'byte-item-range':('(bytes-count (bytes-from-vector-i64 [256]))', b':bytes/item-out-of-range'),
        'byte-slice-range':('(bytes-count (bytes-slice (bytes-from-vector-i64 [42]) 0 2))', b':bytes/slice-bounds'),
        'utf8-truncated':('(string-byte-length (string-from-utf8 (bytes-from-vector-i64 [227 129])))', b':utf8/truncated'),
        'utf8-overlong':('(string-byte-length (string-from-utf8 (bytes-from-vector-i64 [192 128])))', b':utf8/overlong'),
    }
    for name,(body,reason) in refused_programs.items():
        text='(ns vector-refusal (:export [main])) (defn main [] :i64 '+body+')\n'
        src=out/('runtime-refuse-'+name+'.input');src.write_text(text)
        raw=run('serialize-refusal-'+name,[producer,'kir',src]).stdout
        source=build('runtime-refuse-'+name+'-source',text)
        kir=kir_image('runtime-refuse-'+name+'-kir',raw)
        messages=[]
        for lane,image in [('source',source),('kir',kir)]:
            result=run('runtime-refuse-'+name+'-'+lane,[image],120,execution_env={})
            assert not result.stdout and reason in result.stderr
            messages.append(result.stderr)
            report['runtimeRefusals'].append(dict(name=name,lane=lane,image=pin(image),exit=120,reason=reason.decode()))
        assert messages[0]==messages[1]
    mutations = [
        ('mutable-copy','HD-VECTOR-ASSOC-BANG "vector-assoc!"','HD-VECTOR-ASSOC-BANG "vector-assoc"','assoc!','mutable-alias',0),
        ('immutable-write','HD-VECTOR-ASSOC "vector-assoc"','HD-VECTOR-ASSOC "vector-assoc!"','assoc','immutable-alias',42),
        ('compare-as-index','HD-STRING-COMPARE "string-compare"','HD-STRING-COMPARE "string-index-of"','string-compare','compare-order',7),
        ('index-as-compare','HD-STRING-INDEX-OF "string-index-of"','HD-STRING-INDEX-OF "string-compare"','string-index-of','index-match',9),
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
        report['mutations'].append(dict(name=name,image=pin(image),guest=pin(guest),built=True,executed=True,cidMismatch=True,semanticsMismatch=True,aliasingMismatch=name in ['mutable-copy','immutable-write']))
    old='TY-BYTES ":bytes"'
    assert unity.count(old)==1
    image=build('mutant-bytes-type-erasure',unity.replace(old,'TY-BYTES ":vector-i64"'))
    result=run('detect-bytes-type-erasure',[image,'source',inputs['bytes-from-vector-i64']],1)
    assert not result.stdout and result.stderr.startswith(b'DSB:IDENTITY:')
    report['mutations'].append(dict(name='bytes-type-erasure',image=pin(image),built=True,executed=True,atomicFreshTypeRefusal=True))
    whole=out/'whole-compiler.input'
    whole.write_bytes(b''.join((ROOT/p).read_bytes()+b'\n' for p in full))
    assert pin(whole)==product['sourceUnity']
    result=run('whole-compiler-unbridged-refusal',[producer,'compiler',whole],1)
    assert not result.stdout and result.stderr.startswith(b'DSB:')
    report.update(status='PASS_NATIVE_SOURCE_VECTOR_OPERATIONS',matchedSourceKirCases=len(specs),
                  independentPayloadOracles=len(specs),atomicRefusals=len(negatives),
                  aliasingDistinguished=True,wholeInput=pin(whole),wholeCompilerRefusal=result.stderr.decode().strip())
    assert all(pin(ROOT/p)==v for p,v in {**report['modules'],**report['oracleModules'],**report['bufferOracleModules'],**report['executionCompilerModules']}.items())
    save();print(report['status'],flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.compiler.resolve(),a.output.resolve())
