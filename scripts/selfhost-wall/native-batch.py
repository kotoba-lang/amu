#!/usr/bin/env python3
"""native-batch.py -- run a native text->text guest (a `main` that reads every case line on :io/read and writes one answer
line per case) over a case file, ONE LOADER PROCESS PER BATCH, so every arena is reclaimed between batches (the H-M3
process-per-pass idea applied to differential cases). BOOTSTRAP-TOOL (python3 harness; the guest itself runs only under
tools/kexe_loader.c). Agent FRONT, 2026-10-03.

  native-batch.py <loader> <guest.bin> <offset> <cases.txt> <answers.txt> [batch=200]

A batch that traps (or answers a different number of lines) is split in halves down to single cases; a single case that
still traps is answered `TRAP <trap line>`. Env: NB_GRANT (default 3,37,41), NB_ENV ("K=V .." loader budget overrides),
NB_MARKS (file: one tsv line per successful process: cases, pairs, vectors, vector-items, heap-bytes, string-pool-bytes,
rss-bytes, user-s). Prints a summary on stderr: processes, traps, peak marks, wall seconds.
"""
import os, re, subprocess, sys, time

loader, binf, off, casef, outf = sys.argv[1:6]
batch = int(sys.argv[6]) if len(sys.argv) > 6 else 200
grant = os.environ.get('NB_GRANT', '3,37,41')
base = dict(os.environ, KEXE_COMMAND='1', KEXE_ARENA_USE='1', KEXE_STRING_POOL='1073741824', KEXE_PAIRS='67108864',
            KEXE_VECTORS='4194304', KEXE_VECTOR_ITEMS='134217728', KEXE_CPU_SECONDS='600', KEXE_WALL_SECONDS='600')
for kv in os.environ.get('NB_ENV', '').split():
    k, v = kv.split('=', 1); base[k] = v
marks_f = open(os.environ['NB_MARKS'], 'w') if os.environ.get('NB_MARKS') else None
lines = [l for l in open(casef, encoding='utf-8').read().split('\n') if l.strip()]
peak = {}; procs = 0; traps = 0; t0 = time.time()


def mark(err, key):
    m = re.search(r':' + key + r' (\d+)', err)
    return int(m.group(1)) if m else 0


def run(ls):
    global procs
    procs += 1
    p = subprocess.run(['/usr/bin/time', '-l', loader, binf, off, '0', 'aarch64', grant],
                       input=('\n'.join(ls) + '\n').encode(), capture_output=True, env=base)
    out = p.stdout.decode('utf-8', 'replace').split('\n')
    if out and out[-1] == '':
        out = out[:-1]
    err = p.stderr.decode('utf-8', 'replace')
    trap = re.search(r'KEXE_TRAP[^\n]*', err)
    return out, err, (trap.group(0) if trap else None)


def solve(ls):
    global traps
    out, err, trap = run(ls)
    if trap is None and len(out) == len(ls):
        m = [mark(err, k) for k in ('pairs', 'vectors', 'vector-items', 'heap-bytes', 'string-pool-bytes')]
        rss = re.search(r'(\d+)\s+maximum resident set size', err)
        usr = re.search(r'([\d.]+) real\s+([\d.]+) user', err)
        m += [int(rss.group(1)) if rss else 0, float(usr.group(2)) if usr else 0.0]
        for k, v in zip(('pairs', 'vectors', 'vector-items', 'heap-bytes', 'string-pool-bytes', 'rss', 'user'), m):
            peak[k] = max(peak.get(k, 0), v)
        if marks_f:
            marks_f.write('\t'.join(str(x) for x in [len(ls)] + m) + '\n')
        return out
    if len(ls) == 1 and trap is None and out:
        # one case, no trap, several lines: the guest printed a newline inside its answer (an unescaped string);
        # keep the answer on one line
        return ['\\n'.join(out)]
    if len(ls) == 1:
        traps += 1
        return ['TRAP ' + (trap or ('answered %d lines' % len(out)))[:200]]
    h = len(ls) // 2
    return solve(ls[:h]) + solve(ls[h:])


with open(outf, 'w', encoding='utf-8') as o:
    for i in range(0, len(lines), batch):
        for a in solve(lines[i:i + batch]):
            o.write(a + '\n')
        o.flush()
print('native-batch: %d cases, %d processes, %d single-case traps, %.1f s wall; peak per process: %s'
      % (len(lines), procs, traps, time.time() - t0, ' '.join('%s=%s' % kv for kv in sorted(peak.items()))), file=sys.stderr)
