#!/usr/bin/env python3
"""Observer/source golden checks only; never replaces executed native gates."""
import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def form(text, name):
    start = text.index("(defn- " + name + " ")
    depth = 0
    for i in range(start, len(text)):
        depth += (text[i] == "(") - (text[i] == ")")
        if depth == 0:
            return text[start:i + 1]
    raise AssertionError("unclosed function")


def cases(text):
    # Fixed numeric case tables only, not a Kotoba interpreter or verdict.
    tokens = text.strip().split()
    assert tokens[:2] == ["(case", "id"] and tokens[-1].endswith(")")
    values = [int(x) for x in " ".join(tokens[2:]).removesuffix(")").split()]
    assert len(values) % 2 == 1
    return {**dict(zip(values[:-1:2], values[1:-1:2])), "default": values[-1]}


class SourceControls(unittest.TestCase):
    def setUp(self):
        self.host = (ROOT / "seed/bench/host-arm.kotoba").read_text()
        self.reference = json.loads((ROOT / "bench/embench/reproduce-20261015/round-sa-m104-20261015/records/round/expected-accounting-mw.json").read_text())

    def test_exact_factory_bindings(self):
        factory = (ROOT / "seed/79-native-cdci.kotoba").read_text()
        for path in ("seed/bench/host-arm.kotoba", "seed/bench/registry-arm.kotoba"):
            self.assertEqual(factory.count(hashlib.sha256((ROOT / path).read_bytes()).hexdigest()), 1)
        self.assertNotIn("bench", form(factory, "xc-role-hash"))

    def test_fixed_fuel_tables(self):
        tables = re.findall(r"\(case id[^()]*\)", form(self.host, "kb-expected-fuel"))
        self.assertEqual(len(tables), 2)
        for table, field in zip(tables, ("verifyFuel", "benchmarkFuel")):
            actual = cases(table)
            self.assertEqual(len(actual), 20)
            self.assertEqual([actual[i] for i in range(19)], [r["expectedSample"][field] for r in self.reference])
            self.assertEqual(actual["default"], -1)

    def test_fixed_arena_tables(self):
        tables = re.findall(r"([0-9]+) (\(case id[^()]*\))", form(self.host, "kb-expected-arena"))
        actual = {int(field): cases(table) for field, table in tables}
        self.assertEqual(set(actual), {0, 2, 3, 4})
        for i, row in enumerate(self.reference):
            fields = [int(n) for n in re.findall(r":[a-z-]+ ([0-9]+)", row["expectedStderr"])]
            self.assertEqual(len(fields), 17)
            self.assertEqual([actual[f].get(i, actual[f]["default"]) if f in actual else 0 for f in range(17)], fields)

    def test_mutations_are_closed_and_preserve_oracle(self):
        spec = importlib.util.spec_from_file_location("mutations", ROOT / "scripts/seed/check-native-benchmark-mutations.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        mutants = module.mutations(self.host)
        self.assertEqual(len(mutants), 13)
        self.assertEqual(len({name for name, *_ in mutants}), len(mutants))
        self.assertEqual(len({source for *_, source in mutants}), len(mutants))
        for name, _, refusal, source in mutants:
            with self.subTest(name=name):
                self.assertNotEqual(source, self.host)
                self.assertGreater(refusal, 0)
                for f in ("kb-accounting", "kb-expected-fuel", "kb-expected-arena"):
                    self.assertEqual(form(source, f), form(self.host, f))


if __name__ == "__main__":
    unittest.main()
