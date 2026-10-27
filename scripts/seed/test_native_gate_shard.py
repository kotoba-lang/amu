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
        self.assertEqual(len(selected),17)
        self.assertEqual(len({row['name'] for row in selected}),17)
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

    def proofs(self, root):
        for shard in S.SHARDS:
            folder=root/shard
            (folder/'pg-x86').mkdir(parents=True)
            S.main(ROOT/'seed/native-gate-plan.json',shard,folder/'x86-shard-plan.json')
            rows=copy.deepcopy(S.select(self.plan,shard)['phases']['x86'])
            for row in rows:
                row['argv']=[token.replace('@TEMP@',str(folder)) for token in row['argv']]
                row['exit']=0
            (folder/'pg-x86/schedule.json').write_text(json.dumps(dict(
                status='COMPLETED',exit=0,jobs=2,capacity=2,gates=rows)))

    def test_join_accepts_all_seventeen_original_process_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.proofs(root)
            result=S.verify(ROOT/'seed/native-gate-plan.json',root)
            self.assertEqual(result['executedGates'],17)
            self.assertFalse(result['qualificationReplacement'])

    def test_join_refuses_a_missing_execution_despite_success_header(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.proofs(root)
            path=root/'core/pg-x86/schedule.json'
            data=json.loads(path.read_text());data['gates'].pop();path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'missing'):
                S.verify(ROOT/'seed/native-gate-plan.json',root)

    def test_join_refuses_failed_gate_or_changed_argv(self):
        for field,value in [('exit',7),('argv',['native','--skip-refusals'])]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);self.proofs(root)
                path=root/'extensions/pg-x86/schedule.json'
                data=json.loads(path.read_text());data['gates'][0][field]=value;path.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError,'refused'):
                    S.verify(ROOT/'seed/native-gate-plan.json',root)

    def test_join_refuses_source_manifest_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);self.proofs(root)
            manifest=root/'changed-source.json'
            manifest.write_text(json.dumps(self.plan)+'\n')
            with self.assertRaisesRegex(ValueError,'changed'):
                S.verify(manifest,root)

if __name__=='__main__':unittest.main()
