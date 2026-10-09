"""Guard experiment pairing, feasibility and the sequential capacity contract."""

from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import unittest

from plan_matrix import build_plan

ROOT = Path(__file__).resolve().parents[2]


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "bench/integration/campaign.json").read_text())

    def test_pairing_and_reproducibility(self):
        plan = build_plan(self.config)
        self.assertEqual(plan, build_plan(self.config))
        self.assertFalse(plan["execution_enabled"])
        pairs = defaultdict(list)
        for run in plan["planned_runs"]:
            pairs[run["pair_id"]].append(run["variant"])
        for variants in pairs.values():
            self.assertCountEqual(variants, ["baseline", "candidate"])
        self.assertTrue(all(cell["admission"] == "unverified" for cell in plan["cells"]))

    def test_full_mtp_interactions_present(self):
        cells = build_plan(self.config, "mtp_kv_workload")["cells"]
        expected = {(workload, mtp, kv) for workload in ("short", "long")
                    for mtp in (0, 2, 3, 4) for kv in ("control", "qualified_candidate")}
        actual = {(c["parameters"]["workload"], c["parameters"]["mtp_window"],
                   c["parameters"]["kv_profile"]) for c in cells}
        self.assertEqual(actual, expected)
        self.assertEqual(len(cells), len(expected))

    def test_capacity_advances_in_order(self):
        plan = build_plan(self.config, "capacity_ladder", confirmation=True)
        capacities = {c["cell_id"]: c["parameters"]["context_tokens"] for c in plan["cells"]}
        order = [capacities[r["cell_id"]] for r in plan["planned_runs"]]
        self.assertEqual(order, sorted(order))
        self.assertEqual(len(order), 18)

    def test_confirmation_repetitions(self):
        plan = build_plan(self.config, "workers_transfer", confirmation=True)
        counts = Counter((r["cell_id"], r["variant"]) for r in plan["planned_runs"])
        self.assertEqual(set(counts.values()), {7})

    def test_infeasible_or_ambiguous_design_rejected(self):
        invalid = copy.deepcopy(self.config)
        invalid["suites"][0]["blocks"][0]["context_tokens"] = 512
        with self.assertRaisesRegex(ValueError, "exceeds"):
            build_plan(invalid)
        invalid = copy.deepcopy(self.config)
        invalid["suites"][0]["factors"]["mtp_window"] = [0, 0]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_plan(invalid)
        with self.assertRaisesRegex(ValueError, "unknown suite"):
            build_plan(self.config, "typo")


if __name__ == "__main__":
    unittest.main()
