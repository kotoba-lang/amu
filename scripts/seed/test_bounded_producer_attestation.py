#!/usr/bin/env python3
"""Refuse untrusted event contexts before any artifact or verifier is opened."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from check_bounded_producer_attestation import main


class ContextControls(unittest.TestCase):
    def test_untrusted_contexts_refuse_before_io(self):
        trusted = {"GITHUB_REPOSITORY": "kotoba-lang/amu", "GITHUB_REPOSITORY_ID": "1297097065",
                   "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "push", "GITHUB_SHA": "a" * 40}
        cases = [("GITHUB_REPOSITORY", "other/amu"), ("GITHUB_REPOSITORY_ID", "1"),
                 ("GITHUB_REF", "refs/pull/1/merge"), ("GITHUB_EVENT_NAME", "pull_request"),
                 ("GITHUB_SHA", "invalid")]
        for name, value in cases:
            env = dict(trusted, **{name: value})
            with self.subTest(name=name), patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
                main(Path("/nonexistent/artifact"), Path("/nonexistent/gh"))


if __name__ == "__main__":
    unittest.main()
