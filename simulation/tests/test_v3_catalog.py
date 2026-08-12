from collections import Counter

from simulation.catalog import automaker_catalog, policy_region_catalog
from simulation.data import load_automaker_profiles, load_profiles, load_province_personas
from simulation.domain_constants import AUTOMAKER_IDS, MAINLAND_PROVINCE_CODES
from simulation.models.common import DataQuality


def test_policy_region_groups_cover_31_without_duplicates():
    catalog = policy_region_catalog()
    assert tuple(catalog) == MAINLAND_PROVINCE_CODES
    assert Counter(item.policy_region.value for item in catalog.values()) == {
        "west": 12,
        "central": 10,
        "east": 9,
    }


def test_xinjiang_corps_is_not_an_extra_agent():
    assert len(MAINLAND_PROVINCE_CODES) == 31
    assert all("兵团" not in item.name for item in policy_region_catalog().values())


def test_frozen_automaker_set_is_unique_and_named():
    catalog = automaker_catalog()
    assert tuple(catalog) == AUTOMAKER_IDS
    assert [item.display_name for item in catalog.values()] == [
        "比亚迪",
        "吉利",
        "长安",
        "上汽通用五菱",
        "蔚来",
        "奇瑞",
        "零跑",
        "赛力斯",
        "小米汽车",
        "理想汽车",
    ]


def test_profiles_have_provenance_and_peer_network():
    profiles = load_profiles()
    assert len(profiles) == 31
    assert all(len(item.peer_province_codes) in range(3, 6) for item in profiles.values())
    assert all(
        item.provenance and item.data_quality is DataQuality.PROXY for item in profiles.values()
    )


def test_automaker_profiles_have_31_coverage_and_non_demo_sources():
    profiles = load_automaker_profiles()
    assert len(profiles) == 10
    assert all(len(item.channel_coverage_by_province) == 31 for item in profiles.values())
    assert all(
        record.source_year == 2025 and record.quality is not DataQuality.DEMO
        for item in profiles.values()
        for record in item.provenance.values()
    )


def test_personas_are_deterministic():
    assert load_province_personas() == load_province_personas()
