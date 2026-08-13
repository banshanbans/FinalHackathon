from fastapi.testclient import TestClient
from policyscope_api.main import create_app
from policyscope_api.settings import Settings


def _policy(source: dict, policy_id: str, delta: float = 0) -> dict:
    return {
        **source,
        "policy_id": policy_id,
        "west_central_share": source["west_central_share"] + delta,
        "central_central_share": source["central_central_share"] + delta,
        "east_central_share": source["east_central_share"] + delta,
    }


def _prepare(client: TestClient, *, idempotency_key: str = "m34-create") -> dict:
    created = client.post(
        "/api/experiments",
        json={
            "policy_text": "西部 95%，中部 90%，东部 85%。",
            "product_version": "v3_2_m34",
        },
        headers={"Idempotency-Key": idempotency_key},
    )
    assert created.status_code == 201
    state = created.json()
    experiment_id = state["experiment_id"]
    interpretation = {**state["interpretation"], "status": "confirmed"}
    confirmed = client.put(f"/api/experiments/{experiment_id}/interpretation", json=interpretation)
    assert confirmed.status_code == 200
    base_policy = state["interpretation"]["executable_policy"]
    design = {
        "schema_version": "experiment-design-v2",
        "experiment_type": "policy_comparison",
        "control_policy": _policy(base_policy, "control"),
        "treatment_policy": _policy(base_policy, "treatment", 0.02),
        "event_plans": [],
        "status": "confirmed",
    }
    confirmed = client.put(f"/api/experiments/{experiment_id}/design", json=design)
    assert confirmed.status_code == 200
    baseline = client.post(
        f"/api/experiments/{experiment_id}/baseline/confirm",
        json={"confirm_data_snapshot": True, "expected_data_version": "nev-m29-2025-v2"},
    )
    assert baseline.status_code == 200
    return baseline.json()


def test_m34_quarter_api_idempotency_interactions_and_presentation(tmp_path) -> None:
    with TestClient(create_app(settings=Settings(runtime_dir=tmp_path))) as client:
        state = _prepare(client)
        experiment_id = state["experiment_id"]
        headers = {"Idempotency-Key": "run-q1"}
        first = client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_tick": "Q1"},
            headers=headers,
        )
        second = client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_tick": "Q1"},
            headers=headers,
        )
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert first.json()["branches"]["control"]["completed_ticks"] == ["Q1"]

        decisions = client.get(
            f"/api/experiments/{experiment_id}/decision-traces",
            params={"branch_id": "control", "tick": "Q1", "wave": "wave_0"},
        )
        assert decisions.status_code == 200
        assert len(decisions.json()) == 41
        assert len({item["agent_id"] for item in decisions.json()}) == 41

        interactions = client.get(
            f"/api/experiments/{experiment_id}/interactions",
            params={"branch_id": "control", "tick": "Q1"},
        )
        assert interactions.status_code == 200
        assert interactions.json()["schema_version"] == "interaction-market-v1"
        assert interactions.json()["fallback_count"] >= 41

        timeline = client.get(f"/api/experiments/{experiment_id}/presentation/timeline")
        assert timeline.status_code == 200
        assert timeline.json()["schema_version"] == "presentation-timeline-v3"
        settlement = next(item for item in timeline.json()["nodes"] if item["kind"] == "settlement")
        frame = client.get(
            f"/api/experiments/{experiment_id}/presentation/frames/{settlement['node_id']}"
        )
        assert frame.status_code == 200
        assert frame.json()["schema_version"] == "presentation-frame-v3"
        assert frame.json()["disclaimer"].startswith("模拟季度")


def test_m34_runtime_restores_after_api_restart(tmp_path) -> None:
    settings = Settings(runtime_dir=tmp_path)
    with TestClient(create_app(settings=settings)) as first:
        state = _prepare(first, idempotency_key="restart-create")
        experiment_id = state["experiment_id"]
        run = first.post(f"/api/experiments/{experiment_id}/run", json={"until_tick": "Q2"})
        assert run.status_code == 200
        replay = first.get(f"/api/experiments/{experiment_id}/replay").json()
    with TestClient(create_app(settings=settings)) as second:
        restored = second.get(f"/api/experiments/{experiment_id}/state")
        assert restored.status_code == 200
        assert restored.json()["branches"]["control"]["completed_ticks"] == ["Q1", "Q2"]
        assert second.get(f"/api/experiments/{experiment_id}/replay").json() == replay


def test_legacy_m32_runtime_is_gone_without_deleting_files(tmp_path) -> None:
    legacy_id = "exp_m32_deadbeef1234"
    legacy_dir = tmp_path / "v32" / legacy_id
    legacy_dir.mkdir(parents=True)
    marker = legacy_dir / "runtime-snapshot.json"
    marker.write_text('{"legacy": true}', encoding="utf-8")
    with TestClient(create_app(settings=Settings(runtime_dir=tmp_path))) as client:
        paths = (
            f"/api/experiments/{legacy_id}",
            f"/api/experiments/{legacy_id}/state",
            f"/api/experiments/{legacy_id}/run",
            f"/api/experiments/{legacy_id}/presentation/timeline",
            f"/api/experiments/{legacy_id}/compare",
            f"/api/experiments/{legacy_id}/replay",
        )
        for path in paths:
            response = (
                client.post(path, json={"until_tick": "Q1"})
                if path.endswith("/run")
                else client.get(path)
            )
            assert response.status_code == 410
            assert response.json()["detail"]["error_code"] == "LEGACY_V32_RUNTIME_UNSUPPORTED"
    assert marker.read_text(encoding="utf-8") == '{"legacy": true}'
