from fastapi.testclient import TestClient
from policyscope_api.main import create_app

from simulation.m29_data import load_m29_snapshot


def test_v32_api_journey_and_legacy_operation_boundary() -> None:
    with TestClient(create_app()) as client:
        metadata = client.get("/api/meta/v32/baseline")
        assert metadata.status_code == 200
        assert metadata.json()["data_version"] == "nev-m29-2025-v2"
        assert metadata.json()["quality_counts"] == {
            "trusted": metadata.json()["counts"]["raw_facts"]
        }
        assert metadata.json()["province_count"] == 31
        assert len(client.get("/api/meta/v32/provinces").json()) == 31
        assert len(client.get("/api/meta/v32/automakers").json()) == 10
        event_catalog = client.get("/api/meta/presentation-event-catalog")
        assert event_catalog.status_code == 200
        assert event_catalog.json()["schema_version"] == "presentation-event-catalog-v1"
        assert len(event_catalog.json()["templates"]) == 5
        assert all(
            len(item["trigger_points"]) == 3
            and item["supported_intensities"] == ["low", "medium", "high"]
            for item in event_catalog.json()["templates"]
        )
        created = client.post(
            "/api/experiments",
            json={
                "policy_text": "西部 95%，中部 90%，东部 85%，促进消费与产业布局。",
                "product_version": "v3_2_m32",
            },
        )
        assert created.status_code == 201
        state = created.json()
        assert state["product_version"] == "v3_2_m32"
        assert state["schema_version"] == "world-state-v9"
        experiment_id = state["experiment_id"]
        interpretation = state["interpretation"]
        interpretation["status"] = "confirmed"
        assert (
            client.put(
                f"/api/experiments/{experiment_id}/interpretation",
                json=interpretation,
            ).status_code
            == 200
        )
        design = {
            "experiment_type": "policy_comparison",
            "control_policy": {
                "policy_id": "control",
                "west_central_share": 0.95,
                "central_central_share": 0.90,
                "east_central_share": 0.85,
            },
            "treatment_policy": {
                "policy_id": "treatment",
                "west_central_share": 0.98,
                "central_central_share": 0.92,
                "east_central_share": 0.86,
            },
            "event_plan": None,
        }
        assert (
            client.put(f"/api/experiments/{experiment_id}/design", json=design).status_code == 200
        )
        assert (
            client.post(
                f"/api/experiments/{experiment_id}/baseline/confirm",
                json={
                    "confirm_data_snapshot": True,
                    "expected_data_version": metadata.json()["data_version"],
                },
            ).status_code
            == 200
        )
        run = client.post(f"/api/experiments/{experiment_id}/run", json={})
        assert run.status_code == 200
        assert run.json()["status"] == "completed"
        traces = client.get(f"/api/experiments/{experiment_id}/decision-traces")
        assert traces.status_code == 200
        assert len(traces.json()) == 246
        first_trace = traces.json()[0]
        evidence = client.get(
            f"/api/experiments/{experiment_id}/evidence/action:{first_trace['final_action_id']}"
        )
        assert evidence.status_code == 200
        audit = client.get(f"/api/experiments/{experiment_id}/audit?limit=500")
        assert audit.status_code == 200
        assert len(audit.json()["records"]) == 500
        assert audit.json()["records"][0]["payload"]["decision_trace_id"] == first_trace["trace_id"]
        market = client.get(f"/api/experiments/{experiment_id}/strategy-market")
        assert market.status_code == 200
        assert market.json()["automaker_signal_count"] == 620
        assert market.json()["proposal_count"] > 0
        assert market.json()["response_count"] == market.json()["proposal_count"]
        assert market.json()["schema_version"] == "strategy-market-v3"
        assert market.json()["enterprise_offer_count"] > 0
        assert market.json()["enterprise_response_count"] == market.json()["enterprise_offer_count"]
        assert market.json()["enterprise_matched_count"] <= 50
        assert market.json()["competition_outcome_count"] > 0
        assert market.json()["counteroffer_count"] > 0
        assert market.json()["counteroffer_response_count"] == market.json()["counteroffer_count"]
        branch_payload = market.json()["branches"]["control"]
        competition = branch_payload["competition_outcomes"][0]
        counteroffer = branch_payload["automaker_counter_offers"][0]
        counterresponse = branch_payload["province_counter_offer_responses"][0]
        utility = next(iter(branch_payload["province_utilities"].values()))
        assert (
            client.get(
                f"/api/experiments/{experiment_id}/evidence/competition:{competition['outcome_id']}"
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/api/experiments/{experiment_id}/evidence/topk:{branch_payload['automaker_initial_actions'][competition['automaker_id']]['action_id']}"
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/api/experiments/{experiment_id}/evidence/counteroffer:{counteroffer['counter_offer_id']}"
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/api/experiments/{experiment_id}/evidence/counterresponse:{counterresponse['response_id']}"
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/api/experiments/{experiment_id}/evidence/utility:{utility['utility_id']}"
            ).status_code
            == 200
        )
        final_actions = [
            action
            for branch in market.json()["branches"].values()
            for action in branch["automaker_final_actions"].values()
        ]
        assert all(len(action["province_market_actions"]) == 31 for action in final_actions)
        assert all("candidate_provinces" not in action for action in final_actions)
        assert all(
            {signal["decision"] for signal in action["province_signals"]}
            <= {"expand", "maintain", "reduce"}
            for action in final_actions
        )
        summary = client.get(f"/api/experiments/{experiment_id}/presentation-summary")
        assert summary.status_code == 200
        assert [item["scene"] for item in summary.json()["scenes"]] == [
            "policy_input",
            "enterprise_feedback",
            "province_coordination",
            "resource_reallocation",
            "policy_conclusion",
        ]
        coordination_refs = summary.json()["scenes"][2]["evidence_refs"]
        reallocation_refs = summary.json()["scenes"][3]["evidence_refs"]
        assert set(coordination_refs) & set(reallocation_refs)
        state_before_projection = client.get(f"/api/experiments/{experiment_id}/state").json()
        timeline = client.get(f"/api/experiments/{experiment_id}/presentation/timeline")
        assert timeline.status_code == 200
        timeline_payload = timeline.json()
        assert timeline_payload["schema_version"] == "presentation-timeline-v1"
        assert timeline_payload["current_frame_id"] == "frame-comparison-result"
        assert timeline_payload["available_modes"] == ["live", "story", "compare"]
        assert len(timeline_payload["frames"]) == 10
        selected_frame_id = "frame-treatment-province_revision"
        selected_frame = client.get(
            f"/api/experiments/{experiment_id}/presentation/frames/{selected_frame_id}"
        )
        assert selected_frame.status_code == 200
        assert selected_frame.json()["frame_id"] == selected_frame_id
        assert len(selected_frame.json()["province_values"]) == 31
        replay_ids = {
            item["event_id"]
            for item in client.get(f"/api/experiments/{experiment_id}/replay").json()
        }
        assert set(selected_frame.json()["source_event_ids"]) <= replay_ids
        missing_frame = client.get(
            f"/api/experiments/{experiment_id}/presentation/frames/not-a-frame"
        )
        assert missing_frame.status_code == 404
        assert missing_frame.json()["detail"]["error_code"] == "PRESENTATION_FRAME_NOT_FOUND"
        assert (
            client.get(f"/api/experiments/{experiment_id}/state").json() == state_before_projection
        )
        province = client.get(f"/api/experiments/{experiment_id}/provinces/11")
        assert province.status_code == 200
        assert province.json()["m29_profile"]["fact_summary"]
        assert "fiscally_prudent" not in province.json()["persona"]["summary"]
        assert "talent_cost" not in province.json()["persona"]["summary"]
        automaker_id = counteroffer["automaker_id"]
        automaker = client.get(f"/api/experiments/{experiment_id}/automakers/{automaker_id}")
        assert automaker.status_code == 200
        for branch in automaker.json()["branches"].values():
            offer_ids = {item["counter_offer_id"] for item in branch["counter_offers"]}
            response_offer_ids = {
                item["counter_offer_id"] for item in branch["counter_offer_responses"]
            }
            assert response_offer_ids <= offer_ids
        compare = client.get(f"/api/experiments/{experiment_id}/compare")
        assert compare.status_code == 200
        assert compare.json()["schema_version"] == "comparison-v9"
        assert 0 <= compare.json()["counteroffer_acceptance_rate"] <= 1
        incompatible = client.post(
            f"/api/experiments/{experiment_id}/event-scenario/approve",
            json={"template_id": "oil_price_rise", "intensity": "medium"},
        )
        assert incompatible.status_code == 409
        assert incompatible.json()["detail"]["error_code"] == "V32_INCOMPATIBLE_OPERATION"


def test_v32_m29_version_conflict_and_evidence_prefixes() -> None:
    with TestClient(create_app()) as client:
        state = client.post(
            "/api/experiments",
            json={
                "policy_text": "西部 95%，中部 90%，东部 85%。",
                "product_version": "v3_2_m32",
            },
        ).json()
        experiment_id = state["experiment_id"]
        initial_timeline = client.get(f"/api/experiments/{experiment_id}/presentation/timeline")
        assert initial_timeline.status_code == 200
        assert [item["frame_id"] for item in initial_timeline.json()["frames"]] == [
            "frame-setup-policy"
        ]
        interpretation = {**state["interpretation"], "status": "confirmed"}
        client.put(f"/api/experiments/{experiment_id}/interpretation", json=interpretation)
        client.put(
            f"/api/experiments/{experiment_id}/design",
            json={
                "experiment_type": "policy_comparison",
                "control_policy": {
                    "policy_id": "control",
                    "west_central_share": 0.95,
                    "central_central_share": 0.90,
                    "east_central_share": 0.85,
                },
                "treatment_policy": {
                    "policy_id": "treatment",
                    "west_central_share": 0.98,
                    "central_central_share": 0.92,
                    "east_central_share": 0.86,
                },
                "event_plan": None,
            },
        )
        conflict = client.post(
            f"/api/experiments/{experiment_id}/baseline/confirm",
            json={
                "confirm_data_snapshot": True,
                "expected_data_version": "stale-m29-version",
            },
        )
        assert conflict.status_code == 409
        assert "BASELINE_DATA_VERSION_MISMATCH" in conflict.json()["detail"]["message"]

        profile = client.get("/api/meta/v32/provinces").json()[0]
        fact_id = profile["fact_refs"][0]
        feature_id = next(iter(profile["feature_refs"].values()))
        fact = client.get(f"/api/experiments/{experiment_id}/evidence/fact:{fact_id}")
        feature = client.get(f"/api/experiments/{experiment_id}/evidence/feature:{feature_id}")
        snapshot = load_m29_snapshot()
        relation_id = next(iter(snapshot.relation_facts.values())).relation_id
        source_id = snapshot.facts[fact_id].source_id
        relation = client.get(f"/api/experiments/{experiment_id}/evidence/relation:{relation_id}")
        source = client.get(f"/api/experiments/{experiment_id}/evidence/source:{source_id}")
        assert fact.status_code == 200 and fact.json()["type"] == "raw_fact"
        assert feature.status_code == 200 and feature.json()["type"] == "derived_feature"
        assert relation.status_code == 200 and relation.json()["type"] == "relation_fact"
        assert source.status_code == 200 and source.json()["type"] == "source_record"
        assert (
            client.get(f"/api/experiments/{experiment_id}/evidence/fact:not-found").status_code
            == 404
        )
