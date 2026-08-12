from fastapi.testclient import TestClient
from policyscope_api.main import create_app
from policyscope_api.settings import Settings

from simulation.adapters.asyncio_adapter import AsyncioSimulationAdapter
from simulation.llm.fake_provider import FakeLLMProvider


def _client(tmp_path):
    adapter = AsyncioSimulationAdapter(FakeLLMProvider(), runtime_dir=tmp_path)
    settings = Settings(run_mode="fake", runtime_dir=tmp_path)
    return TestClient(create_app(adapter=adapter, settings=settings))


def test_complete_v2_api_flow_and_idempotency(tmp_path) -> None:
    with _client(tmp_path) as client:
        assert client.get("/api/health").json()["version"] == "0.2.0"
        assert len(client.get("/api/meta/enterprise-archetypes").json()) == 6
        policy = client.get("/api/meta/default-policy").json()
        create_headers = {"Idempotency-Key": "create-demo"}
        create_body = {"objective": "推动制造业设备更新并改善中小企业融资"}
        create = client.post("/api/experiments", json=create_body, headers=create_headers)
        assert create.status_code == 201
        repeated = client.post("/api/experiments", json=create_body, headers=create_headers)
        assert repeated.json()["experiment_id"] == create.json()["experiment_id"]
        conflict = client.post(
            "/api/experiments",
            json={"objective": "不同目标"},
            headers=create_headers,
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["error_code"] == "IDEMPOTENCY_CONFLICT"
        world = create.json()
        experiment_id = world["experiment_id"]
        assert world["schema_version"] == "world-state-v2"
        assert len(world["enterprise_profiles"]) == 186

        forbidden = client.post(f"/api/experiments/{experiment_id}/run", json={"until_phase": "T1"})
        assert forbidden.status_code == 403
        missing_policy = client.post(f"/api/experiments/{experiment_id}/directive/approve", json={})
        assert missing_policy.status_code == 422
        approve = client.post(
            f"/api/experiments/{experiment_id}/directive/approve",
            json={"policy": policy},
            headers={"Idempotency-Key": "approve-t0"},
        )
        assert approve.status_code == 200
        repeated_approval = client.post(
            f"/api/experiments/{experiment_id}/directive/approve",
            json={"policy": policy},
            headers={"Idempotency-Key": "approve-t0-repeat"},
        )
        assert repeated_approval.status_code == 409
        assert repeated_approval.json()["detail"]["error_code"] == "DIRECTIVE_NOT_AWAITING_APPROVAL"
        t3 = client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_phase": "T3"},
            headers={"Idempotency-Key": "run-t3"},
        )
        assert t3.status_code == 200
        assert len(t3.json()["province_feedback"]) == 31
        assert len(t3.json()["enterprise_actions"]) == 186
        proposal = t3.json()["intervention_proposals"][0]

        unapproved_branch = client.post(
            f"/api/experiments/{experiment_id}/branches",
            json={"intervention_id": proposal["proposal_id"]},
        )
        assert unapproved_branch.status_code == 403
        intervention_response = client.post(
            f"/api/experiments/{experiment_id}/interventions/{proposal['proposal_id']}/approve",
            json={"policy": proposal["proposed_policy"]},
            headers={"Idempotency-Key": "approve-t3"},
        )
        assert intervention_response.status_code == 200
        intervention = intervention_response.json()
        assert intervention["schema_version"] == "central-intervention-v2"
        branch_response = client.post(
            f"/api/experiments/{experiment_id}/branches",
            json={"intervention_id": intervention["intervention_id"]},
            headers={"Idempotency-Key": "create-treatment"},
        )
        assert branch_response.status_code == 201
        branch_id = branch_response.json()["branch_id"]
        control_run = client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_phase": "T5", "branch_id": "control"},
            headers={"Idempotency-Key": "run-control-t5"},
        )
        assert control_run.status_code == 200
        treatment_run = client.post(
            f"/api/branches/{branch_id}/run",
            json={"until_phase": "T5"},
            headers={"Idempotency-Key": "run-treatment-t5"},
        )
        assert treatment_run.status_code == 200
        comparison = client.get(f"/api/experiments/{experiment_id}/compare")
        assert comparison.status_code == 200
        assert comparison.json()["schema_version"] == "comparison-v2"
        assert sum(item["count"] for item in comparison.json()["action_migrations"]) == 186
        assert comparison.json()["central_review"]["review_mode"] == "comparison"
        evidence = client.get(f"/api/experiments/{experiment_id}/evidence/metric:national:T5")
        assert evidence.status_code == 200
        assert evidence.json()["seed"] == 20260812
        replay = client.get(f"/api/experiments/{experiment_id}/replay")
        assert replay.status_code == 200
        event_types = {item["type"] for item in replay.json()}
        assert {
            "enterprise.batch.started",
            "enterprise.batch.completed",
            "enterprise.aggregate.updated",
            "province.feedback.completed",
        } <= event_types


def test_reject_intervention_returns_single_branch_review(tmp_path) -> None:
    with _client(tmp_path) as client:
        policy = client.get("/api/meta/default-policy").json()
        world = client.post("/api/experiments", json={"objective": "测试拒绝干预"}).json()
        experiment_id = world["experiment_id"]
        client.post(
            f"/api/experiments/{experiment_id}/directive/approve",
            json={"policy": policy},
        )
        t3 = client.post(f"/api/experiments/{experiment_id}/run", json={"until_phase": "T3"}).json()
        proposal_id = t3["intervention_proposals"][0]["proposal_id"]
        rejected = client.post(
            f"/api/experiments/{experiment_id}/interventions/{proposal_id}/reject",
            json={"reason": "保留原始方案观察单线结果"},
        )
        assert rejected.status_code == 200
        final = client.post(f"/api/experiments/{experiment_id}/run", json={"until_phase": "T5"})
        assert final.status_code == 200
        assert final.json()["central_review"]["review_mode"] == "single_branch"
        comparison = client.get(f"/api/experiments/{experiment_id}/compare")
        assert comparison.status_code == 409
        assert comparison.json()["detail"]["error_code"] == "COMPARISON_NOT_AVAILABLE"
