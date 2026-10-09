"""Saved-data offline controls only. No producer/native/process/setter calls."""
from pathlib import Path
import json,hashlib,struct,ast
D=Path(__file__).resolve().parent;W=D.parent;B=W/'crc-table-decision-collapse-tc-emitted-build8-source-v1-20261008';C=W/'crc-table-decision-collapse-native-component-v4-portable-env-20261008'
for p in D.glob('*.py'):ast.parse(p.read_text())
ns={'__file__':str(D/'validate.py'),'__name__':'offline_saved_emission_source_controls'};exec(compile((D/'validate.py').read_bytes(),str(D/'validate.py'),'exec'),ns)
raw=(B/'run-outputs/observed-on-input-compile.stdout').read_bytes();blob=(B/'run-outputs/observed-on-input.kseed').read_bytes();end=blob.index(b'\n\n');header=blob[:end].splitlines();payload=blob[end+2:];exports=[(z[0].decode(),int(z[1]),int(z[2]))for row in header[1:]for z in [row.split()]]
source=(B/'original-input.kotoba').read_bytes();base=json.loads((C/'run-outputs/typed-binding.json').read_bytes())
result=ns['verify'](raw,payload,exports,source,base);assert result['actualEmission']['sourceRegister']==24 and result['actualEmission']['rawSreg']==25 and result['actualEmission']['destinationRegister']==9
assert blob==(B/'run-outputs/on-input.kseed').read_bytes()and payload==(B/'run-outputs/on-input.bin').read_bytes()
controls=[]
def reject(name,r,p=payload):
 try:ns['verify'](r,p,exports,source,base)
 except (AssertionError,KeyError,ValueError):controls.append({'name':name,'rejected':True})
 else:raise AssertionError(name)
def word(name,at,v):
 old=struct.unpack_from('<I',payload,(at-1)*4)[0];needle=f'FCODE {at} {old}\n'.encode();assert raw.count(needle)==1
 p=bytearray(payload);struct.pack_into('<I',p,(at-1)*4,v)
 reject(name,raw.replace(needle,f'FCODE {at} {v}\n'.encode(),1),bytes(p))
word('treat raw25 as x25 incorrectly',244,0xaa1903e0)
word('wrong capture x23',244,0xaa1703e0)
word('wrong result x8',256,0xaa0003e8)
word('charge removed',246,0xd503201f)
word('exhaustion zero-store replaced',248,0xf90004e8)
word('wrong table stride',251,0x8b000a31)
word('narrow32 read',254,0xb8706a20)
word('success fuel publication removed',255,0xd503201f)
reject('missing emitter',raw.replace(next(x for x in raw.splitlines(keepends=True)if x.startswith(b'TCEMIT ')),b'',1))
reject('duplicate emitter',raw+next(x for x in raw.splitlines(keepends=True)if x.startswith(b'TCEMIT ')))
reject('wrong captured slot',raw.replace(b'TCG 220 0 31 7\n',b'TCG 220 0 31 6\n',1))
reject('wrong raw sreg',raw.replace(b'TCG 220 0 23 25\n',b'TCG 220 0 23 26\n',1))
reject('missing descriptor record',raw.replace(b'TCG 220 1 37 0\n',b'',1))
reject('wrong nonleaf frame',raw.replace(b'TCG 220 0 3 176\n',b'TCG 220 0 3 0\n',1))
reject('wrong TC transaction count',raw.replace(b'TCEMIT 220 1 0 1 256 244 257 49 50 10 23 1 2 0',b'TCEMIT 220 1 0 1 256 244 257 49 50 10 22 1 2 0',1))
roles=[]
names=['leaf','has-fuel','callee-saved-count','frame-bytes','local-slot-count','temp-depth','live-height','x7-context','descriptor-cache-mode','dead','skip','x8-fuel-register','outgoing-area-bytes','descriptor-slot-witness','reserved14','reserved15']
actual_rows=result['allRawRecords']['TCG'];old_rows=base['allRawRecords']['TCG']
for k in range(38):
 role=names[k]if k<16 else ('raw-slot-register-plus-one-'+str(k-16)if k<24 else('temp-descriptor-kind-'+str(k-24)if k<31 else'temp-descriptor-value-'+str(k-31)))
 a=[r[3]for r in actual_rows if r[0]==220 and r[2]==k];o=[r[3]for r in old_rows if r[0]==220 and r[2]==k];assert a==o and len(a)==2
 roles.append({'k':k,'role':role,'OFFBeforeAfter':o,'ONBeforeAfter':a,'comparison':'exact-both-phases-no-field-exclusions'})
q={'status':'PASS_FINITE_SAVED_RAW_SOURCE_REPAIR_CONTROLS_ONLY','actualSavedPositive':True,'notNewOperationalExecution':True,'emission':result['actualEmission'],'full38RolePairs':roles,'negativeMutations':controls,'sourceFaultControlsModifySavedModelOnly':True,'oldFailurePreserved':True,'doesNotCompleteOriginalBuild8':True,'observedNativeExtractionNotExecuted':True,'nativeCompilerGuestSettersProcessAPICalls':0}
(D/'source-controls.json').write_text(json.dumps(q,indent=2)+'\n')
