"""Native translated ports, public official driver/formula; no private source build."""
from pathlib import Path
import json,hashlib,subprocess,os,sys,platform,statistics,math,shlex,re
def global_idle(exclude_ancestors=False):
 q=subprocess.run(['/bin/ps','-axo','pid=,ppid=,command='],capture_output=True,text=True,check=True)
 parsed=[]
 for line in q.stdout.splitlines():
  m=re.match(r'\s*(\d+)\s+(\d+)\s+(.*)',line)
  if m:parsed.append(dict(pid=int(m[1]),ppid=int(m[2]),command=m[3]))
 own=os.getpid();ancestors=set();byid={r['pid']:r for r in parsed};p=byid.get(own,{}).get('ppid',0)
 while p in byid and p not in ancestors:
  ancestors.add(p);p=byid[p]['ppid']
 watched=[]
 pattern=re.compile(r'/Users/joseph/github/workspaces/codex/embench-picojpeg-edn-20261009|/Users/joseph/github/workspaces/codex/seed-logical-immediate|/Users/joseph/github/workspaces/codex/seed-logical-immediate|/Users/joseph/github/workspaces/codex/seed-logical-immediate|/(?:timer(?:s)?(?:\s|/|$)|kexe-loader(?:\s|$)|(?:one-controller|confirm-controller)\.py(?:\s|$)|ablate\.py(?:\s|$)|(?:campaign[^ /]*|run_trigger)\.py(?:\s|$))')
 active=re.compile(r'/(?:OFF|ON)/timer(?:\s|$)|/(?:one-controller|confirm-controller|ablate|(?:campaign[^ /]*|run_trigger))\.py(?:\s|$)')
 for row in parsed:
  if row['pid']==own:continue
  # Exclude only an actual ancestor invoking this exact script with no
  # additional command. macOS login wrappers are explicitly recognized.
  if row['pid'] in ancestors:
   ownscript=str(Path(__file__).resolve())
   try: argv=shlex.split(row['command'])
   except ValueError: argv=[]
   shellnames=['/bin/zsh','/bin/sh','/bin/bash','/bin/dash']
   tail=None
   if len(argv)>=3 and argv[0] in shellnames and argv[1]=='-c': tail=argv[2:]
   elif argv and argv[0]=='/usr/bin/login':
    # Only the login's real shell invocation suffix can qualify.
    positions=[i for i,x in enumerate(argv) if x in shellnames]
    if len(positions)==1:
     i=positions[0]
     if i+2<len(argv) and argv[i+1]=='-c': tail=argv[i+2:]
   if tail is not None:
    if len(tail)==1:
     try: tail=shlex.split(tail[0])
     except ValueError: tail=[]
    if tail==['python3',ownscript]:continue
  if pattern.search(row['command']):watched.append(row)
 return watched


W=Path(__file__).resolve().parent;A=json.loads((W/'workloads.json').read_text());O=W/'results';MULT={e['workload']:e['multiplier'] for e in A};assert all(m in (1,2,4,8,16) for m in MULT.values())
globalPreflight=global_idle();assert globalPreflight==[],globalPreflight
custody=json.loads((W/'custody-receipt.json').read_text());assert custody['status']=='PASS_EXACT_PUBLIC_ARCHIVE_FILES_AND_GLOBAL_IDLE' and custody['root']==str(W) and custody['GSF']==8192 and custody['ownedRows']==[]
assert custody['files']==140 and custody['members']==141
O.mkdir(exist_ok=False)
(O/'global-preflight.json').write_text(json.dumps(dict(status='PASS_GLOBAL_PROCESS_IDLE',ownedRows=globalPreflight),indent=2)+'\n')
report=dict(status='building-native-C-timers',label='translated Kotoba port / official Embench speed formula and driver',officialUnmodifiedCScore=False,GSF=8192,host=platform.node(),clock='CLOCK_MONOTONIC_RAW',warmupBodies=1,resetOutsideTiming=True,representationAllocationInsideTiming=True,fuel=34359738368,CPUSeconds=1800,wallSeconds=1800,preAdmission=dict(probeSeconds=1,requiredConsecutive=1,rawIdleMinimumPercent=70,loadInformationalOnly=True,perAttemptWaitMaximumSeconds=60,campaignWaitBudgetSeconds=120,outsideTimedInvocation=True),postAdmissionCPUIdleMinimumPercent=70,postRawCPUIdleMinimumPercent=70,loadInformationalOnly=True,samplesPerWorkload=1,maxActualAttemptsPerWorkload=3,noRetry=False,cpuOnlyRetries=True,noAdaptiveRetry=True,selectionPolicy="FIRST_CPU_QUALIFIED_NOT_FASTEST",sourceCommit="a9edc1f0d5021efabf6864e70c5b92d59257f348",adoptedProduct=None,candidateProduct="m104-same-algorithm-a9edc1f0d5021efabf6864e70c5b92d59257f348",candidateAdopted=False,CReferenceSameHost=None,referencePolicy="fresh same-cycle C114 only; old Stat60 exploratory timing excluded",exploratory=True,performanceGoalAchieved=False,builds=[])
def save():(O/'report.json').write_text(json.dumps(report,indent=2)+'\n')
report.update(protocolRevision="PROTOCOL REVISION (user-approved; record it verbatim in the round's receipts):\n- Each Kotoba workload w runs n_w = LSF_w · 8192 · m_w iterations, with m_w ∈ {1,2,4,8,16}. Reported ratio_w = (4/m_w) · K_ns / C_ns. The full-19 GM is over those ratios.\n- m_w is fixed BEFORE transfer from local data only, never adjusted after any Joseph timing. Write it into a pre-registration receipt (hashed) in s3. Rule: m_w = the smallest power of two such that the projected Joseph interval ≥ 1.0 s, using the conservative Joseph/local ratio 0.33 (local_elapsed · m_w · 0.33 ≥ 1.0 s), subject to fuel: (benchmarkFuel + verifyFuel)(n_w) must stay well under 2^35 (≤ ~0.9 · 2^35). If fuel binds, take the largest feasible m_w and report the projection.\n- Unchanged: the C arm (GSF 32768, frozen round65 binaries); the 0.5 s floor; fuel 2^35; the trusted loader; warm1/sample1; ≤3 CPU-only retries; first qualified; no subset GM.\n- Arena caps (KEXE_* env): raise only where the new n needs it (e.g. qrduino KEXE_PAIRS 65536 vs 40960·m pairs, slre pairs, aha vectors), and record every change.\n- Expected exactness values (benchmarkFuel, verifyFuel, result, the 17-counter arena line) must be re-derived for each new n from a TRUSTED reference, never from the candidate m92 itself. Use the same method that produced expected-original-accounting.json, or something at least as independent. If fuel/arena are exactly linear in n, show it from ≥2 reference n values per workload. Tell me what reference you used.\n- Add the local short-interval screen to s3: refuse to transfer if any workload's projected Joseph interval at its m_w is < 0.75 s.\n\nPROTOCOL AMENDMENT 1 (coordinator decision, before any pre-registration; replaces the local-wall-time projection, the 0.33 ratio and the 0.75 s screen):\n1) LOCAL IDLE GATE: drop it for pre-registration. This machine carries persistent unrelated load (java pid 73536, hermes, Codex, node), which I'm not allowed to kill, so ≥70% idle may never happen. Local wall time under load is meaningless anyway. Use a deterministic, load-independent projection instead.\nP_w(m) = I_w · m / R_w, where:\n- I_w = the candidate's instruction count for w at m=1 (local, deterministic: the instr= values your s3/validate runs record);\n- R_w = the FASTEST Joseph instructions-per-second observed for w in any previous round (m43 17 workloads, m87 6 incl. matmult's short attempt). Use the instruction count of that exact prior image (recount locally if needed);\n- if w has no prior Joseph data, R_w = 30e9 instr/s.\nFastest R gives the shortest projection, so the rule is conservative for the floor. Calibration comes only from earlier rounds, never from this round, so pre-registration stays clean. Record the R_w table and its sources in the pre-registration receipt.\n2) SELECTION AND SCREEN (replaces my 0.33-ratio and 0.75 s rules):\n- m_w = the smallest power of two in {1,2,4,8,16} with P_w(m_w) ≥ 1.0 s, capped by fuel ≤ 0.9·2^35.\n- Retime rule: if (image, n_w) was already timed on Joseph (aha-mont64, crc32 and matmult-int at m=1 in m87), take the next feasible power of two instead. That makes aha-mont64 m ≥ 2 and needs its KEXE_VECTORS/VECTOR_ITEMS caps doubled; record it.\n- Screen: refuse transfer if any P_w(m_w) < 0.6 s.\n- Example: matmult-int at m=8 projects 1.49e9·8/12.4e9 ≈ 0.96 s using its identical m87 image's own Joseph rate.\n\nPROTOCOL AMENDMENT 2 (coordinator decision, before any m93 pre-registration and before any Joseph timing of this round):\nR_w DECISION: NARROW, i.e. m43 accepted (17) + m87 executed (6). That is what my parenthetical and example specified; the broad reading was my wording's fault, not yours.\n- Record it as Amendment 2, verbatim, and keep the broad pre-registration 91e3daad… on record as superseded. No Joseph timing has happened since, so m_w is still fixed from local data only.\n- Workloads with no narrow-set data use R = 30e9.\n\nPROTOCOL AMENDMENT 3 and changes for the corrected same-algorithm-only round (user-approved, 15 Oct 2026):\n- Amendment 3 (user decision, 15 Oct): an image byte-identical to one already timed may be timed again as part of a complete, pre-registered new round with fresh C. aha-mont64 can only run at m=1 because of the loader vector cap, and its image is identical to m93's. Disclose every identical (image, n_w) pair and report both timings as a noise check. crc32 is identical too but can move to m=2, so use m=2 there; apply the rule only where m is forced.\n- Screen: raise the projection floor to 0.85 s, per your caveat. R_w calibration: the fastest prior Joseph rate from m43, m87 and m93. The m93 round now gives all 19 workloads.\n- Expected values re-derived from the trusted references at each n_w, as before.\n- Load gate, retries and first-qualified rules unchanged; fresh C in the same round.\n\nPROTOCOL AMENDMENT 4 (coordinator decision before any timing of this round; the 0.85 s screen was a coordinator margin, not a user rule):\nDecision: option (a).\n- A workload at its maximum feasible m (fuel or loader ceiling) is accepted if its projection is ≥ 0.6 s.\n- All others still need ≥ 0.85 s.\n- Disclose it in the summary with matmult-int's projection of 0.78 s and its m93 interval of 0.777 s.\n",preregistrationSHA256='edda4577fc3d46b04466525fc3dce28d43807e17ed237bb08eb368af924b89ea',multipliers=MULT,iterations='n_w=LSF_w*8192*m_w',kotobaScoreFormula='baseline/(K_ns/1e6)*8192*m_w',ratioFormula='(4/m_w)*K_ns/C_ns')
try:
 for e in A:
  n=e['workload'];d=W/'timers'/n;native=d/'image.bin';assert hashlib.sha256(native.read_bytes()).hexdigest()==e['nativeSHA256']
  h=d/'timing-packet-generated.h';s=h.read_text();start=s.index('#define TIMING_NATIVE_PATH ');end=s.index('\n',start);s=s[:start]+'#define TIMING_NATIVE_PATH '+json.dumps(str(native))+s[end:];h.write_text(s)
  cmd=['/usr/bin/clang','-std=c11','-O2',str(d/'separated-loader.c'),'-o',str(d/'timer')];q=subprocess.run(cmd,capture_output=True,text=True);report['builds'].append(dict(workload=n,argv=cmd,exit=q.returncode,stderr=q.stderr));save();assert q.returncode==0
  caps=dict(KEXE_FUEL='34359738368',KEXE_STRUCTURED_REPORT='1',KEXE_ARENA_USE='1',KEXE_CPU_SECONDS='1800',KEXE_WALL_SECONDS='1800')
  if n=='aha-mont64':caps.update(KEXE_VECTORS='67108864',KEXE_VECTOR_ITEMS='134217728')
  if n=='qrduino':caps.update(KEXE_PAIRS='65536')
  if n=='slre':caps.update(KEXE_PAIRS='8388608')
  caps.update(e['extraCaps'])
  b=O/'measured/src'/n;b.mkdir(parents=True);f=b/n;f.write_text('#!/bin/sh\nexec env '+ ' '.join(shlex.quote(k+'='+v) for k,v in caps.items())+' '+shlex.quote(str(d/'timer'))+' '+str(e['LSF']*8192*e['multiplier'])+'\n');f.chmod(0o755)
 cmd=[sys.executable,str(W/'upstream/benchmark_speed.py'),'--builddir',str(O/'measured'),'--logdir',str(O/'official-logs'),'--target-module','run_trigger','--gsf','8192','--json-output','--samples','1'];report.update(status='measuring',driverCommand=cmd);save()
 env=dict(os.environ,PYTHONPATH=str(W));q=subprocess.run(cmd,env=env,cwd=W/'upstream',capture_output=True,text=True);(O/'official.stdout').write_text(q.stdout);(O/'official.stderr').write_text(q.stderr);report['driverExit']=q.returncode
 raw={e['workload']:json.loads((O/'measured/raw'/(e['workload']+'.json')).read_text()) for e in A};missing=[n for n,r in raw.items() if not r['complete']];report.update(incomplete=missing,full19=not missing)
 if not missing and q.returncode==0:
  baseline=json.loads((W/'upstream/baseline-data/speed.json').read_text());ratios={n:baseline[n]/(statistics.median(s['elapsedNs'] for s in r['samples'] if s['accepted'])/1e6)*8192*MULT[n] for n,r in raw.items()};report.update(status='COMPLETE_EXPLORATORY_TRANSLATED_PORT_DRIVER_FORMULA',relativeSpeeds=ratios,speedGeometricMean=math.exp(statistics.mean(map(math.log,ratios.values()))))
 else:report.update(status='REFUSED_INCOMPLETE_TRANSLATED_SUITE',speedGeometricMean=None)
 print(report['status'],report.get('speedGeometricMean'),flush=True)
except BaseException as ex:report.update(status='FAILED',failure=repr(ex));raise
finally:
 save()
 closure=global_idle();assert closure==[],closure
 (O/'global-closure.json').write_text(json.dumps(dict(status='PASS_GLOBAL_NO_OWNED_BENCHMARK_PROCESS',ownedRows=closure),indent=2)+'\n')
