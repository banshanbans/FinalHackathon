from __future__ import annotations

from simulation.domain_constants import MAINLAND_PROVINCE_CODES
from simulation.models.m34 import (
    BranchRuntimeStateV9,
    InteractionWave,
    MacroTick,
    PresentationBranchSnapshotV3,
    PresentationFrameV3,
    PresentationInteractionSummaryV3,
    PresentationProvinceValueV3,
    PresentationTimelineNodeV3,
    PresentationTimelineV3,
    TransactionState,
    WorldStateV10,
)
from simulation.models.world import NationalMetrics
from simulation.services.replay import canonical_hash


class M34PresentationProjection:
    def __init__(self, world: WorldStateV10, *, comparison_available: bool) -> None:
        self.world = world
        self.comparison_available = comparison_available

    @staticmethod
    def _position(tick: MacroTick | None, wave: InteractionWave | None, offset: float) -> float:
        if tick is None:
            return offset
        quarter_start = tick.order / 4
        if wave is None:
            return min(1.0, quarter_start + 0.225 + offset)
        return min(1.0, quarter_start + 0.025 + wave.order * 0.055 + offset)

    def _nodes(self) -> list[PresentationTimelineNodeV3]:
        raw: list[dict[str, object]] = [
            {
                "node_id": "frame-policy-freeze",
                "kind": "policy",
                "tick": None,
                "wave": None,
                "title": "政策与同源基线冻结",
                "timeline_position": 0.0,
                "interaction_count": 0,
                "fallback_count": 0,
                "source_event_ids": [],
            }
        ]
        if self.world.design:
            control = self.world.branches.get("control")
            treatment = self.world.branches.get("treatment")
            for event in sorted(
                self.world.design.event_plans,
                key=lambda item: (
                    item.scheduled_tick.order,
                    item.release_wave.order,
                    item.event_plan_id,
                ),
            ):
                released = bool(
                    control
                    and treatment
                    and (
                        event.scheduled_tick in control.completed_ticks
                        and event.scheduled_tick in treatment.completed_ticks
                        or (
                            control.current_tick is event.scheduled_tick
                            and treatment.current_tick is event.scheduled_tick
                            and control.current_wave is not None
                            and treatment.current_wave is not None
                            and control.current_wave.order >= event.release_wave.order
                            and treatment.current_wave.order >= event.release_wave.order
                        )
                    )
                )
                if not released:
                    continue
                raw.append(
                    {
                        "node_id": f"frame-event-{event.event_plan_id}",
                        "kind": "event",
                        "tick": event.scheduled_tick,
                        "wave": event.release_wave,
                        "title": event.name,
                        "timeline_position": self._position(
                            event.scheduled_tick, event.release_wave, 0.005
                        ),
                        "interaction_count": 0,
                        "fallback_count": 0,
                        "source_event_ids": [event.event_plan_id],
                    }
                )
        control = self.world.branches.get("control")
        treatment = self.world.branches.get("treatment")
        if control and treatment:
            for tick in MacroTick:
                for wave in InteractionWave:
                    decisions = [
                        item
                        for branch in (control, treatment)
                        for item in branch.decisions
                        if item.tick is tick and item.wave is wave
                    ]
                    if not decisions:
                        continue
                    raw.append(
                        {
                            "node_id": f"frame-{tick.value.lower()}-{wave.value}",
                            "kind": "wave",
                            "tick": tick,
                            "wave": wave,
                            "title": f"{tick.value} {wave.value.replace('_', ' ')} 互动",
                            "timeline_position": self._position(tick, wave, 0.0),
                            "interaction_count": sum(
                                item.tick is tick and item.wave is wave
                                for branch in (control, treatment)
                                for item in branch.messages
                            ),
                            "fallback_count": sum(item.fallback_used for item in decisions),
                            "source_event_ids": [],
                        }
                    )
                if tick in control.completed_ticks and tick in treatment.completed_ticks:
                    raw.append(
                        {
                            "node_id": f"frame-{tick.value.lower()}-settlement",
                            "kind": "settlement",
                            "tick": tick,
                            "wave": None,
                            "title": f"{tick.value} 季度结算",
                            "timeline_position": self._position(tick, None, 0.0),
                            "interaction_count": 0,
                            "fallback_count": 0,
                            "source_event_ids": [],
                        }
                    )
        if self.comparison_available:
            raw.append(
                {
                    "node_id": "frame-annual-comparison",
                    "kind": "comparison",
                    "tick": MacroTick.Q4,
                    "wave": None,
                    "title": "年度同源比较与中央复盘",
                    "timeline_position": 1.0,
                    "interaction_count": 0,
                    "fallback_count": 0,
                    "source_event_ids": [],
                }
            )
        raw.sort(key=lambda item: (float(item["timeline_position"]), str(item["node_id"])))
        return [
            PresentationTimelineNodeV3(
                **item,
                sequence=index,
                source_hash=canonical_hash(item),
            )
            for index, item in enumerate(raw)
        ]

    def build_timeline(self) -> PresentationTimelineV3:
        nodes = self._nodes()
        completed = (
            list(self.world.branches["control"].completed_ticks)
            if "control" in self.world.branches
            else []
        )
        return PresentationTimelineV3(
            experiment_id=self.world.experiment_id,
            status=self.world.status,
            current_node_id=nodes[-1].node_id,
            nodes=nodes,
            completed_ticks=completed,
            source_world_hash=canonical_hash(self.world),
        )

    def get_frame(self, frame_id: str) -> PresentationFrameV3:
        node = next((item for item in self._nodes() if item.node_id == frame_id), None)
        if node is None:
            raise KeyError(f"presentation frame not found: {frame_id}")
        return self._frame(node)

    @staticmethod
    def _checkpoint(branch: BranchRuntimeStateV9, tick: MacroTick | None):
        if tick is not None and tick in branch.checkpoints:
            return branch.checkpoints[tick]
        if branch.completed_ticks:
            return branch.checkpoints[branch.completed_ticks[-1]]
        return None

    def _frame(self, node: PresentationTimelineNodeV3) -> PresentationFrameV3:
        branches: dict[str, PresentationBranchSnapshotV3] = {}
        checkpoints = {}
        for role in ("control", "treatment"):
            branch = self.world.branches.get(role)
            checkpoint = self._checkpoint(branch, node.tick) if branch else None
            checkpoints[role] = checkpoint
            branches[role] = PresentationBranchSnapshotV3(
                branch_id=role,
                tick=checkpoint.tick if checkpoint else None,
                national_metrics=(
                    checkpoint.settlement.national_metrics if checkpoint else NationalMetrics()
                ),
                checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
            )
        province_values = []
        for code in MAINLAND_PROVINCE_CODES:
            control = (
                checkpoints["control"].settlement.province_states[code].development_index
                if checkpoints["control"]
                else None
            )
            treatment = (
                checkpoints["treatment"].settlement.province_states[code].development_index
                if checkpoints["treatment"]
                else None
            )
            province_values.append(
                PresentationProvinceValueV3(
                    province_code=code,
                    control=control,
                    treatment=treatment,
                    delta=(
                        round(treatment - control, 4)
                        if control is not None and treatment is not None
                        else None
                    ),
                )
            )
        interactions = []
        for role, branch in self.world.branches.items():
            for session in branch.sessions:
                if node.tick is not None and session.tick is not node.tick:
                    continue
                if node.wave is not None:
                    session_messages = [
                        message
                        for message in branch.messages
                        if message.session_id == session.session_id
                    ]
                    if not any(message.wave is node.wave for message in session_messages):
                        continue
                else:
                    session_messages = [
                        message
                        for message in branch.messages
                        if message.session_id == session.session_id
                    ]
                interactions.append(
                    PresentationInteractionSummaryV3(
                        session_id=session.session_id,
                        branch_id=role,
                        tick=session.tick,
                        participants=session.participant_ids,
                        state=session.state,
                        message_count=len(session.message_ids),
                        summary=(
                            "合法互动已结算并进入环境贡献。"
                            if session.state is TransactionState.SETTLED
                            else f"互动状态：{session.state.value}。"
                        ),
                        fallback=any(
                            decision.fallback_used
                            and decision.agent_id in session.participant_ids
                            and decision.tick is session.tick
                            for decision in branch.decisions
                        ),
                    )
                )
        interactions.sort(
            key=lambda item: (
                item.state is not TransactionState.SETTLED,
                -item.message_count,
                item.branch_id,
                item.session_id,
            )
        )
        summary = {
            "policy": "中央政策解读、实验设计与同源基线已冻结。",
            "event": "外生事件按冻结季度与逻辑 Wave 批次发布。",
            "wave": f"本波聚合 {len(interactions)} 条互动会话。",
            "settlement": "确定性环境已提交不可变季度 Checkpoint。",
            "comparison": "Q4 年度结果完成同源 A/B 与中央复盘。",
        }[node.kind]
        evidence = [f"session:{item.session_id}" for item in interactions]
        evidence.extend(
            f"checkpoint:{checkpoint.checkpoint_id}"
            for checkpoint in checkpoints.values()
            if checkpoint
        )
        payload = {
            "frame_id": node.node_id,
            "experiment_id": self.world.experiment_id,
            "sequence": node.sequence,
            "kind": node.kind,
            "tick": node.tick,
            "wave": node.wave,
            "title": node.title,
            "summary": summary,
            "branches": branches,
            "province_values": province_values,
            "interactions": interactions,
            "spotlight_session_ids": [item.session_id for item in interactions[:3]],
            "event_plan_ids": node.source_event_ids,
            "evidence_refs": evidence,
        }
        return PresentationFrameV3(**payload, source_hash=canonical_hash(payload))
