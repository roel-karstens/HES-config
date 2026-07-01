from __future__ import annotations

from models import CandidateEvaluation, Recommendation


def _confidence_from_ranked(ranked: list[CandidateEvaluation]) -> str:
    if len(ranked) < 2:
        return "low"
    best = ranked[0]
    runner = ranked[1]
    denom = max(abs(best.score), 1.0)
    margin = (best.score - runner.score) / denom
    if margin >= 0.15:
        return "high"
    if margin >= 0.05:
        return "medium"
    return "low"


def explain_tradeoff(best: CandidateEvaluation, alternatives: list[CandidateEvaluation]) -> list[str]:
    reasons = [
        f"Simulated {1 + len(alternatives)} candidate system configurations.",
        f"Best candidate annual savings: EUR {best.annual_savings_eur:,.0f}.",
        f"Estimated payback: {best.payback_years:.1f} years.",
    ]
    if alternatives:
        alt = alternatives[0]
        reasons.append(
            "Top alternative had either lower savings or weaker objective score "
            f"(alt score {alt.score:,.0f} vs best {best.score:,.0f})."
        )
    return reasons


def recommend_top_configuration(ranked: list[CandidateEvaluation], top_n: int = 3) -> list[Recommendation]:
    if not ranked:
        return []

    out: list[Recommendation] = []
    conf = _confidence_from_ranked(ranked)

    for idx, ev in enumerate(ranked[:top_n], start=1):
        candidate = ev.candidate
        action = (
            f"Set PV to {candidate.solar_kwp:.0f} kWp and battery to {candidate.battery_kwh:.0f} kWh; "
            f"charging strategy: {candidate.charging_strategy}."
        )
        why = explain_tradeoff(ev, ranked[idx:idx + 2])

        out.append(
            Recommendation(
                title=f"Recommended configuration #{idx}",
                action=action,
                why=why,
                expected_savings_eur_year=ev.annual_savings_eur,
                investment_eur=ev.capex_eur,
                payback_years=ev.payback_years,
                confidence=conf,
                evidence=ev.evidence,
            )
        )
    return out


def answer_user_question(
    question: str,
    ranked: list[CandidateEvaluation],
    context: dict,
) -> Recommendation:
    if not ranked:
        return Recommendation(
            title="No recommendation available",
            action="Provide more input data and run optimization.",
            why=["No candidates were evaluated."],
            expected_savings_eur_year=0.0,
            investment_eur=0.0,
            payback_years=float("inf"),
            confidence="low",
            evidence=context,
        )

    question_l = question.lower()
    best = ranked[0]

    if "battery" in question_l and "worth" in question_l:
        no_batt = next((r for r in ranked if r.candidate.battery_kwh == 0), None)
        if no_batt is not None and best.candidate.battery_kwh > 0:
            incremental = best.annual_savings_eur - no_batt.annual_savings_eur
            return Recommendation(
                title="Battery value assessment",
                action=f"Use approximately {best.candidate.battery_kwh:.0f} kWh battery.",
                why=[
                    f"Incremental annual savings over no battery: EUR {incremental:,.0f}.",
                    f"Estimated payback for best design: {best.payback_years:.1f} years.",
                ],
                expected_savings_eur_year=best.annual_savings_eur,
                investment_eur=best.capex_eur,
                payback_years=best.payback_years,
                confidence=_confidence_from_ranked(ranked),
                evidence=best.evidence,
            )

    recs = recommend_top_configuration(ranked, top_n=1)
    return recs[0]
