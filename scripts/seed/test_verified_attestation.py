#!/usr/bin/env python3
"""Policy-shape controls; cryptographic verification is exercised separately."""
import unittest
from dataclasses import replace

from verified_attestation import AttestationPolicy, _certificate_matches, _validate


class PolicyControls(unittest.TestCase):
    def setUp(self):
        self.policy = AttestationPolicy("kotoba-lang/amu", "1297097065", ".github/workflows/producer.yml",
                                        "refs/heads/main", "a" * 40, "b" * 40, "push")
        identity = "https://github.com/kotoba-lang/amu/.github/workflows/producer.yml@refs/heads/main"
        self.certificate = {
            "issuer": "https://token.actions.githubusercontent.com", "subjectAlternativeName": identity,
            "buildSignerURI": identity, "buildSignerDigest": "b" * 40,
            "sourceRepositoryURI": "https://github.com/kotoba-lang/amu", "sourceRepositoryIdentifier": "1297097065",
            "sourceRepositoryDigest": "a" * 40, "sourceRepositoryRef": "refs/heads/main",
            "runnerEnvironment": "github-hosted", "buildTrigger": "push",
        }

    def test_every_certificate_field_is_required(self):
        _validate(self.policy)
        self.assertTrue(_certificate_matches(self.certificate, self.policy))
        for key in self.certificate:
            with self.subTest(key=key):
                altered = dict(self.certificate)
                altered[key] = "untrusted"
                self.assertFalse(_certificate_matches(altered, self.policy))
                del altered[key]
                self.assertFalse(_certificate_matches(altered, self.policy))

    def test_unbounded_policy_inputs_are_refused(self):
        invalid = [("repository", "kotoba-lang/amu/other"), ("repository_id", "0"),
                   ("workflow", ".github/workflows/../../producer.yml"), ("ref", "refs/pull/1/merge"),
                   ("ref", "refs/heads/../main"), ("ref", "refs/heads/main//other"),
                   ("ref", "refs/heads/main.lock"),
                   ("source_sha", "a" * 39), ("signer_sha", "b" * 39), ("trigger", "pull_request")]
        for field, value in invalid:
            with self.subTest(field=field), self.assertRaises(ValueError):
                _validate(replace(self.policy, **{field: value}))

    def test_explicit_task_branch_is_not_main(self):
        branch = replace(self.policy, ref="refs/heads/codex/task-branch")
        _validate(branch)
        self.assertFalse(_certificate_matches(self.certificate, branch))


if __name__ == "__main__":
    unittest.main()
