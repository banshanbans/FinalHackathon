from simulation.data import load_network, load_profiles
from simulation.models.common import DataQuality


def test_profiles_and_network_cover_31_provinces() -> None:
    profiles = load_profiles()
    network = load_network()
    assert len(profiles) == 31
    assert set(network) == set(profiles)
    for code, edges in network.items():
        assert 3 <= len(edges) <= 5
        assert code not in {edge.target for edge in edges}
        assert {edge.target for edge in edges} <= set(profiles)


def test_only_three_profiles_are_marked_verified() -> None:
    profiles = load_profiles()
    assert {
        code for code, profile in profiles.items() if profile.data_quality == DataQuality.VERIFIED
    } == {"14", "33", "44"}
