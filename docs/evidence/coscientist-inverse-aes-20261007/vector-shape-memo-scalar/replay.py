"""External reader, source-only: hermetic offline replay of the fixed scalar archive."""
from pathlib import Path
import json,hashlib,sys,sysconfig,os

def main():
 sys.dont_write_bytecode=True
 W=Path(sys.argv[1]).resolve(strict=True)
 assert W.is_dir() and not W.is_symlink()
 stdlib=Path(sysconfig.get_path('stdlib')).resolve()
 def read_guard(event,args):
  if event!='open':return
  path,mode,flags=args
  if isinstance(path,int):
   assert path in (0,1,2),'unexpected file descriptor'
   return
  p=Path(os.fsdecode(path)).resolve()
  assert not isinstance(mode,str) or not any(c in mode for c in 'wax+'),'offline writes denied'
  assert not flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_APPEND|os.O_TRUNC),'offline write flags denied'
  allowed=p.is_relative_to(W) or (p.is_relative_to(stdlib) and not any(c in p.parts for c in ('site-packages','dist-packages')))
  assert allowed,('outside extracted evidence/stdlib',str(p))
 sys.addaudithook(read_guard)
 manifest=json.loads((W/'manifest.json').read_text())
 assert manifest['rawCap']==33554432 and manifest['compressedCap']==4194304
 size=0
 for row in manifest['files']:
  rel=Path(row['relativePath']);assert not rel.is_absolute() and '..' not in rel.parts
  p=W/rel;assert p.is_file() and not p.is_symlink()
  b=p.read_bytes();size+=len(b)
  assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
 assert size<=33554432
 A='vector-shape-memo-native-controls-v3';C='vector-shape-memo-native-controls-validator-v4'
 rows=json.loads((W/C/'attempts.json').read_text());prior=json.loads((W/A/'attempts.json').read_text())
 assert len(rows)==25 and rows[:3]==prior and len(prior)==3
 frozen_prefix='/Users/junkawasaki/github/workspaces/codex/'
 def normalize(arg):
  if not arg.startswith('/'):return arg
  assert arg.startswith(frozen_prefix),('unregistered argv absolute prefix',arg)
  rel=arg[len(frozen_prefix):];assert rel and '..' not in Path(rel).parts
  return rel
 loader=A+'/kexe-loader';producer=A+'/producer.bin';image=A+'/controls.bin'
 offset=int((W/A/'controls.offset').read_text());assert offset==0
 basego=json.loads((W/C/'parent-baseline-go.json').read_text())
 assert normalize(basego['baselineImage'])==producer and basego['baselineOffset']==0
 assert basego['baselineSourceKernelSHA256']=='d1b628a3cfc3cc6c250936a0e75ba5bcd1758633da59f2ec73e38a5986e652ac'
 prefix=lambda im:[loader,im,'0','0','aarch64','35,37,38,39','--']
 expected=[('controls-compile',prefix(producer)+['compile',A+'/unity-memo-controls.kotoba','--target','aarch64-macos','--output',A+'/controls.kseed'],1800),
           ('controls-extract',prefix(producer)+['extract-native',A+'/controls.kseed','--symbol','main','--output',A+'/controls.bin'],1800)]
 expected.extend((f'case-{c}',prefix(image)+['probe',str(c)],120) for c in range(21))
 expected.extend([('baseline-compile',prefix(producer)+['compile',C+'/fixture.kotoba','--target','aarch64-macos','--output',C+'/baseline.kseed'],1800),
                  ('baseline-extract',prefix(producer)+['extract-native',C+'/baseline.kseed','--symbol','bench','--output',C+'/baseline.bin'],1800)])
 for i,(row,(label,argv,seconds)) in enumerate(zip(rows,expected)):
  assert row['index']==i+1 and row['label']==label
  assert [normalize(x) for x in row['argv']]==argv,('exact argv',label)
  assert row['caps']=={'seconds':seconds,'vectorItems':134217728} and row['state']=='terminal' and row['returncode']==0
 # Existing audit semantics stay unchanged; suppress only archived report writes/print.
 p=W/'vector-shape-memo-scalar-actual-v8-controls/audit.py';source=p.read_text()
 old="(D/'report.json').write_text(json.dumps(report,indent=2)+'\\n')";assert source.count(old)==1
 source=source.replace(old,'REPLAY_REPORT=report',1)
 source=source[:source.index("print(json.dumps({'report':")]
 ns={'__file__':str(p),'__name__':'hermetic_offline_archive_replay'}
 exec(compile(source,str(p),'exec'),ns)
 r=ns['REPLAY_REPORT'];assert r['actualLoaderCalls']==25 and r['allStrictCases']==21
 print(json.dumps({'status':r['status'],'fullNormalizedArgvRows':25,'offlineRevalidatedCases':21,'nativeReplayCalls':0,'archivedReportsChanged':False,'outsideEvidenceReads':'DENIED exceptstdlib, no thirdparty','scalarPacketSelfhostBuildReplay':False,'producerProvenance':'Pinned V8 image hash and sibling source/build receipt, not rerun8build proof','positiveZeroCapture':'HOLD'},indent=2))

if __name__=='__main__':main()
