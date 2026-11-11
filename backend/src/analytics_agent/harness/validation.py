import math
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from typing import Any

from analytics_agent.harness.models import (
    Claim,
    Evidence,
    RuleId,
    ValidationResult,
    ValidationStatus,
)


def rule_result(
    rule_id: RuleId, status: ValidationStatus, reason: str, **values: Any
) -> ValidationResult:
    """Use the selected rule's units even when no calculation could be completed."""
    if rule_id == "sales_total":
        return ValidationResult(
            status=status,
            reason=reason,
            rule_version="sales_total-v1",
            unit="CNY_cent",
            tolerance="0",
            **values,
        )
    return ValidationResult(status=status, reason=reason, **values)


class InvalidAmount(ValueError):
    def __init__(self, reason: str, status: ValidationStatus = "unverifiable"):
        self.reason = reason
        self.status = status


def amount_cents(value: Any) -> Decimal:
    """Accept integral engine numerics, never silently parse text or round cents."""
    if value is None:
        raise InvalidAmount("missing_or_invalid_amount")
    if isinstance(value, bool) or not isinstance(value, (int, Decimal, float)):
        raise InvalidAmount("evidence_type_drift", "tool_error")
    if (isinstance(value, float) and not math.isfinite(value)) or (
        isinstance(value, Decimal) and not value.is_finite()
    ):
        raise InvalidAmount("evidence_type_drift", "tool_error")
    if (isinstance(value, float) and not value.is_integer()) or (
        isinstance(value, Decimal) and value != value.to_integral_value()
    ):
        raise InvalidAmount("non_integral_amount")
    if value < 0:
        raise InvalidAmount("negative_amount_unsupported")
    return Decimal(int(value))


def validate_growth(run_id: str, claim: Claim | None, evidence: list[Evidence]) -> ValidationResult:
    """Pure rule: no model calls, SQL, persistence, or presentation decisions."""

    def unknown(reason: str) -> ValidationResult:
        return ValidationResult(
            status="unverifiable",
            reason=reason,
            claimed_value=claim.claimed_value if claim else None,
        )

    def tool_error(reason: str) -> ValidationResult:
        # Our own plumbing changing must never look like missing business data.
        return ValidationResult(
            status="tool_error",
            reason=reason,
            claimed_value=claim.claimed_value if claim else None,
        )

    if claim is None:
        return unknown("missing_claim")
    matches = [e for e in evidence if e.id == claim.evidence_id and e.run_id == run_id]
    if len(matches) != 1:
        return unknown("evidence_not_found_or_wrong_run")
    item = matches[0]
    if item.dataset_version != "sales-v1":
        return unknown("unsupported_dataset")
    if item.truncated:
        return unknown("truncated_evidence")
    if claim.unit != "percent" or item.amount_unit != "CNY_cent":
        return unknown("unsupported_unit")
    if claim.store_id != "demo-store" or (claim.previous_year, claim.current_year) != (2024, 2025):
        return unknown("unsupported_scope")
    if len(item.rows) != 2:
        return unknown("missing_or_ambiguous_periods")
    amounts: dict[int, Decimal] = {}
    for row in item.rows:
        year = row.get("year")
        if (
            type(year) is not int
            or year not in (2024, 2025)
            or year in amounts
            or row.get("store_id") != claim.store_id
            or row.get("currency") != "CNY"
        ):
            return unknown("evidence_scope_mismatch")
        try:
            amounts[year] = amount_cents(row.get("amount_cents"))
        except InvalidAmount as exc:
            return tool_error(exc.reason) if exc.status == "tool_error" else unknown(exc.reason)
    previous, current = amounts[2024], amounts[2025]
    if previous == 0:
        return unknown("zero_denominator")
    try:
        actual = Decimal(claim.claimed_value)
    except InvalidOperation:
        return unknown("invalid_claim_value")
    if not actual.is_finite() or abs(actual) > Decimal("1e20"):
        return unknown("invalid_claim_value")
    with localcontext() as ctx:
        # A 64-character claim times a SQLite integer must not round at the
        # inclusive boundary before comparison. Display rounding stays separate.
        ctx.prec = 100
        numerator = (current - previous) * 100
        expected = numerator / previous
        difference = abs(actual - expected)
        # Cross-multiplication avoids rounding a recurring quotient at the boundary.
        passed = abs(actual * previous - numerator) <= Decimal("0.01") * previous
        return ValidationResult(
            status="passed" if passed else "failed",
            reason="within_tolerance" if passed else "outside_tolerance",
            expected_value=str(expected),
            expected_display=str(expected.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            claimed_value=claim.claimed_value,
            difference_pp=str(difference),
        )


def validate_total(run_id: str, claim: Claim | None, evidence: list[Evidence]) -> ValidationResult:
    """Verify the 2025 demo-store total in integer CNY cents with zero tolerance."""

    def result(status: ValidationStatus, reason: str, **values: Any) -> ValidationResult:
        return rule_result(
            "sales_total",
            status,
            reason,
            claimed_value=claim.claimed_value if claim else None,
            **values,
        )

    if claim is None:
        return result("unverifiable", "missing_claim")
    matches = [e for e in evidence if e.id == claim.evidence_id and e.run_id == run_id]
    if len(matches) != 1:
        return result("unverifiable", "evidence_not_found_or_wrong_run")
    item = matches[0]
    if item.dataset_version != "sales-v1":
        return result("unverifiable", "unsupported_dataset")
    if item.truncated:
        return result("unverifiable", "truncated_evidence")
    if claim.unit != "CNY_cent" or item.amount_unit != "CNY_cent":
        return result("unverifiable", "unsupported_unit")
    if claim.store_id != "demo-store" or claim.year != 2025:
        return result("unverifiable", "unsupported_scope")
    if len(item.rows) != 1:
        return result("unverifiable", "missing_or_ambiguous_periods")
    row = item.rows[0]
    if (
        type(row.get("year")) is not int
        or row["year"] != claim.year
        or row.get("store_id") != claim.store_id
        or row.get("currency") != "CNY"
    ):
        return result("unverifiable", "evidence_scope_mismatch")
    try:
        expected = amount_cents(row.get("amount_cents"))
    except InvalidAmount as exc:
        return result(exc.status, exc.reason)
    try:
        actual = Decimal(claim.claimed_value)
    except InvalidOperation:
        return result("unverifiable", "invalid_claim_value")
    if not actual.is_finite() or actual.copy_abs() > Decimal("1e20"):
        return result("unverifiable", "invalid_claim_value")
    if actual != actual.to_integral_value():
        return result("unverifiable", "non_integral_claim")
    with localcontext() as ctx:
        ctx.prec = 100
        difference = abs(actual - expected)
    passed = difference == 0
    return result(
        "passed" if passed else "failed",
        "within_tolerance" if passed else "outside_tolerance",
        expected_value=str(expected),
        expected_display=str(expected),
        difference=str(difference),
    )
