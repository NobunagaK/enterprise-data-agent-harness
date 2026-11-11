"""Bounded sales rules: query, structured claim scope and pure validator.

The runner executes this definition without owning metric-specific formulas.
No SQL, paths, or expected answers are accepted from the HTTP request.
"""

from collections.abc import Callable
from dataclasses import dataclass

from analytics_agent.harness.models import Claim, Evidence, RuleId, ValidationResult, ValueUnit
from analytics_agent.harness.validation import validate_growth, validate_total

SALES_SQL = """SELECT store_id, year, currency, SUM(amount_cents) AS amount_cents
FROM sales_records
WHERE store_id = 'demo-store' AND currency = 'CNY' AND year IN (2024, 2025)
GROUP BY store_id, year, currency ORDER BY year LIMIT 10"""
TOTAL_SQL = """SELECT store_id, year, currency, SUM(amount_cents) AS amount_cents
FROM sales_records
WHERE store_id = 'demo-store' AND currency = 'CNY' AND year = 2025
GROUP BY store_id, year, currency LIMIT 10"""


@dataclass(frozen=True)
class SalesRule:
    sql: str
    unit: ValueUnit
    claim_tool: str
    question: str
    year: int | None
    validate: Callable[[str, Claim | None, list[Evidence]], ValidationResult]

    def claim(self, evidence_id: str, value: str, unit: str | None = None) -> Claim:
        # Scope is fixed by the bounded task; the submitted unit is never corrected.
        return Claim(
            evidence_id=evidence_id,
            claimed_value=value,
            unit=self.unit if unit is None else unit,
            year=self.year,
        )


RULES: dict[RuleId, SalesRule] = {
    "growth_rate": SalesRule(
        sql=SALES_SQL,
        unit="percent",
        claim_tool="submit_growth_claim",
        year=None,
        question="What is the 2025 annual sales growth for demo-store?",
        validate=validate_growth,
    ),
    "sales_total": SalesRule(
        sql=TOTAL_SQL,
        unit="CNY_cent",
        claim_tool="submit_total_claim",
        year=2025,
        question="What is the total sales amount for demo-store in 2025, in CNY cents?",
        validate=validate_total,
    ),
}
