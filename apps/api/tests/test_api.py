from fastapi.testclient import TestClient
from policyscope_api.main import create_app
from policyscope_api.settings import Settings

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider


def test_complete_api_flow(tmp_path) -> None:
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    settings = Settings(run_mode="fake", runtime_dir=tmp_path)
    with TestClient(create_app(adapter=adapter, settings=settings)) as client:
        assert client.get("/api/health").status_code == 200
        create = client.post("/api/experiments", json={"objective": "促进创新并兼顾区域均衡"})
        assert create.status_code == 201
        world = create.json()
        experiment_id = world["experiment_id"]

        mismatched_mode = client.post(
            "/api/experiments",
            json={"objective": "测试运行模式门禁", "run_mode": "live"},
        )
        assert mismatched_mode.status_code == 409

        forbidden_run = client.post(
            f"/api/experiments/{experiment_id}/run", json={"until_phase": "T1"}
        )
        assert forbidden_run.status_code == 403

        approve = client.post(f"/api/experiments/{experiment_id}/directive/approve", json={})
        assert approve.status_code == 200
        t3 = client.post(f"/api/experiments/{experiment_id}/run", json={"until_phase": "T3"})
        assert t3.status_code == 200
        proposal = t3.json()["intervention_proposals"][0]

        unapproved_continuation = client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_phase": "T5", "branch_id": "control"},
        )
        assert unapproved_continuation.status_code == 403
        unapproved_branch = client.post(
            f"/api/experiments/{experiment_id}/branches",
            json={"intervention_id": proposal["proposal_id"]},
        )
        assert unapproved_branch.status_code == 403

        intervention_response = client.post(
            f"/api/experiments/{experiment_id}/interventions/{proposal['proposal_id']}/approve",
            json={},
        )
        assert intervention_response.status_code == 200
        intervention = intervention_response.json()
        branch_response = client.post(
            f"/api/experiments/{experiment_id}/branches",
            json={"intervention_id": intervention["intervention_id"]},
        )
        assert branch_response.status_code == 201
        branch_id = branch_response.json()["branch_id"]

        control_run = client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_phase": "T5", "branch_id": "control"},
        )
        assert control_run.status_code == 200
        treatment_run = client.post(f"/api/branches/{branch_id}/run", json={"until_phase": "T5"})
        assert treatment_run.status_code == 200

        comparison = client.get(f"/api/experiments/{experiment_id}/compare")
        assert comparison.status_code == 200
        assert len(comparison.json()["province_deltas"]) == 31
        assert comparison.json()["central_review"] is not None

        repeated_final_phase = client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_phase": "T5", "branch_id": "control"},
        )
        assert repeated_final_phase.status_code == 409

        replay = client.get(f"/api/experiments/{experiment_id}/replay")
        assert replay.status_code == 200
        assert len(replay.json()) > 100
