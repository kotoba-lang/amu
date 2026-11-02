"""Partition process argv only; all original native gates remain mandatory on main (on a pull request the x86 copies of
the gates that also run on arm64 are deferred to main, JUN-629)."""
import argparse
import hashlib
import json
from pathlib import Path

SHARDS = {
    'core': ('native-cdci', 'aiueos-projects', 'zero-watermark', 'live-abi',
             'kototama-receipt', 'b2-image', 'kototama-i64', 'b2-libc',
             'fs2-x86', 'aiueos-boot', 'clock-entropy', 'aiueos-image'),
    'extensions': ('kernel-memory', 'flock-vector', 'kototama-cache-abi',
                   'kototama-cache-host'),
    'x86-dupes': ('label-proof-index', 'runtime-profile', 'ccf-filter'),
}
# JUN-629 (owner decision 2026-10-30): on a pull request the x86 copies of these three gates are deferred to main.
# Each also runs in the arm64 phase of the same plan on every pull request, and verify refuses the deferral unless it
# still does. Main, the schedule and a manual dispatch run all nineteen x86 gates, as before.
DEFERRED_ON_PR = ('x86-dupes',)
TIERS = ('pr', 'main', 'full')

def select(plan, shard):
    if plan.get('schema') != 'amu.native-gate-plan.v1' or shard not in SHARDS:
        raise ValueError('unknown native gate plan or shard')
    rows = plan['phases']['x86']
    names = [row['name'] for row in rows]
    expected = [name for group in SHARDS.values() for name in group]
    if len(set(expected)) != len(expected) or len(set(names)) != len(names):
        raise ValueError('duplicate native gate')
    if set(names) != set(expected):
        raise ValueError('native gate partition is incomplete or stale')
    if any(not row['argv'] or not all(isinstance(arg,str) for arg in row['argv']) for row in rows):
        raise ValueError('invalid original native argv')
    original = {row['name']:row for row in rows}
    # Preserve every complete row and argv token. No shell/option rewriting,
    # fixture filtering, cached verdict or resource-profile change is allowed.
    selected = json.loads(json.dumps([original[name] for name in SHARDS[shard]]))
    return dict(schema=plan['schema'],baseline=plan['baseline'],phases={'x86':selected})

def main(manifest, shard, output):
    raw = manifest.read_bytes()
    source = json.loads(raw)
    selected = select(source,shard)
    with output.open('x') as stream:
        stream.write(json.dumps(selected,indent=2)+'\n')
    coverage = dict(schema='amu.native-gate-partition.v1',sourceManifest=manifest.as_posix(),
                    sourceManifestSHA256=hashlib.sha256(raw).hexdigest(),shard=shard,
                    temporaryRoot=output.parent.as_posix(),
                    allPartitions=SHARDS,selected=[row['name'] for row in selected['phases']['x86']],
                    originalArgvPreserved=True,nativeVerdictAuthority=False,
                    qualificationReplacement=False)
    output.with_suffix('.coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')

def verify(manifest, root, workflow_result, tier='full'):
    # Native schedules alone do not cover the runtime/browser checks before
    # and after them. A failed shard job must fail the legacy aggregate check.
    if workflow_result!='success':
        raise ValueError('native qualification shard job did not succeed')
    if tier not in TIERS:
        raise ValueError('unknown tier')
    raw=manifest.read_bytes()
    original=json.loads(raw)
    deferred=[name for shard in DEFERRED_ON_PR for name in SHARDS[shard]] if tier=='pr' else []
    arm64={row['name'] for row in original['phases'].get('arm64',[])}
    if any(name not in arm64 for name in deferred):
        raise ValueError('a gate deferred to main does not run in the arm64 phase')
    required=[shard for shard in SHARDS if not (tier=='pr' and shard in DEFERRED_ON_PR)]
    seen=[]; capacities=set()
    for shard in required:
        folder=root/shard
        coverage=json.loads((folder/'x86-shard-plan.coverage.json').read_text())
        staged=json.loads((folder/'x86-shard-plan.json').read_text())
        schedule=json.loads((folder/'pg-x86/schedule.json').read_text())
        expected=select(original,shard)
        if (coverage['sourceManifestSHA256']!=hashlib.sha256(raw).hexdigest()
                or coverage['shard']!=shard or staged!=expected):
            raise ValueError('changed native gate source or partition')
        # A runner schedules at most its vCPU count: 2 (the original bounded runner) or 4 (JUN-629, the 4-vCPU CI
        # runner), with jobs equal to the capacity. Scheduling only: every gate below still runs with its original argv.
        if (schedule['status']!='COMPLETED' or schedule['exit']!=0
                or schedule['capacity'] not in (2, 4) or schedule['jobs']!=schedule['capacity']):
            raise ValueError('native gate shard did not complete at a bounded capacity (2 or 4)')
        capacities.add(schedule['capacity'])
        rows=schedule['gates']
        names=[row['name'] for row in rows]
        if len(set(names))!=len(names) or set(names)!=set(SHARDS[shard]):
            raise ValueError('missing or duplicate executed native gate')
        by_name={row['name']:row for row in expected['phases']['x86']}
        for row in rows:
            argv=[token.replace('@TEMP@',coverage['temporaryRoot']) for token in by_name[row['name']]['argv']]
            if row['exit']!=0 or row['argv']!=argv:
                raise ValueError('refused native gate or changed original argv')
        seen.extend(names)
    if len(seen)+len(deferred)!=19 or len(set(seen)|set(deferred))!=19:
        raise ValueError('incomplete native x86 qualification')
    return dict(schema='amu.native-gate-partition-review.v1',status='PASS',tier=tier,executedGates=len(seen),
                deferredToMain=deferred,deferredGatesRunOnArm64=bool(deferred),
                originalArgvPreserved=True,capacityPerRunner=max(capacities),nativeVerdictAuthority=False,
                qualificationReplacement=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--shard',choices=SHARDS)
    p.add_argument('--output',type=Path)
    p.add_argument('--verify-root',type=Path)
    p.add_argument('--workflow-result')
    p.add_argument('--tier',choices=TIERS,default='full')
    args=p.parse_args()
    if args.verify_root:
        if args.shard or not args.output or not args.workflow_result:
            p.error('verification requires --verify-root, --workflow-result and --output')
        args.output.write_text(json.dumps(verify(args.manifest,args.verify_root,args.workflow_result,args.tier),indent=2)+'\n')
    else:
        if not args.shard or not args.output or args.workflow_result:
            p.error('staging requires only --shard and --output')
        main(args.manifest,args.shard,args.output)
