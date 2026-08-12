import pytest
from pydantic import ValidationError

from simulation.data import build_enterprise_profiles
from simulation.models.action import ProvinceAction
from simulation.models.central import PolicyFieldChange
from simulation.models.common import (
    AdjustmentDirection,
    CentralSupportType,
    DecisionPosture,
    EnterpriseArchetype,
    EnterpriseReasonCode,
    FinancingChoice,
    InterprovincialStrategy,
    Participation,
    Phase,
    ProvinceConstraint,
    ProvincePriorityGoal,
    ProvinceReasonCode,
    StrategyAssessment,
    UpgradeType,
)
from simulation.models.enterprise import EnterpriseAction, EnterpriseActionBatch
from simulation.models.policy import InstrumentMix, TechnologyMix
from simulation.models.province import AdjustmentIntent, ProvinceFeedback


def test_policy_mixes_must_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        InstrumentMix(direct_subsidy=0.5, interest_subsidy=0.4, financing_guarantee=0.3)
    with pytest.raises(ValidationError):
        TechnologyMix(digital=0.5, green=0.4, general=0.3)


def _enterprise_action(
    archetype: EnterpriseArchetype,
    *,
    participation: Participation = Participation.PARTICIPATE,
) -> EnterpriseAction:
    inactive = participation in {Participation.WAIT, Participation.DECLINE}
    return EnterpriseAction(
        action_id=f"action_{archetype.value}",
        enterprise_id=f"44:{archetype.value}",
        province_code="44",
        archetype=archetype,
        phase=Phase.T2,
        participation=participation,
        upgrade_type=UpgradeType.NONE if inactive else UpgradeType.DIGITAL,
        financing_choice=FinancingChoice.NONE if inactive else FinancingChoice.DIRECT_SUBSIDY,
        investment_intensity=0 if inactive else 0.6,
        requested_support=0.4,
        reason_codes=[EnterpriseReasonCode.POLICY_MATCH],
        public_summary="结构化企业行动",
    )


def test_enterprise_action_rejects_inconsistent_combinations() -> None:
    with pytest.raises(ValidationError):
        _enterprise_action(EnterpriseArchetype.TRADITIONAL_SME).model_copy(
            update={
                "participation": Participation.WAIT,
                "investment_intensity": 0.5,
            }
        ).model_validate(
            {
                **_enterprise_action(EnterpriseArchetype.TRADITIONAL_SME).model_dump(mode="json"),
                "participation": "wait",
                "upgrade_type": "none",
                "financing_choice": "none",
                "investment_intensity": 0.5,
            }
        )


def test_enterprise_batch_requires_all_six_archetypes() -> None:
    actions = [_enterprise_action(item) for item in EnterpriseArchetype]
    batch = EnterpriseActionBatch(
        batch_id="batch_44",
        province_code="44",
        phase=Phase.T2,
        actions=actions,
    )
    assert len(batch.actions) == 6
    with pytest.raises(ValidationError):
        EnterpriseActionBatch(
            batch_id="bad",
            province_code="44",
            phase=Phase.T2,
            actions=actions[:-1],
        )


def test_policy_change_path_is_frozen() -> None:
    with pytest.raises(ValidationError):
        PolicyFieldChange(path="gdp_growth", from_value=1, to_value=2)


def test_enterprise_profile_ids_match_archetypes() -> None:
    profiles = build_enterprise_profiles()
    assert all(item.enterprise_id.endswith(item.archetype.value) for item in profiles.values())


def _province_action(**updates: object) -> ProvinceAction:
    payload = {
        "action_id": "province_41_T1",
        "previous_action_id": None,
        "province_code": "41",
        "phase": Phase.T1,
        "primary_goal": ProvincePriorityGoal.SME_FINANCING_ACCESS,
        "decision_posture": DecisionPosture.BALANCED,
        "target_enterprise_groups": [EnterpriseArchetype.TRADITIONAL_SME],
        "interprovincial_strategy": InterprovincialStrategy.COLLABORATE,
        "target_province_codes": ["42"],
        "implementation_intensity": 0.7,
        "local_match_ratio": 0.5,
        "instrument_mix": InstrumentMix(),
        "sme_preference": 0.7,
        "regional_delivery_focus": 0.6,
        "technology_mix": TechnologyMix(),
        "requested_central_support": 0.4,
        "reason_codes": [ProvinceReasonCode.SME_ACCESS_PRIORITY],
        "public_summary": "本次实验中优先改善中小企业融资可达性。",
    }
    payload.update(updates)
    return ProvinceAction.model_validate(payload)


def test_province_action_phase_and_strategy_combinations_are_enforced() -> None:
    assert _province_action().schema_version == "province-action-v3"
    with pytest.raises(ValidationError):
        _province_action(
            interprovincial_strategy=InterprovincialStrategy.INDEPENDENT,
            target_province_codes=["42"],
        )
    with pytest.raises(ValidationError):
        _province_action(phase=Phase.T4, previous_action_id=None)
    t4 = _province_action(
        action_id="province_41_T4",
        phase=Phase.T4,
        previous_action_id="province_41_T1",
    )
    assert t4.previous_action_id == "province_41_T1"


def test_feedback_adjustment_paths_and_support_type_are_frozen() -> None:
    with pytest.raises(ValidationError):
        AdjustmentIntent(
            path="gdp_growth",
            direction=AdjustmentDirection.INCREASE,
            reason_code=ProvinceReasonCode.MANUFACTURING_BASE,
        )
    with pytest.raises(ValidationError):
        ProvinceFeedback(
            feedback_id="feedback_41",
            province_code="41",
            strategy_assessment=StrategyAssessment.MIXED,
            priority_enterprise_groups=[EnterpriseArchetype.TRADITIONAL_SME],
            key_constraints=[ProvinceConstraint.FINANCING_GAP],
            requested_support_type=CentralSupportType.NONE,
            requested_central_support=0.5,
            reason_codes=[ProvinceReasonCode.FINANCING_GAP],
            evidence_refs=["enterprise:41:traditional_sme:action:T2"],
            public_summary="当前企业反馈显示融资约束仍需跟踪。",
        )
