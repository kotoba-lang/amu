#!/usr/bin/env python3
"""Classifier v2: split host-vtable vs guest call conventions, distinguish
tail dispatch from intra-function label branches, and structurally verify that
every cross-function transfer (call/jmp whose target is a function prologue)
carries the context discipline. Also audit push/pop for the 16-byte alignment
argument. Reads the voff map of prologues from the pattern scan."""
import json, re, subprocess, sys, os, collections

L = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/llvm-objdump"
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400078
LINE = re.compile(r'^\s+([0-9a-f]+):\s+(([0-9a-f]{2} )+)\s+(\S+)\s*(.*)$')

def decode(elf_path):
    out = subprocess.run([L, '-d', '--triple=x86_64-unknown-linux', elf_path],
                         capture_output=True, text=True).stdout
    return [(int(m.group(1), 16), m.group(4).lower(), m.group(5).strip())
            for m in (LINE.match(l) for l in out.splitlines()) if m]

def parse_tgt(ops):
    tok = ops.split()[0] if ops.split() else ''
    if re.match(r'^0x[0-9a-f]+$', tok):
        return int(tok, 16) - BASE
    return None

def ctx_rdi(i):
    return bool(i) and i[1] == 'movq' and i[2].startswith('-0x8(%rbp), %rdi')
def ctx_r9(i):
    return bool(i) and i[1] == 'movq' and i[2].startswith('-0x8(%rbp), %r9')

def run(elf_path, prologues):
    insns = decode(elf_path)
    voffs = [o - BASE for o, _, _ in insns]
    pset = set(prologues)
    out = {'elf': os.path.basename(elf_path), 'decoded_insns': len(insns),
           'class': collections.Counter(), 'anomalies': [],
           'push_pop': collections.Counter(),
           'ctx_rdi_loads': 0, 'ctx_r9_loads': 0}
    for idx, (off, mnem, ops) in enumerate(insns):
        voff = off - BASE
        prev = insns[idx-1] if idx else None
        prev2 = insns[idx-2] if idx > 1 else None
        prev3 = insns[idx-3] if idx > 2 else None
        if mnem in ('push', 'pushq', 'pop', 'popq'):
            out['push_pop'][mnem + ' ' + ops] += 1
        if ctx_r9((off, mnem, ops)):
            out['ctx_r9_loads'] += 1
        if ctx_rdi((off, mnem, ops)):
            out['ctx_rdi_loads'] += 1
        if mnem.startswith('call'):
            if '*' in ops:
                if 'rdi' in ops:
                    ok = ctx_rdi(prev)
                    out['class']['call_host_vtable_ok' if ok else 'call_host_vtable_BAD'] += 1
                    if not ok:
                        out['anomalies'].append({'voff': voff, 'insn': mnem + ' ' + ops,
                                                 'prev': prev, 'note': 'host dispatch without rdi reload'})
                else:
                    ok = ctx_r9(prev)
                    out['class']['call_guest_indirect_ok' if ok else 'call_guest_indirect_BAD'] += 1
                    if not ok:
                        out['anomalies'].append({'voff': voff, 'insn': mnem + ' ' + ops,
                                                 'prev': prev, 'note': 'guest indirect call without r9'})
            else:
                tgt = parse_tgt(ops)
                ok = ctx_r9(prev)
                key = 'call_guest_direct_ok' if ok else 'call_guest_direct_BAD'
                out['class'][key] += 1
                if tgt is not None and tgt not in pset:
                    out['class']['call_target_not_prologue'] += 1
                    out['anomalies'].append({'voff': voff, 'insn': mnem + ' ' + ops,
                                             'target': tgt, 'note': 'call target not a prologue'})
                if not ok:
                    out['anomalies'].append({'voff': voff, 'insn': mnem + ' ' + ops,
                                             'prev': prev, 'note': 'guest direct call without r9'})
        elif mnem.startswith('jmp'):
            tail = prev is not None and prev[1] == 'leave' and ctx_r9(prev2)
            if '*' in ops:
                ok = tail
                out['class']['jmp_tail_indirect_ok' if ok else 'jmp_tail_indirect_BAD'] += 1
                if not ok:
                    out['anomalies'].append({'voff': voff, 'insn': mnem + ' ' + ops,
                                             'prev': prev, 'note': 'indirect jmp without leave/r9'})
            else:
                tgt = parse_tgt(ops)
                if voff == 0:
                    out['class']['jmp_entry_dispatch'] += 1
                    if tgt not in pset:
                        out['anomalies'].append({'voff': 0, 'target': tgt,
                                                 'note': 'entry jmp target not a prologue'})
                elif tail:
                    out['class']['jmp_tail_dispatch_ok'] += 1
                    if tgt is not None and tgt not in pset:
                        out['class']['jmp_tail_target_not_prologue'] += 1
                        out['anomalies'].append({'voff': voff, 'target': tgt,
                                                 'note': 'tail jmp target not a prologue'})
                else:
                    out['class']['jmp_label_branch'] += 1
                    if tgt is not None and tgt in pset:
                        out['class']['jmp_branch_to_prologue_ANOMALY'] += 1
                        out['anomalies'].append({'voff': voff, 'target': tgt, 'prev': prev,
                                                 'note': 'plain jmp into a function prologue (possible missing tail discipline)'})
    out['class'] = dict(out['class'])
    out['push_pop'] = dict(out['push_pop'])
    return out

if __name__ == '__main__':
    scan = json.load(open(os.path.join(HERE, 'scan-results.json')))
    progs = {k: [d['offset'] for d in v['prologues']] for k, v in scan.items()}
    results = {}
    for elf in sys.argv[1:]:
        base = os.path.basename(elf).replace('.wrapped.elf', '').replace('.code', 'G1.code')
        key = os.path.basename(elf).replace('.wrapped.elf', '.bin')
        if key == 'G1.code.bin':
            pkey = 'G1.code.bin'
        else:
            pkey = key
        p = progs.get(pkey, [])
        r = run(elf, p)
        results[os.path.basename(elf)] = r
        print(json.dumps({'elf': r['elf'], 'insns': r['decoded_insns'],
                          'class': r['class'], 'push_pop': r['push_pop'],
                          'ctx_rdi_loads': r['ctx_rdi_loads'],
                          'ctx_r9_loads': r['ctx_r9_loads'],
                          'anomalies': len(r['anomalies'])}))
        for a in r['anomalies'][:10]:
            print('   ANOMALY', json.dumps(a, default=str))
    json.dump(results, open(os.path.join(HERE, 'classify-v2.json'), 'w'), indent=1, default=str)
