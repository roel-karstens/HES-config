from models import CandidateConfig, CandidateEvaluation
from recommendation import answer_user_question, recommend_top_configuration


def _mock_eval(score: float, savings: float, capex: float, payback: float, battery_kwh: float) -> CandidateEvaluation:
    return CandidateEvaluation(
        candidate=CandidateConfig(
            solar_kwp=10.0,
            battery_kwh=battery_kwh,
            heat_pump_enabled=True,
            ev_enabled=True,
            v2g_enabled=False,
            charging_strategy="pv_optimized",
        ),
        annual_savings_eur=savings,
        capex_eur=capex,
        payback_years=payback,
        score=score,
        constraints_ok=True,
        evidence={"grid_dependency_pct": 40.0, "self_consumption_pct": 55.0},
    )


def test_recommendation_contains_required_fields():
    ranked = [
        _mock_eval(1000, 900, 12000, 13.3, 8.0),
        _mock_eval(900, 850, 11000, 12.9, 0.0),
    ]
    recs = recommend_top_configuration(ranked, top_n=1)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.title
    assert rec.action
    assert len(rec.why) >= 1
    assert rec.expected_savings_eur_year > 0


def test_answer_user_question_returns_battery_assessment():
    ranked = [
        _mock_eval(1000, 900, 12000, 13.3, 8.0),
        _mock_eval(900, 850, 11000, 12.9, 0.0),
    ]
    rec = answer_user_question("Is a battery worth it?", ranked, context={})
    assert "Battery" in rec.title or "battery" in rec.title.lower()
    assert len(rec.why) > 0
