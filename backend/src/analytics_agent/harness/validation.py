from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

from analytics_agent.harness.models import Claim, Evidence, ValidationResult


def validate_growth(run_id: str, claim: Claim | None, evidence: list[Evidence]) -> ValidationResult:
    """Pure rule: no model calls, SQL, persistence, or presentation decisions."""

    def unknown(reason: str) -> ValidationResult:
        return ValidationResult(
            status="unverifiable",
            reason=reason,
            claimed_value=claim.claimed_value if claim else None,
        )

    if claim is None:
        return unknown("missing_claim")
    matches = [e for e in evidence if e.id == claim.evidence_id and e.run_id == run_id]
    if len(matches) != 1:
        return unknown("evidence_not_found_or_wrong_run")
    item = matches[0]
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
        value = row.get("amount_cents")
        if type(value) is not int:
            return unknown("missing_or_invalid_amount")
        if value < 0:
            return unknown("negative_amount_unsupported")
        amounts[year] = Decimal(value)
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
        ctx.prec = 60
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
