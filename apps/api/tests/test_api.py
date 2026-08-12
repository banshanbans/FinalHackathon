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


def test_complete_v3_api_flow_and_idempotency(tmp_path):
    with _client(tmp_path) as client:
        assert client.get("/api/health").json()["version"] == "0.5.0"
        assert len(client.get("/api/meta/provinces").json()) == 31
        assert len(client.get("/api/meta/automakers").json()) == 10
        assert len(client.get("/api/meta/event-scenarios").json()) == 5
        regions = client.get("/api/meta/policy-regions").json()
        assert [len(item["province_codes"]) for item in regions] == [12, 10, 9]
        assert [item["central_share"] for item in regions] == [0.95, 0.90, 0.85]
        policy = client.get("/api/meta/default-policy").json()
        headers = {"Idempotency-Key": "create-v3"}
        created = client.post(
            "/api/experiments", json={"objective": "新能源汽车区域补贴实验"}, headers=headers
        )
        assert created.status_code == 201
        assert (
            client.post(
                "/api/experiments", json={"objective": "新能源汽车区域补贴实验"}, headers=headers
            ).json()["experiment_id"]
            == created.json()["experiment_id"]
        )
        assert (
            client.post(
                "/api/experiments", json={"objective": "另一个实验"}, headers=headers
            ).status_code
            == 409
        )
        world = created.json()
        experiment_id = world["experiment_id"]
        assert world["schema_version"] == "world-state-v5"
        assert len(world["province_personas"]) == 31 and len(world["automaker_profiles"]) == 10
        assert (
            client.post(
                f"/api/experiments/{experiment_id}/run", json={"until_phase": "Y1_Q1"}
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/experiments/{experiment_id}/directive/approve", json={"policy": policy}
            ).status_code
            == 200
        )
        review = client.post(
            f"/api/experiments/{experiment_id}/run", json={"until_phase": "YEAR1_REVIEW"}
        )
        assert review.status_code == 200
        assert len(review.json()["province_feedback"]) == 31
        assert len(review.json()["automaker_actions"]) == 10
        proposal = review.json()["intervention_proposals"][0]
        intervention = client.post(
            f"/api/experiments/{experiment_id}/interventions/{proposal['proposal_id']}/approve",
            json={"policy": proposal["proposed_policy"]},
        )
        assert (
            intervention.status_code == 200
            and intervention.json()["schema_version"] == "central-intervention-v3"
        )
        branch = client.post(
            f"/api/experiments/{experiment_id}/branches",
            json={
                "kind": "policy_intervention",
                "intervention_id": intervention.json()["intervention_id"],
            },
        )
        assert branch.status_code == 201
        branches = client.get(f"/api/experiments/{experiment_id}/branches")
        assert branches.status_code == 200
        assert {item["kind"] for item in branches.json()} == {"control", "treatment"}
        restored_control = client.get(f"/api/experiments/{experiment_id}/state").json()
        assert restored_control["intervention_decision"] == "approved"
        assert (
            restored_control["approved_intervention"]["intervention_id"]
            == intervention.json()["intervention_id"]
        )
        assert (
            client.post(
                f"/api/experiments/{experiment_id}/run",
                json={"until_phase": "Y2_Q2", "branch_id": "control"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/branches/{branch.json()['branch_id']}/run", json={"until_phase": "Y2_Q2"}
            ).status_code
            == 200
        )
        blocked = client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_phase": "Y2_Q3", "branch_id": "control"},
        )
        assert blocked.status_code == 403
        assert blocked.json()["detail"]["error_code"] == "EVENT_APPROVAL_REQUIRED"
        scenario = client.post(
            f"/api/experiments/{experiment_id}/event-scenario/approve",
            json={"template_id": "oil_price_rise", "intensity": "medium"},
            headers={"Idempotency-Key": "event-once"},
        )
        assert scenario.status_code == 200 and scenario.json()["activation_phase"] == "Y2_Q3"
        assert (
            client.post(
                f"/api/experiments/{experiment_id}/event-scenario/approve",
                json={"template_id": "oil_price_rise", "intensity": "medium"},
                headers={"Idempotency-Key": "event-once"},
            ).json()["scenario_id"]
            == scenario.json()["scenario_id"]
        )
        assert (
            client.post(
                f"/api/experiments/{experiment_id}/run",
                json={"until_phase": "Y2_Q4", "branch_id": "control"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/branches/{branch.json()['branch_id']}/run",
                json={"until_phase": "Y2_Q4"},
            ).status_code
            == 200
        )
        comparison = client.get(f"/api/experiments/{experiment_id}/compare")
        assert (
            comparison.status_code == 200 and comparison.json()["schema_version"] == "comparison-v5"
        )
        assert comparison.json()["active_difference_proof"]["active_difference"] == "policy"
        assert len(comparison.json()["province_strategy_transitions"]) == 31
        assert len(comparison.json()["automaker_strategy_transitions"]) == 10
        assert client.get(f"/api/experiments/{experiment_id}/automakers/byd").status_code == 200
        assert client.get(f"/api/experiments/{experiment_id}/provinces/41").status_code == 200
        audit = client.get(
            f"/api/experiments/{experiment_id}/audit",
            params={"record_type": "agent_invocation", "limit": 5},
        )
        assert audit.status_code == 200 and len(audit.json()["records"]) == 5
        assert client.get(f"/api/experiments/{experiment_id}/replay").json()


def test_reject_intervention_is_single_branch(tmp_path):
    with _client(tmp_path) as client:
        policy = client.get("/api/meta/default-policy").json()
        world = client.post("/api/experiments", json={"objective": "拒绝干预验证"}).json()
        experiment_id = world["experiment_id"]
        client.post(f"/api/experiments/{experiment_id}/directive/approve", json={"policy": policy})
        review = client.post(
            f"/api/experiments/{experiment_id}/run", json={"until_phase": "YEAR1_REVIEW"}
        ).json()
        proposal_id = review["intervention_proposals"][0]["proposal_id"]
        assert (
            client.post(
                f"/api/experiments/{experiment_id}/interventions/{proposal_id}/reject",
                json={"reason": "保留原方案"},
            ).status_code
            == 200
        )
        final = client.post(
            f"/api/experiments/{experiment_id}/run", json={"until_phase": "COMPLETE"}
        )
        assert (
            final.status_code == 200
            and final.json()["central_review"]["review_mode"] == "single_branch"
        )
        assert client.get(f"/api/experiments/{experiment_id}/compare").status_code == 409


def test_event_counterfactual_api_keeps_policy_identical(tmp_path):
    with _client(tmp_path) as client:
        policy = client.get("/api/meta/default-policy").json()
        world = client.post(
            "/api/experiments",
            json={
                "objective": "事件反事实接口验证",
                "comparison_mode": "event_counterfactual",
            },
        ).json()
        experiment_id = world["experiment_id"]
        client.post(f"/api/experiments/{experiment_id}/directive/approve", json={"policy": policy})
        client.post(f"/api/experiments/{experiment_id}/run", json={"until_phase": "YEAR1_REVIEW"})
        branch = client.post(
            f"/api/experiments/{experiment_id}/branches",
            json={"kind": "event_counterfactual"},
        ).json()
        client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_phase": "Y2_Q2", "branch_id": "control"},
        )
        client.post(f"/api/branches/{branch['branch_id']}/run", json={"until_phase": "Y2_Q2"})
        approved = client.post(
            f"/api/experiments/{experiment_id}/event-scenario/approve",
            json={"template_id": "battery_node_upgrade_sichuan", "intensity": "high"},
        )
        assert approved.status_code == 200
        client.post(
            f"/api/experiments/{experiment_id}/run",
            json={"until_phase": "Y2_Q4", "branch_id": "control"},
        )
        client.post(f"/api/branches/{branch['branch_id']}/run", json={"until_phase": "Y2_Q4"})
        comparison = client.get(f"/api/experiments/{experiment_id}/compare").json()
        assert comparison["policy_diff"] == []
        assert comparison["event_diff"]["changed"]
        assert comparison["active_difference_proof"]["active_difference"] == "event"
        control = client.get(f"/api/experiments/{experiment_id}/state").json()
        treatment = client.get(
            f"/api/experiments/{experiment_id}/state",
            params={"branch_id": branch["branch_id"]},
        ).json()
        assert len(control["province_event_signals"]) == 0
        assert len(treatment["province_event_signals"]) == 31
