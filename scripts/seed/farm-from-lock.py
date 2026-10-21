#!/usr/bin/env python3
"""scripts/seed/farm-from-lock.py <out-dir> [--lock deps-lock.edn] [--repos DIR] -- the selfbuild classpath farm from the
lock, with git alone (BOOTSTRAP-TOOL, JUN-202, 2026-10-21).

selfbuild-inputs.sh copied its classpath from a recorded snapshot (the seed17 scan farm). That snapshot is not durable;
the lock is. For every :lock/entries entry this extracts each listed path that is a source root ("src") at the entry's
:git-sha from a local clone (<repos>/<repo-name>, default ~/github/kotoba-lang, else ~/.gitlibs/_repos/...), with
`git archive`, into <out>/cp/<repo-name>/src, and writes:
  <out>/cp.txt       the classpath (one ':'-joined line of the src roots, lock order)
  <out>/farm.txt     provenance: coordinate, sha, extracted file count, tree sha256 of the extracted files
Fails closed on a missing clone or commit: no network, no JVM, no node, no fallback to another revision."""
import hashlib, os, re, subprocess, sys
args = sys.argv[1:]
if not args: sys.exit(__doc__)
out = os.path.abspath(args[0]); lock = 'deps-lock.edn'; repos = os.path.expanduser('~/github/kotoba-lang')
i = 1
while i < len(args):
    if args[i] == '--lock': lock = args[i+1]; i += 2
    elif args[i] == '--repos': repos = os.path.expanduser(args[i+1]); i += 2
    else: sys.exit('unknown option ' + args[i])
text = open(lock).read()
entries = re.findall(r'\{:coordinate "([^"]+)"\s+:git-url "([^"]+)"\s+:git-sha "([0-9a-f]{40})"\s+:paths \[([^\]]*)\]', text)
if not entries: sys.exit('no lock entries read from ' + lock)
os.makedirs(out + '/cp', exist_ok=True)
roots = []; prov = []
for coord, url, sha, paths in entries:
    name = url.rstrip('/').split('/')[-1].removesuffix('.git')
    cands = [os.path.join(repos, name), os.path.expanduser('~/.gitlibs/_repos/https/github.com/kotoba-lang/' + name)]
    repo = next((c for c in cands if os.path.exists(c) and subprocess.run(['git', '-C', c, 'cat-file', '-e', sha + '^{commit}'], capture_output=True).returncode == 0), None)
    if repo is None: sys.exit(f'farm-from-lock: FAIL: {coord} {sha[:8]}: no local clone has the commit ({cands})')
    for p in re.findall(r'"([^"]+)"', paths):
        if p != 'src': continue
        dest = os.path.join(out, 'cp', name)
        os.makedirs(dest, exist_ok=True)
        has = subprocess.run(['git', '-C', repo, 'cat-file', '-e', f'{sha}:{p}'], capture_output=True).returncode == 0
        if not has: continue
        arch = subprocess.run(['git', '-C', repo, 'archive', sha, p], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', dest], input=arch, check=True)
        files = sorted(os.path.relpath(os.path.join(d, f), dest) for d, _, fs in os.walk(os.path.join(dest, p)) for f in fs)
        h = hashlib.sha256()
        for f in files: h.update(f.encode() + b'\0' + hashlib.sha256(open(os.path.join(dest, f), 'rb').read()).digest())
        roots.append(os.path.join(dest, p))
        prov.append(f'{coord} {sha} {p} files {len(files)} tree-sha256 {h.hexdigest()}')
open(out + '/cp.txt', 'w').write(':'.join(roots) + '\n')
open(out + '/farm.txt', 'w').write('\n'.join(prov) + '\n')
print(f'farm-from-lock: {len(roots)} src roots from {len(entries)} lock entries -> {out}/cp.txt')
