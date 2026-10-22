import pathlib,json,hashlib,importlib.util
W=pathlib.Path('/Users/junkawasaki/github/workspaces/codex');D=pathlib.Path(__file__).resolve().parent
V=W/'vector-masked32-on-clone-observer-offline-validator-v4-controls/validate.py'
s=importlib.util.spec_from_file_location('observer_inert_parser',V);v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
inputs=[V];out=[]
for name,folder,clones in [('nettle-aes','vector-masked32-on-clone-observer-plan-v2-native-controls',range(77,80)),('nettle-sha256','vector-masked32-on-clone-observer-remaining3-plan-v2-width',range(33,43))]:
 raw=W/folder/'run-outputs'/f'{name}-compile.stdout';src=raw.parent/f'{name}.kotoba';inputs += [raw,src]
 phases,calls=v.parse(raw.read_bytes());fr={r[0]:r[1:]for r in phases[4]['FREC']};code={r[0]:r[1]for r in phases[4]['CODE']};sir={r[0]:r[1:]for r in phases[2]['SIR']}
 rows=[]
 for fn in clones:
  f=fr[fn];start=f[13];end=min([r[13] for r in fr.values() if r[13]>start] or [phases[4]['header'][4]])
  words=[code[i]for i in range(start,end)];assert len(words)==25
  assert words[:13]==[0xa9bf7bfd,0x910003fd,0xd10143ff,0xf90003f3,0xf90027e7,0xaa0003f3,0xf9001fe1,0xf94004f0,0xf1000610,0x54000042,0xd4200000,0xf90004f0,words[12]]
  assert words[14:]==[0xaa0a0129,0xaa0903e0,0xf94027e7,0xd3407c00,0xaa0003e9,0xaa0903e0,0xf94003f3,0x910003bf,0xa8c17bfd,0xd65f03c0,0xd4200020]
  edges=[{'sir':i,'owner':next(n for n,f0 in fr.items()if f0[12]<i and next((j for j in range(f0[12]+1,phases[2]['header'][2])if sir[j][0]==2),phases[2]['header'][2])>i)}for i,r in sir.items()if r[0]==13 and r[1]==fn]
  rows.append({'function':fn,'codeStartIndex':start,'codeEndIndex':end,'frameBytes':80,'wordHex':[f'{x:08x}'for x in words], 'successInstructionsThroughRET':23,'arithmeticWords':4,'entryFuelWords':5,'staticJoinedCalls':edges})
 out.append({'workload':name,'clones':rows,'staticCloneCallSites':sum(len(r['staticJoinedCalls'])for r in rows),'runtimeProfile':False})
for p in [W/'vector-masked32-shift-orr-emitter-source-v1-native-controls/unity-sr-on.kotoba',W/'vector-masked32-shift-orr-emitter-source-v1-native-controls/helpers.kotoba',W/'vector-masked32-shift-orr-emitter-source-v1-native-controls/source-pins.json'] :inputs.append(p)
pins={str(p):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in inputs}
(D/'census.json').write_text(json.dumps(out,indent=2)+'\n');(D/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
