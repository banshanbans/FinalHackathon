from collections import Counter, defaultdict

from simulation.data import (
    build_enterprise_profiles,
    build_province_personas,
    load_enterprise_archetypes,
    load_network,
    load_profiles,
    load_province_personas,
)
from simulation.models.common import DataQuality, EnterpriseArchetype


def test_profiles_network_and_enterprises_are_complete() -> None:
    profiles = load_profiles()
    network = load_network()
    enterprises = build_enterprise_profiles(profiles)
    assert len(profiles) == 31
    assert set(network) == set(profiles)
    assert len(enterprises) == 186
    by_province: defaultdict[str, list[EnterpriseArchetype]] = defaultdict(list)
    for enterprise_id, enterprise in enterprises.items():
        assert enterprise_id == enterprise.enterprise_id
        by_province[enterprise.province_code].append(enterprise.archetype)
        assert enterprise.data_quality in {DataQuality.PROXY, DataQuality.DEMO}
    assert set(by_province) == set(profiles)
    assert all(Counter(items) == Counter(EnterpriseArchetype) for items in by_province.values())
    for code, edges in network.items():
        assert 3 <= len(edges) <= 5
        assert code not in {edge.target for edge in edges}
        assert {edge.target for edge in edges} <= set(profiles)


def test_enterprise_weights_and_provenance_categories() -> None:
    archetypes = load_enterprise_archetypes()
    assert abs(sum(item.weight for item in archetypes.values()) - 1) < 1e-9
    assert all(item.data_quality == DataQuality.DEMO for item in archetypes.values())
    provinces = load_profiles()
    assert {
        code for code, profile in provinces.items() if profile.data_quality == DataQuality.VERIFIED
    } == {"14", "33", "44"}


def test_province_personas_are_deterministic_and_match_demo_fixtures() -> None:
    profiles = load_profiles()
    network = load_network()
    personas = load_province_personas()
    assert personas == build_province_personas(profiles, network)
    assert len(personas) == 31
    assert personas["41"].primary_type.value == "inclusive_diffusion"
    assert personas["44"].primary_type.value == "technology_leap"
    assert personas["14"].primary_type.value == "green_transition"
    assert all(
        item.data_quality in {DataQuality.PROXY, DataQuality.DEMO} for item in personas.values()
    )
    assert all(len(item.key_constraints) == 2 for item in personas.values())
