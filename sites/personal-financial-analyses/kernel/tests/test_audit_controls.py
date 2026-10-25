"""Adversarial research-control acceptance, authored before remediation.

These are semantic counterexamples, not copies of the selection implementation.
All mutations use disposable databases. Any synthetic fact is audit-only and is
never written to the application's real database or a company source package.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from pfa.research import Research
from pfa.store import Store
import scripts.validate as validation


ROOT = Path(__file__).resolve().parents[1]


class AuditControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pfa-audit-controls-")
        self.research = Research(Store(Path(self.temp.name) / "research.sqlite3"))
        self.research.seed(ROOT / "fixtures/companies.json")

    def tearDown(self):
        self.temp.cleanup()

    def command(self, issuer, action, **data):
        return self.research.command(issuer, action, dict(
            data, expected_revision=self.research.view(issuer)["revision"]))

    def clone_verified(self, issuer, source, **overrides):
        keys = ("document_id", "metric", "value", "unit", "currency", "period_start",
                "period_end", "scope", "basis", "locator", "quote", "evidence_label")
        payload = {key: source[key] for key in keys if key in source}
        payload.update(overrides)
        item = self.command(issuer, "fact", **payload)
        self.command(issuer, "check", fact_id=item["id"], status="verified",
                     reason="AUDIT SYNTHETIC INPUT ONLY: accepted transcription does not establish its suitability for actuals.")
        return item

    def test_annual_growth_requires_matching_accounting_basis(self):
        view = self.research.view("msft")
        for metric, value in (("revenue", "1000000000"), ("net_income", "100000000")):
            original = next(f for f in view["quality"]["usable"]
                            if f["metric"] == metric and f["period_end"] == "2025-06-30")
            self.clone_verified("msft", original, value=value, basis="IFRS (audit synthetic)",
                                quote="AUDIT: an alternative accounting basis without a reconciliation bridge.")
        model = self.command("msft", "model")
        inputs = {item["role"]: item for item in model["inputs"]}
        if "prior_revenue" in inputs:
            self.assertEqual(inputs["revenue"]["basis"], inputs["prior_revenue"]["basis"],
                             "Annual growth needs comparable accounting bases or a documented bridge.")
        else:
            self.assertNotIn("revenue_growth", model["diagnostics"])

    def test_half_year_growth_does_not_use_eighteen_month_comparative(self):
        view = self.research.view("byd")
        current = next(f for f in view["quality"]["usable"]
                       if f["metric"] == "revenue" and f["period_end"] == "2026-06-30")
        try:
            synthetic = self.clone_verified("byd", current, value="1000000000",
                                            period_start="2024-01-01", period_end="2025-06-30",
                                            quote="AUDIT: eighteen months cannot be compared to one half-year.")
        except ValueError:
            return  # Rejecting the malformed actual at admission is also safe.
        model = self.command("byd", "model")
        comparative = next((i for i in model["inputs"] if i["role"] == "latest_comparative_revenue"), None)
        if comparative:
            self.assertNotEqual(comparative["fact_id"], synthetic["id"],
                                "Matching only month/day allows an eighteen-month value to masquerade as H1.")

    def test_review_rejects_conflicted_evidence(self):
        view = self.research.view("msft")
        fact = next(f for f in view["quality"]["usable"]
                    if f["metric"] == "revenue" and f["period_end"] == "2026-06-30")
        self.clone_verified("msft", fact, value=str(Decimal(fact["value"]) + 1))
        self.command("msft", "model")
        self.assertNotIn(fact["id"], {f["id"] for f in self.research.view("msft")["quality"]["usable"]})
        with self.assertRaises(ValueError, msg="A review's evidence gate must respect current unresolved conflicts."):
            self.command("msft", "review",
                         strongest_counter="AUDIT: this evidence is in an unresolved numeric conflict.",
                         response="AUDIT: resolve that conflict before admitting it as review support.",
                         falsifier="AUDIT: verify the original source and the conflicting extraction first.",
                         verdict="supported", fact_ids=[fact["id"]])

    def test_scenario_assumption_cannot_supply_actual_model_baseline(self):
        view = self.research.view("msft")
        synthetic_ids = set()
        for metric in ("revenue", "net_income"):
            fact = next(f for f in view["quality"]["usable"]
                        if f["metric"] == metric and f["period_end"] == "2026-06-30")
            try:
                synthetic = self.clone_verified("msft", fact, evidence_label="scenario_assumption",
                                                quote="AUDIT: explicitly an analyst assumption, not a historical actual.")
            except ValueError:
                continue  # Rejecting the label or verification transition is safe.
            synthetic_ids.add(synthetic["id"])
        model = self.command("msft", "model")
        self.assertFalse(synthetic_ids.intersection(i["fact_id"] for i in model["inputs"]),
                         "Verified transcription does not convert an assumption into an actual.")

    def test_future_period_cannot_supply_historical_actual_baseline(self):
        view = self.research.view("msft")
        synthetic_ids = set()
        for metric, value in (("revenue", "1000000000000"), ("net_income", "300000000000")):
            fact = next(f for f in view["quality"]["usable"] if f["metric"] == metric)
            try:
                synthetic = self.clone_verified("msft", fact, value=value,
                                                period_start="2099-01-01", period_end="2099-12-31",
                                                quote="AUDIT: a 2099 forecast is unavailable as a 2026 historical actual.")
            except ValueError:
                continue
            synthetic_ids.add(synthetic["id"])
        model = self.command("msft", "model")
        self.assertFalse(synthetic_ids.intersection(i["fact_id"] for i in model["inputs"]),
                         "Future forecasts must be excluded from historical actual inputs.")
        self.assertNotEqual(model["baseline_as_of"], "2099-12-31")

    def test_latest_comparable_ytd_not_hidden_by_unmatched_quarter(self):
        # CATL has comparable 9M actuals and a current Q3 without a prior Q3.
        # A valid, newer nine-month comparison must remain available to the user.
        model = self.command("catl", "model")
        expected = Decimal("442137424000") / Decimal("283071987000") - 1
        self.assertIn("latest_revenue_growth", model["diagnostics"],
                      "An unmatched current single quarter must not erase the latest valid YTD comparison.")
        self.assertAlmostEqual(Decimal(model["diagnostics"]["latest_revenue_growth"]), expected, places=20)

    def test_validation_fails_required_output_when_raw_hashes_pass(self):
        original_seed = Research.seed
        def seed_with_missing_bank_equity(instance, path):
            original_seed(instance, path)
            with instance.store.tx() as db:
                for fact in instance.facts(db, "cmb"):
                    if fact["metric"] == "common_equity":
                        instance.check_fact(db, "cmb", fact["id"], "rejected",
                                            "AUDIT: ordinary-share equity removed to simulate a failed mandatory model input.")
        output = Path(self.temp.name) / "validation-output.json"
        argv = ["validate.py", "--db", str(Path(self.temp.name) / "validation.sqlite3"), "--output", str(output)]
        failed = False
        with patch.object(Research, "seed", seed_with_missing_bank_equity), patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            try:
                result = validation.main()
                failed = isinstance(result, int) and result != 0
            except SystemExit as exc:
                failed = exc.code not in (None, 0)
            except ValueError:
                failed = True
        self.assertTrue(failed, "Acceptance must fail a required model output even when all source hashes match.")
        if output.exists():
            report = json.loads(output.read_text())
            self.assertTrue(all(row["sha256_match"] for row in report["source_checks"]))


if __name__ == "__main__":
    unittest.main()
