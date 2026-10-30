"""Coverage/refusal checks for scheduling metadata, never native semantics."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import native_gate_shard as S

ROOT=Path(__file__).resolve().parents[2]

class NativeGateShardTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/'seed/native-gate-plan.json').read_text())

    def test_complete_disjoint_partition_preserves_every_original_argv(self):
        before=copy.deepcopy(self.plan)
        original={row['name']:row for row in self.plan['phases']['x86']}
        selected=[row for shard in S.SHARDS for row in S.select(self.plan,shard)['phases']['x86']]
        self.assertEqual(len(selected),19)
        self.assertEqual(len({row['name'] for row in selected}),19)
        self.assertEqual({row['name']:row for row in selected},original)
        self.assertEqual(self.plan,before)
        selected[0]['argv'].append('--invalid-test-token')
        self.assertEqual(self.plan,before)

    def test_missing_gate_refuses_both_partitions(self):
        self.plan['phases']['x86'].pop()
        for shard in S.SHARDS:
            with self.assertRaisesRegex(ValueError,'incomplete'):
                S.select(self.plan,shard)

    def test_duplicate_gate_cannot_be_hidden_by_name_lookup(self):
        self.plan['phases']['x86'].append(copy.deepcopy(self.plan['phases']['x86'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate'):
            S.select(self.plan,'core')

    def test_new_gate_requires_explicit_partition_update(self):
        self.plan['phases']['x86'].append(dict(name='new-mandatory-gate',argv=['native']))
        with self.assertRaisesRegex(ValueError,'incomplete'):
            S.select(self.plan,'extensions')

    def test_unknown_shard_and_schema_refuse(self):
        with self.assertRaises(ValueError):S.select(self.plan,'skip')
        self.plan['schema']='unknown'
        with self.assertRaises(ValueError):S.select(self.plan,'core')

    def test_staging_records_exact_source_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'plan.json'
            S.main(ROOT/'seed/native-gate-plan.json','core',output)
            self.assertEqual(json.loads(output.read_text()),S.select(self.plan,'core'))
            coverage=json.loads(output.with_suffix('.coverage.json').read_text())
            self.assertEqual(coverage['selected'],list(S.SHARDS['core']))
            self.assertFalse(coverage['nativeVerdictAuthority'])
            with self.assertRaises(FileExistsError):
                S.main(ROOT/'seed/native-gate-plan.json','core',output)

    def proofs(self, root, capacity=2, shards=None):
        for shard in (shards or S.SHARDS):
            folder=root/shard
            (folder/'pg-x86').mkdir(parents=True)
            S.main(ROOT/'seed/native-gate-plan.json',shard,folder/'x86-shard-plan.json')
            rows=copy.deepcopy(S.select(self.plan,shard)['phases']['x86'])
            for row in rows:
                row['argv']=[token.replace('@TEMP@',str(folder)) for token in row['argv']]
                row['exit']=0
            (folder/'pg-x86/schedule.json').write_text(json.dumps(dict(
                status='COMPLETED',exit=0,jobs=capacity,capacity=capacity,gates=rows)))

    def test_join_accepts_all_nineteen_original_process_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.proofs(root)
            result=S.verify(ROOT/'seed/native-gate-plan.json',root,'success')
            self.assertEqual(result['executedGates'],19)
            self.assertFalse(result['qualificationReplacement'])

    def test_join_accepts_the_four_vcpu_runner_capacity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.proofs(root,4)
            result=S.verify(ROOT/'seed/native-gate-plan.json',root,'success')
            self.assertEqual((result['executedGates'],result['capacityPerRunner']),(19,4))

    def test_join_refuses_an_unbounded_capacity(self):
        for capacity in (1,3,8):
            with tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);self.proofs(root,capacity)
                with self.assertRaises(ValueError):
                    S.verify(ROOT/'seed/native-gate-plan.json',root,'success')

    def test_pull_request_tier_defers_only_the_arm64_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.proofs(root,shards=['core','extensions'])
            result=S.verify(ROOT/'seed/native-gate-plan.json',root,'success','pr')
            self.assertEqual(result['executedGates'],16)
            self.assertEqual(sorted(result['deferredToMain']),sorted(S.SHARDS['x86-dupes']))
            # main and full still require all nineteen
            for tier in ('main','full'):
                with self.assertRaisesRegex(ValueError,'missing|No such file'):
                    try: S.verify(ROOT/'seed/native-gate-plan.json',root,'success',tier)
                    except FileNotFoundError as e: raise ValueError('No such file') from e

    def test_pull_request_tier_refuses_a_deferral_arm64_no_longer_covers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            plan=copy.deepcopy(self.plan)
            plan['phases']['arm64']=[row for row in plan['phases']['arm64'] if row['name']!='ccf-filter']
            manifest=root/'plan.json'; manifest.write_text(json.dumps(plan)+'\n')
            with self.assertRaisesRegex(ValueError,'arm64'):
                S.verify(manifest,root,'success','pr')

    def test_join_refuses_a_missing_execution_despite_success_header(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.proofs(root)
            path=root/'core/pg-x86/schedule.json'
            data=json.loads(path.read_text());data['gates'].pop();path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'missing'):
                S.verify(ROOT/'seed/native-gate-plan.json',root,'success')

    def test_join_refuses_failed_gate_or_changed_argv(self):
        for field,value in [('exit',7),('argv',['native','--skip-refusals'])]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);self.proofs(root)
                path=root/'extensions/pg-x86/schedule.json'
                data=json.loads(path.read_text());data['gates'][0][field]=value;path.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError,'refused'):
                    S.verify(ROOT/'seed/native-gate-plan.json',root,'success')

    def test_join_refuses_source_manifest_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.proofs(root)
            manifest=root/'changed-source.json'
            manifest.write_text(json.dumps(self.plan)+'\n')
            with self.assertRaisesRegex(ValueError,'changed'):
                S.verify(manifest,root,'success')

    def test_post_gate_runtime_or_browser_failure_cannot_pass_aggregate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.proofs(root)
            for result in ['failure','cancelled','skipped',None]:
                with self.subTest(result=result),self.assertRaisesRegex(ValueError,'job did not succeed'):
                    S.verify(ROOT/'seed/native-gate-plan.json',root,result)

if __name__=='__main__':unittest.main()
