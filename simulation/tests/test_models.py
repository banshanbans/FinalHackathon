import pytest
from pydantic import ValidationError

from simulation.data import build_enterprise_profiles
from simulation.models.central import PolicyFieldChange
from simulation.models.common import (
    EnterpriseArchetype,
    EnterpriseReasonCode,
    FinancingChoice,
    Participation,
    Phase,
    UpgradeType,
)
from simulation.models.enterprise import EnterpriseAction, EnterpriseActionBatch
from simulation.models.policy import InstrumentMix, TechnologyMix


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
