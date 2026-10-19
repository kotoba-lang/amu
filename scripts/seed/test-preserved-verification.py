#!/usr/bin/env python3
"""Negative controls for the qualification harness; no compiler/guest execution."""
import importlib.util,pathlib,shutil,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qualification',ROOT/'scripts/seed/verify-preserved-integration.py')
qualification=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualification)
class VerificationControls(unittest.TestCase):
 def test_only_exact_result_is_accepted(self):
  qualification.require_smoke_42(b'42\n',b'')
  for stdout,stderr in [(b'142\n',b''),(b'diagnostic 42\n',b''),(b'42\n',b'error 42')]:
   with self.subTest(stdout=stdout,stderr=stderr),self.assertRaises(AssertionError):qualification.require_smoke_42(stdout,stderr)
 def test_reintegration_archive_corruption_is_rejected(self):
  root=ROOT/'docs/evidence/native-selfhost-paused-20261012'
  with tempfile.TemporaryDirectory() as name:
   target=pathlib.Path(name)
   for file in ['verify.py','checkpoint.json','inventory.json','evidence.tgz','reintegration.json']:shutil.copyfile(root/file,target/file)
   (target/'reintegration-raw.tgz').write_bytes(b'corrupt')
   result=subprocess.run(['python3',str(target/'verify.py')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   self.assertNotEqual(result.returncode,0)
if __name__=='__main__':unittest.main()
