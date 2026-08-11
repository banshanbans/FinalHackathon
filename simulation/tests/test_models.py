import pytest
from pydantic import ValidationError

from simulation.models.action import ProvinceAction
from simulation.models.central import CentralIntervention, ParameterChange
from simulation.models.common import Industry, InteractionStrategy, Phase, Stance, TalentStrategy
from simulation.models.policy import EvaluationWeights


def test_evaluation_weights_must_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        EvaluationWeights(innovation=0.5, employment=0.3, equity=0.3, fiscal_efficiency=0.1)


def test_province_action_rejects_self_target() -> None:
    with pytest.raises(ValidationError):
        ProvinceAction(
            action_id="a1",
            province_code="44",
            phase=Phase.T1,
            stance=Stance.BALANCED,
            implementation_intensity=0.6,
            local_budget_ratio=0.5,
            priority_industries=[Industry.AI],
            talent_strategy=TalentStrategy.EXPAND,
            interaction_strategy=InteractionStrategy.COMPETE,
            target_provinces=["44"],
            requested_central_support=0.2,
            reason_codes=["HIGH_INDUSTRY_FIT"],
            public_summary="测试策略",
        )


def test_intervention_rejects_unsupported_fields() -> None:
    with pytest.raises(ValidationError):
        CentralIntervention(
            intervention_id="i1",
            proposal_id="p1",
            parameter_changes={"gdp_growth": ParameterChange(from_value=1, to_value=2)},
            approved_at="2026-08-12T00:00:00Z",
        )
