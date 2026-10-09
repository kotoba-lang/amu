"""Inert reviewed bootstrap SOURCE. Five fixed Clang commands, one build, zero guests."""
from pathlib import Path
import json, hashlib, stat, os, re, shlex, struct
D = Path(__file__).resolve().parent

def need(v, message):
    if not v:
        raise AssertionError(message)

def load(p):
    return json.loads(Path(p).read_bytes())

def receipt(p, maximum=402653184):
    p = Path(p); a = p.lstat()
    need(stat.S_ISREG(a.st_mode) and not p.is_symlink() and 0 <= a.st_size <= maximum, 'bounded regular')
    b = p.read_bytes(); z = p.lstat()
    need((a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns) == (z.st_dev, z.st_ino, z.st_size, z.st_mtime_ns), 'stable bytes')
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def pin(p, r):
    need(receipt(p) == {k: r[k] for k in ['bytes', 'sha256']}, 'exact pin: ' + str(p))

def save(p, v):
    b = (json.dumps(v, indent=2) + '\n').encode(); need(len(b) <= 8388608, 'bounded metadata')
    q = Path(str(p) + '.pending')
    with q.open('wb', buffering=0) as f:
        view = memoryview(b)
        while view:
            n = f.write(view); need(type(n) is int and 0 < n <= len(view), 'metadata write'); view = view[n:]
        os.fsync(f.fileno())
    os.replace(q, p)

def scope(pr, ip):
    need(type(pr['exactInputFiles']) is int and type(pr['exactInputLogicalBytes']) is int and len(ip) == pr['exactInputFiles'] <= 128 and sum(r['bytes'] for r in ip.values()) == pr['exactInputLogicalBytes'] <= 536870912 and pr['maximumInputLogicalBytes']==536870912, 'exact input registry')
    need(pr['maximumChildCalls'] == 5 and pr['maximumClangBuildCalls'] == 1 and pr['guestCalls'] == 0 and pr['C2'] is False, 'bootstrap only')
    need([c['label'] for c in pr['cases']] == ['version-before', 'dependencies', 'link-preview', 'build-loader', 'version-after'], 'exact ordered five')
    need(pr['source']['sha256'] == '04428f47af807fcb19342d035ce730f980f97c001747c806e059bbc4380c52b2', 'held-launch V5 C exact')
    c = pr['compiler']['path']; flags = ['-std=c11', '-O2', '-DKEXE_OWNERSHIP_DIAGNOSTIC_V3']
    build = [c, *flags, pr['source']['path'], '-o', str(Path(pr['outputRoot']) / 'kexe-loader'), '-lproc']
    expected = [[c, '--version'], [c, *flags, '-M', pr['source']['path']], build + ['-###'], build, [c, '--version']]
    need([x['argv'] for x in pr['cases']] == expected, 'fixed reviewed compile and query argv')
    subject=load(pr['subjectPreregistration']['path'])
    need(build==subject['prospectiveLoaderBuildArgv'] and pr['outputRoot']==str(Path(subject['loader']).parent) and pr['source']['path']==str(Path(pr['subjectPreregistration']['path']).parent/'kexe_loader_diagnostic.c'), 'exact V5 prospective build/source/output')
    need([x['timeoutSeconds'] for x in pr['cases']] == [30,60,30,180,30], 'fixed timeout budget')
    need(Path(pr['sdkAlias']).resolve(strict=True) == Path(pr['sdk']), 'live SDK alias binding')
    need(pr['environment']=={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/Users/junkawasaki','TMPDIR':pr['outputRoot'],'LANG':'C','LC_ALL':'C','TZ':'UTC','DEVELOPER_DIR':'/Library/Developer/CommandLineTools'},'exact build environment')
    need(pr['maximumCampaignSeconds'] == 480 and pr['cleanupSeconds'] == 30 and pr['maximumRawBytesPerStream'] == 1048576, 'bounded work')
    return True

def dependencies(raw, pr):
    need(len(raw) <= 1048576 and b'\x00' not in raw, 'bounded dependency bytes')
    text = raw.decode('ascii').replace('\\\n', ' ')
    need(text.count(':') == 1, 'single dependency target')
    names = text.split(':',1)[1].split(); need(0 < len(names) <= 4096 and len(names) == len(set(names)), 'finite dependency set')
    resolved = []
    for name in names:
        p = Path(name); need(p.is_absolute(), 'absolute dependency')
        p = p.resolve(strict=True)
        need(p == Path(pr['source']['path']) or p.is_relative_to(Path(pr['sdk'])) or p.is_relative_to(Path('/Library/Developer/CommandLineTools/usr/lib/clang')), 'dependency domain')
        resolved.append(str(p))
    need(len(resolved) == len(set(resolved)) and pr['source']['path'] in resolved, 'resolved aliases deduplicated and exact source present')
    return resolved

def preview(raw, pr, ip):
    need(0 < len(raw) <= 1048576 and b'\x00' not in raw, 'bounded preview')
    lines = raw.decode('utf-8').splitlines(); commands = [shlex.split(s) for s in lines if s.lstrip().startswith('"/')]
    need(len(commands) == 2 and commands[0][0] == pr['resolvedCompiler']['path'] and commands[1][0] == pr['linker']['path'], 'one compiler frontend and one pinned linker')
    need('-cc1' in commands[0] and '-isysroot' in commands[0] and '-syslibroot' in commands[1] and '-lSystem' in commands[1] and '-lproc' in commands[1], 'declared frontend and library contract')
    # Exact default SDK resolution is evidence-gated before any build.
    for command,flag in [(commands[0],'-isysroot'),(commands[1],'-syslibroot')]:
        need(command.count(flag)==1 and command.index(flag)+1<len(command), 'one explicit preview SDK')
        root=Path(command[command.index(flag)+1])
        need(str(root) in [pr['sdk'],pr['sdkAlias']] and root.resolve(strict=True)==Path(pr['sdk']), 'default SDK exact registered binding')
    need(commands[0].count('-resource-dir')==1 and commands[0][commands[0].index('-resource-dir')+1]==pr['compilerResourceDirectory'], 'pinned frontend resources')
    need(all(t in ['-lSystem','-lproc','-lto_library']for c in commands for t in c if t.startswith('-l'))and all('-framework'not in c for c in commands),'no unregistered linked library')
    for command in commands:
        for token in command:
            if not token.startswith('/'):
                continue
            p = Path(token)
            if token in ip or token in [pr['sdk'],pr['sdkAlias'],pr['compilerResourceDirectory']]:
                continue
            if p.is_relative_to(Path(pr['outputRoot'])) and (p.suffix in ['.o','.c'] or token == str(Path(pr['outputRoot'])/'kexe-loader')):
                continue
            need(False, 'unregistered absolute link/compiler input: ' + token)
    return commands

def bounded_diagnostic(raw):
    # Diagnostic evidence only; rc0 and exact whole artifact remain separate.
    need(type(raw)is bytes and len(raw)<=1048576 and b'\x00'not in raw, 'bounded diagnostic text')
    text=raw.decode('utf-8')
    need('error:'not in text and 'fatal error:'not in text, 'error diagnostic refuses')
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'nonempty':bool(raw),'interpretation':'bounded compiler diagnostic evidence only; clean-build not claimed'}

def main(go_path):
    import subprocess, time, sys
    gp = Path(go_path); g = load(gp); gr = receipt(gp); pr = load(D/'preregistration.json'); sp = load(D/'source-pins.json'); ip = load(D/'input-pins.json'); O = Path(pr['outputRoot']); rows = []; deps = {}; ok = False
    need(set(g) == {'status','sourcePinsSHA256','inputPinsSHA256','preregistrationSHA256','driverSHA256','sourceReviews','subjectReviews','maximumChildCalls','guestAuthorized','noRetry'}, 'exact GO')
    need(g['status'] == pr['rootGOStatus'] and g['maximumChildCalls'] == 5 and g['guestAuthorized'] is False and g['noRetry'] is True, 'one build only GO')
    for n,k in [('source-pins.json','sourcePinsSHA256'),('input-pins.json','inputPinsSHA256'),('preregistration.json','preregistrationSHA256'),('run.py','driverSHA256')]:
        need(receipt(D/n)['sha256'] == g[k], 'reviewed GO identity')
    for field,status in [('sourceReviews',pr['sourceReviewStatus']),('subjectReviews',pr['subjectReviewStatus'])]:
        need(len(g[field]) == 2 and len({r['path'] for r in g[field]}) == 2, 'two distinct exact reviews')
        for r in g[field]:
            pin(r['path'],r); q = load(r['path']); need(q['status'] == status, 'review status')
            need(q['sourcePinsSHA256'] == (g['sourcePinsSHA256'] if field == 'sourceReviews' else pr['subjectSourcePins']['sha256']), 'reviewed source identity')
            if field == 'sourceReviews':
                need(q['driverSHA256'] == g['driverSHA256'] and q['preregistrationSHA256'] == g['preregistrationSHA256'], 'build driver/prereg reviewed')
            else:
                need(q['driverSHA256']==pr['subjectDriver']['sha256'] and q['preregistrationSHA256']==pr['subjectPreregistration']['sha256'], 'exact V5 subject driver/prereg review')
    def guard():
        need(receipt(gp) == gr, 'immutable GO'); scope(pr,ip)
        for n,r in sp.items(): pin(D/n,r)
        for p,r in ip.items(): pin(p,r)
        for p,r in deps.items(): pin(p,r)
    guard(); need(not O.exists(), 'fresh fixed output namespace'); O.mkdir(); deadline = time.monotonic()+480
    try:
        for c in pr['cases']:
            guard(); need(time.monotonic()+c['timeoutSeconds']+30 <= deadline, 'original absolute campaign bound')
            r = dict(label=c['label'],argv=c['argv'],state='not-started',pid=None,returncode=None); rows.append(r); save(O/'attempts.json',rows)
            proc = None; out = O/(c['label']+'.stdout'); err = O/(c['label']+'.stderr'); safe = False; wait_entered = False
            with out.open('xb',buffering=0) as fo, err.open('xb',buffering=0) as fe:
                try:
                    proc = subprocess.Popen([pr['interpreter']['path'],str(D/'limit-exec.py'),c['label']],env=pr['environment'],cwd=O,stdin=subprocess.DEVNULL,stdout=fo,stderr=fe,close_fds=True)
                    r.update(pid=proc.pid,state='started'); save(O/'attempts.json',rows)
                    try:
                        wait_entered = True; r['waitEntered'] = True
                        rc = proc.wait(timeout=min(c['timeoutSeconds'],max(.001,deadline-time.monotonic())))
                    except subprocess.TimeoutExpired:
                        r['timeout'] = True
                        proc.kill()  # direct owned child, still unreaped; never any group operation
                        rc = proc.wait(timeout=min(30,max(.001,deadline-time.monotonic())))
                    r.update(returncode=rc,state='terminal'); safe = rc == 0 and not r.get('timeout'); need(safe,'first process failure; quarantine output, no retry')
                except BaseException:
                    if proc is not None and r['state'] == 'started':
                        if not wait_entered:
                            # Exact unreaped direct handle; metadata failure must still attempt cleanup.
                            try:
                                proc.kill(); r['waitEntered'] = True
                                rc = proc.wait(timeout=max(.001,min(30,deadline-time.monotonic())))
                                r.update(state='terminal',returncode=rc,failedBeforeWaitCleanup=True)
                            except BaseException as cleanup:
                                r.update(state='wait-uncertain-signal-authority-retired',cleanupError=repr(cleanup))
                        else:
                            # Arbitrary wait failure: retire all explicit signal/wait operations permanently.
                            r['state'] = 'wait-uncertain-signal-authority-retired'
                    try: save(O/'attempts.json',rows)
                    except BaseException: pass
                    raise
            need(safe, 'normal direct wait before hashing writers')
            r.update(stdout=receipt(out,1048576),stderr=receipt(err,1048576)); save(O/'attempts.json',rows)
            b = out.read_bytes(); e = err.read_bytes()
            if c['label'] == 'dependencies':
                r['diagnosticEvidence']=bounded_diagnostic(e); save(O/'attempts.json',rows); total = 0
                for p in dependencies(b,pr):
                    size = Path(p).stat().st_size; need(size <= 67108864-total, 'header budget before read'); total += size; deps[p] = receipt(p,67108864)
                save(O/'dependency-input-pins.json',deps)
            elif c['label'] == 'link-preview':
                need(b == b'', 'preview stdout empty'); save(O/'link-preview.json',preview(e,pr,ip))
            elif c['label'].startswith('version'):
                need(e == b'' and b.startswith(b'Apple clang version ') and len(b) <= 16384, 'actual compiler identity')
            else:
                need(b == b'', 'build stdout empty'); r['diagnosticEvidence']=bounded_diagnostic(e); save(O/'attempts.json',rows); loader=O/'kexe-loader'; raw=loader.read_bytes(); need(32<=len(raw)<=4194304 and raw[:4]==b'\xcf\xfa\xed\xfe' and struct.unpack_from('<I',raw,4)[0]==0x100000c and struct.unpack_from('<I',raw,12)[0]==2,'whole arm64 executable')
                save(O/'loader.json',dict(path=str(loader),**receipt(loader,4194304)))
            guard()
        need((O/'version-before.stdout').read_bytes()==(O/'version-after.stdout').read_bytes(),'same compiler identity before/after'); ok=True
    except BaseException as ex:
        save(O/'failure.json',dict(error=repr(ex),noRetry=True,childCalls=len(rows),rawOnFailedOrUncertainCallUnhashed=True)); raise
    finally:
        save(O/'terminal.json',dict(childCalls=len(rows),allDirectChildrenClosed=all(r['state']=='terminal'for r in rows),failure=not ok,descendantClosureUniversal=False))
    guard(); need(ok and len(rows)==5,'five normal closed tool calls')
    evidence={n:dict(path=str(O/n),**receipt(O/n))for n in ['attempts.json','terminal.json','dependency-input-pins.json','link-preview.json','loader.json']}
    save(O/'report.json',dict(status='COMPLETE_SOURCE_BOUND_HELD_LAUNCH_V5_LOADER_BUILD5_IDENTITY_ONLY',childCalls=5,buildCalls=1,guestCalls=0,source=pr['source'],compiler=pr['compiler'],sdk=pr['sdk'],rootGO=dict(path=str(gp),**gr),sourcePinsSHA256=g['sourcePinsSHA256'],loader=load(O/'loader.json'),evidence=evidence,sdkWholeTreeQualified=False,lifecycleFixtureQualified=False,functionalQualified=False,performanceQualified=False,cleanBuildDiagnosticsQualified=False,C2=False))

if __name__ == '__main__':
    import sys
    need(len(sys.argv)==2,'one exact root GO'); main(sys.argv[1])
