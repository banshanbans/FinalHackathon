from fastapi.testclient import TestClient
from policyscope_api.main import create_app
from policyscope_api.settings import Settings

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider


def _client(tmp_path):
    return TestClient(
        create_app(
            adapter=AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path),
            settings=Settings(run_mode="fake", runtime_dir=tmp_path),
        )
    )


def _create_and_confirm_interpretation(client: TestClient):
    created = client.post(
        "/api/experiments",
        json={"policy_text": "西部 98%，中部 92%，东部 86%。", "product_version": "v3_2_m34"},
    )
    assert created.status_code == 201
    world = created.json()
    confirmed = client.put(
        f"/api/experiments/{world['experiment_id']}/interpretation",
        json={**world["interpretation"], "status": "confirmed"},
    )
    assert confirmed.status_code == 200
    return world


def test_m34_metadata_and_create_idempotency(tmp_path):
    with _client(tmp_path) as client:
        assert client.get("/api/health").json()["run_mode"] == "fake"
        assert len(client.get("/api/meta/provinces").json()) == 31
        assert len(client.get("/api/meta/automakers").json()) == 10
        assert [
            len(item["province_codes"]) for item in client.get("/api/meta/policy-regions").json()
        ] == [12, 10, 9]
        headers = {"Idempotency-Key": "m34-create"}
        body = {"policy_text": "西部 98%，中部 92%，东部 86%。", "product_version": "v3_2_m34"}
        first = client.post("/api/experiments", json=body, headers=headers)
        second = client.post("/api/experiments", json=body, headers=headers)
        assert first.status_code == second.status_code == 201
        assert first.json() == second.json()
        assert first.json()["schema_version"] == "world-state-v10"
        assert first.json()["experiment_id"].startswith("exp_m34_")


def test_event_counterfactual_keeps_policy_identical(tmp_path):
    with _client(tmp_path) as client:
        world = _create_and_confirm_interpretation(client)
        experiment_id = world["experiment_id"]
        base = world["interpretation"]["executable_policy"]
        event = {
            "schema_version": "event-plan-v2",
            "event_plan_id": "event_counterfactual",
            "template_id": "battery_node_upgrade_sichuan",
            "name": "西部电池节点能力升级",
            "description": "冻结情景假设",
            "scheduled_tick": "Q3",
            "release_wave": "wave_1",
            "branch_scope": "treatment_only",
            "affected_subjects": ["province", "automaker", "supply_chain"],
            "mechanism_channels": ["battery", "industry"],
            "evidence_refs": ["scenario:battery-node"],
        }
        design = {
            "schema_version": "experiment-design-v2",
            "experiment_type": "event_counterfactual",
            "control_policy": {**base, "policy_id": "control"},
            "treatment_policy": {**base, "policy_id": "treatment"},
            "event_plans": [event],
            "status": "confirmed",
        }
        assert (
            client.put(f"/api/experiments/{experiment_id}/design", json=design).status_code == 200
        )
        assert (
            client.post(
                f"/api/experiments/{experiment_id}/baseline/confirm",
                json={"confirm_data_snapshot": True},
            ).status_code
            == 200
        )
        final = client.post(f"/api/experiments/{experiment_id}/run", json={"until_tick": "Q4"})
        assert final.status_code == 200
        comparison = client.get(f"/api/experiments/{experiment_id}/compare").json()
        assert comparison["schema_version"] == "comparison-v10"
        assert comparison["active_difference"] == "event"
        assert comparison["same_policy"] is True
        assert comparison["same_event"] is False
        assert final.json()["central_call_count"] == 2
