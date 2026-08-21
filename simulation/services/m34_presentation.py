from __future__ import annotations

from simulation.catalog import automaker_catalog, policy_region_catalog
from simulation.domain_constants import MAINLAND_PROVINCE_CODES
from simulation.models.m34 import (
    AgentTickDecision,
    BranchRuntimeStateV9,
    EngagementMode,
    InteractionMessage,
    InteractionSession,
    InteractionWave,
    MacroTick,
    MessageKind,
    PresentationActionV4,
    PresentationBranchProvinceValueV4,
    PresentationBranchViewV5,
    PresentationCausalBeatV4,
    PresentationDivergenceV5,
    PresentationFrameV5,
    PresentationGameEdgeV5,
    PresentationMetricChangeV5,
    PresentationProvinceChangeV5,
    PresentationSettlementV5,
    PresentationSharedScaleV4,
    PresentationSpotlightV5,
    PresentationSubjectV4,
    PresentationTimelineNodeV3,
    PresentationTimelineV4,
    TickCheckpoint,
    TransactionState,
    WorldStateV10,
)
from simulation.models.world import NationalMetrics
from simulation.services.replay import canonical_hash

WAVE_LABELS = {
    InteractionWave.WAVE_0: "首次行动",
    InteractionWave.WAVE_1: "条件回应",
    InteractionWave.WAVE_2: "协议收敛",
}

STATE_LABELS = {
    TransactionState.PROPOSED: "已提出",
    TransactionState.COUNTERED: "已反报价",
    TransactionState.ACCEPTED: "已接受",
    TransactionState.REJECTED: "已拒绝",
    TransactionState.DEFERRED: "暂缓处理",
    TransactionState.SETTLED: "已达成",
    TransactionState.WITHDRAWN: "已撤回",
    TransactionState.EXPIRED: "已过期",
    TransactionState.RESOURCE_INVALID: "资源无效",
}

ENGAGEMENT_LABELS = {
    EngagementMode.IGNORE: "暂不行动",
    EngagementMode.MONITOR: "持续关注",
    EngagementMode.INITIATE: "主动发起",
    EngagementMode.RESPOND: "作出回应",
    EngagementMode.REVISE: "调整方案",
}

MESSAGE_LABELS = {
    MessageKind.PUBLIC_POLICY: "政策信息",
    MessageKind.PUBLIC_EVENT: "事件信息",
    MessageKind.PUBLIC_ACTION_SIGNAL: "公开行动",
    MessageKind.INTERPROVINCIAL_PROPOSAL: "省际协同提议",
    MessageKind.PROVINCE_AUTOMAKER_PACKAGE: "省企协同方案",
    MessageKind.AUTOMAKER_PROVINCE_INTENT: "企业合作意向",
    MessageKind.AUTOMAKER_COUNTEROFFER: "企业反报价",
    MessageKind.RESOURCE_REALLOCATION: "资源重新配置",
    MessageKind.TRANSACTION_RESPONSE: "交易回应",
}


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
                            "title": f"{tick.value} · {WAVE_LABELS[wave]}",
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

    def _shared_scale(self) -> PresentationSharedScaleV4:
        absolute_values: list[float] = []
        differences: list[float] = []
        control = self.world.branches.get("control")
        treatment = self.world.branches.get("treatment")
        if control and treatment:
            for tick in MacroTick:
                control_checkpoint = control.checkpoints.get(tick)
                treatment_checkpoint = treatment.checkpoints.get(tick)
                if not control_checkpoint or not treatment_checkpoint:
                    continue
                for code in MAINLAND_PROVINCE_CODES:
                    control_value = control_checkpoint.settlement.province_states[
                        code
                    ].development_index
                    treatment_value = treatment_checkpoint.settlement.province_states[
                        code
                    ].development_index
                    absolute_values.extend((control_value, treatment_value))
                    differences.append(treatment_value - control_value)
        minimum = min(absolute_values, default=0.0)
        maximum = max(absolute_values, default=100.0)
        if abs(maximum - minimum) < 1e-9:
            minimum = max(0.0, minimum - 0.5)
            maximum = min(100.0, maximum + 0.5)
        return PresentationSharedScaleV4(
            metric_id="province_nev_development_index",
            absolute_min=round(minimum, 4),
            absolute_max=round(maximum, 4),
            difference_bound=round(
                max([0.01, *(abs(item) for item in differences)]),
                4,
            ),
            low_label="相对较低",
            midpoint_label="年度中位",
            high_label="相对较高",
        )

    def build_timeline(self) -> PresentationTimelineV4:
        nodes = self._nodes()
        completed = (
            list(self.world.branches["control"].completed_ticks)
            if "control" in self.world.branches
            else []
        )
        return PresentationTimelineV4(
            experiment_id=self.world.experiment_id,
            status=self.world.status,
            current_node_id=nodes[-1].node_id,
            nodes=nodes,
            completed_ticks=completed,
            shared_scale=self._shared_scale(),
            source_world_hash=canonical_hash(self.world),
        )

    def get_frame(self, frame_id: str) -> PresentationFrameV5:
        node = next((item for item in self._nodes() if item.node_id == frame_id), None)
        if node is None:
            raise KeyError(f"presentation frame not found: {frame_id}")
        return self._frame(node)

    @staticmethod
    def _checkpoint_for_node(
        branch: BranchRuntimeStateV9,
        node: PresentationTimelineNodeV3,
    ) -> TickCheckpoint | None:
        """Return only facts available before or at this narrative node."""

        if node.kind in {"settlement", "comparison"}:
            return branch.checkpoints.get(node.tick) if node.tick is not None else None
        if node.tick is None:
            return None
        previous_ticks = [tick for tick in MacroTick if tick.order < node.tick.order]
        for tick in reversed(previous_ticks):
            checkpoint = branch.checkpoints.get(tick)
            if checkpoint is not None:
                return checkpoint
        return None

    def _subject(self, subject_id: str) -> PresentationSubjectV4:
        provinces = policy_region_catalog()
        automakers = automaker_catalog()
        if subject_id in provinces:
            return PresentationSubjectV4(
                subject_ref=f"province:{subject_id}",
                subject_type="province",
                subject_id=subject_id,
                display_name=provinces[subject_id].short_name,
            )
        if subject_id in automakers:
            return PresentationSubjectV4(
                subject_ref=f"automaker:{subject_id}",
                subject_type="automaker",
                subject_id=subject_id,
                display_name=f"{automakers[subject_id].display_name}模拟主体",
            )
        if subject_id.startswith("event:"):
            event_id = subject_id.split(":", 1)[1]
            event = next(
                (
                    item
                    for item in (self.world.design.event_plans if self.world.design else [])
                    if item.event_plan_id == event_id
                ),
                None,
            )
            return PresentationSubjectV4(
                subject_ref=subject_id,
                subject_type="event",
                subject_id=event_id,
                display_name=event.name if event else "外生事件",
            )
        return PresentationSubjectV4(
            subject_ref="environment:national",
            subject_type="environment",
            subject_id="national",
            display_name="全国确定性环境",
        )

    @staticmethod
    def _chapter_label(node: PresentationTimelineNodeV3) -> str:
        if node.tick is None:
            return "年度起点"
        return {
            MacroTick.Q1: "Q1 政策落地",
            MacroTick.Q2: "Q2 主体互动",
            MacroTick.Q3: "Q3 调整扩散",
            MacroTick.Q4: "Q4 年度结算",
        }[node.tick]

    @staticmethod
    def _question(node: PresentationTimelineNodeV3) -> str:
        if node.kind == "policy":
            return "两套方案的唯一主动差异是什么？"
        if node.kind == "event":
            return "外生事件开始可见后，哪些主体会重新考虑？"
        if node.kind == "comparison":
            return "干预方案是否在可见代价下缩小了区域差距？"
        if node.kind == "settlement":
            return f"{node.tick.value if node.tick else '本季度'} 的行动如何改变了世界状态？"
        return "当前主体为何行动，对方如何回应？"

    @staticmethod
    def _province_values(
        checkpoints: dict[str, TickCheckpoint | None], role: str
    ) -> list[PresentationBranchProvinceValueV4]:
        checkpoint = checkpoints.get(role)
        return [
            PresentationBranchProvinceValueV4(
                province_code=code,
                value=(
                    checkpoint.settlement.province_states[code].development_index
                    if checkpoint is not None
                    else None
                ),
            )
            for code in MAINLAND_PROVINCE_CODES
        ]

    @staticmethod
    def _messages_for_session(
        branch: BranchRuntimeStateV9,
        session: InteractionSession,
        node: PresentationTimelineNodeV3,
    ) -> list[InteractionMessage]:
        messages = [
            item
            for item in branch.messages
            if item.session_id == session.session_id
            and (node.wave is None or item.wave.order <= node.wave.order)
        ]
        return sorted(messages, key=lambda item: (item.logical_sequence, item.message_id))

    @staticmethod
    def _decision_for(
        branch: BranchRuntimeStateV9,
        *,
        subject_id: str,
        tick: MacroTick,
        maximum_wave: InteractionWave | None,
        preferred_wave: InteractionWave | None,
    ) -> AgentTickDecision | None:
        decisions = [
            item
            for item in branch.decisions
            if item.agent_id == subject_id
            and item.tick is tick
            and (maximum_wave is None or item.wave.order <= maximum_wave.order)
        ]
        decisions.sort(
            key=lambda item: (
                item.wave is not preferred_wave,
                -item.wave.order,
                item.decision_id,
            )
        )
        return decisions[0] if decisions else None

    @staticmethod
    def _decision_summary(decision: AgentTickDecision | None) -> str:
        if decision is None:
            return "本节点没有新的结构化主体决策。"
        if decision.province_action:
            return decision.province_action.public_summary
        if decision.automaker_action:
            return decision.automaker_action.public_summary
        return decision.no_action_reason or "主体维持上一冻结行动。"

    @staticmethod
    def _condition_labels(decision: AgentTickDecision | None) -> list[str]:
        if decision is None:
            return []
        return [item.action_if_met for item in decision.reconsideration_conditions[:4]]

    @staticmethod
    def _previous_checkpoint(
        branch: BranchRuntimeStateV9, tick: MacroTick
    ) -> TickCheckpoint | None:
        previous = [item for item in MacroTick if item.order < tick.order]
        return branch.checkpoints.get(previous[-1]) if previous else None

    def _settlement_view(
        self,
        branch: BranchRuntimeStateV9,
        node: PresentationTimelineNodeV3,
        *,
        participant_ids: list[str],
        contributed: bool,
        contribution: float,
        result_summary: str,
    ) -> PresentationSettlementV5:
        province_changes: list[PresentationProvinceChangeV5] = []
        national_changes: list[PresentationMetricChangeV5] = []
        if node.kind in {"settlement", "comparison"} and node.tick is not None:
            checkpoint = branch.checkpoints.get(node.tick)
            previous = self._previous_checkpoint(branch, node.tick)
            if checkpoint is not None:
                province_catalog = policy_region_catalog()
                for province_code in dict.fromkeys(participant_ids):
                    if province_code not in province_catalog:
                        continue
                    current_state = checkpoint.settlement.province_states[province_code]
                    previous_state = (
                        previous.settlement.province_states[province_code]
                        if previous is not None
                        else None
                    )
                    province_changes.append(
                        PresentationProvinceChangeV5(
                            province_code=province_code,
                            province_name=province_catalog[province_code].short_name,
                            current_value=round(current_state.development_index, 4),
                            quarterly_change=(
                                round(
                                    current_state.development_index
                                    - previous_state.development_index,
                                    4,
                                )
                                if previous_state is not None
                                else None
                            ),
                        )
                    )
                current_metrics = checkpoint.settlement.national_metrics
                previous_metrics = (
                    previous.settlement.national_metrics if previous is not None else None
                )
                for metric_id, label in (
                    ("regional_development_gap", "区域发展差距"),
                    ("local_fiscal_pressure", "地方财政压力"),
                ):
                    current_value = getattr(current_metrics, metric_id)
                    previous_value = (
                        getattr(previous_metrics, metric_id)
                        if previous_metrics is not None
                        else None
                    )
                    national_changes.append(
                        PresentationMetricChangeV5(
                            metric_id=metric_id,
                            label=label,
                            current_value=round(current_value, 4),
                            quarterly_change=(
                                round(current_value - previous_value, 4)
                                if previous_value is not None
                                else None
                            ),
                        )
                    )
        return PresentationSettlementV5(
            contributed=contributed,
            contribution=round(contribution, 6) if contributed else 0,
            result_summary=result_summary,
            direct_contribution_label=(
                f"环境机制贡献 +{contribution:.3f}" if contributed else "未进入环境贡献"
            ),
            province_changes=province_changes,
            national_changes=national_changes,
        )

    @staticmethod
    def _edge_relation(message: InteractionMessage) -> tuple[str, str, str]:
        state = message.transaction_state or TransactionState.PROPOSED
        if (
            message.kind is MessageKind.AUTOMAKER_COUNTEROFFER
            or state is TransactionState.COUNTERED
        ):
            return "counteroffer", "反报价", "dashed"
        if state is TransactionState.SETTLED:
            return "settled", "已达成", "thick"
        if state is TransactionState.ACCEPTED:
            return "accepted", "已接受", "thick"
        if state is TransactionState.REJECTED:
            return "rejected", "已拒绝", "faded"
        if state is TransactionState.DEFERRED:
            return "deferred", "暂缓处理", "dashed"
        if state is TransactionState.RESOURCE_INVALID:
            return "invalid", "资源无效", "faded"
        return "proposal", MESSAGE_LABELS[message.kind], "solid"

    def _spotlight(
        self,
        branch: BranchRuntimeStateV9,
        role: str,
        session: InteractionSession,
        messages: list[InteractionMessage],
        node: PresentationTimelineNodeV3,
    ) -> PresentationSpotlightV5:
        action_message = messages[0]
        actor = self._subject(action_message.sender_id)
        counterpart_id = action_message.recipient_ids[0]
        counterpart = self._subject(counterpart_id)
        decision = self._decision_for(
            branch,
            subject_id=action_message.sender_id,
            tick=session.tick,
            maximum_wave=node.wave,
            preferred_wave=action_message.wave,
        )
        response_message = messages[-1] if len(messages) > 1 else None
        response_decision = self._decision_for(
            branch,
            subject_id=response_message.sender_id if response_message else counterpart_id,
            tick=session.tick,
            maximum_wave=node.wave,
            preferred_wave=response_message.wave if response_message else None,
        )
        action_state = action_message.transaction_state or TransactionState.PROPOSED
        action = PresentationActionV4(
            kind=action_message.kind.value,
            label=MESSAGE_LABELS[action_message.kind],
            summary=action_message.public_summary,
            state=action_state.value,
            state_label=STATE_LABELS[action_state],
            message_id=action_message.message_id,
        )
        response = None
        if response_message is not None:
            response_state = response_message.transaction_state or session.state
            response = PresentationActionV4(
                kind=response_message.kind.value,
                label=MESSAGE_LABELS[response_message.kind],
                summary=response_message.public_summary,
                state=response_state.value,
                state_label=STATE_LABELS[response_state],
                message_id=response_message.message_id,
            )
        contributed = (
            node.kind in {"settlement", "comparison"} and session.state is TransactionState.SETTLED
        )
        visible_state = (
            session.state
            if node.kind in {"settlement", "comparison"}
            else messages[-1].transaction_state or TransactionState.PROPOSED
        )
        result_summary = (
            f"本次互动以 {session.settled_contribution:.3f} 的模拟贡献进入季度环境。"
            if contributed
            else f"当前结果为“{STATE_LABELS[visible_state]}”，未进入环境贡献。"
        )
        observed = (decision.noticed_facts if decision else [])[:6]
        if not observed:
            observed = ["年度资源约束与本季度授权上下文"]
        objective = (
            "在本省财政空间内争取更有效的产业与渠道协同"
            if actor.subject_type == "province"
            else "在全国资源约束内改善省级合作组合"
        )
        strongest_constraint = (
            decision.opportunity_costs[0]
            if decision and decision.opportunity_costs
            else "年度资源包固定，新增投入会挤占其他选择"
        )
        decision_summary = self._decision_summary(decision)
        response_summary = response.summary if response else "等待对方在后续逻辑节点回应。"
        settle_status = (
            "completed"
            if node.kind in {"settlement", "comparison"}
            else ("completed" if contributed else "pending")
        )
        beats = [
            PresentationCausalBeatV4(
                beat="focus",
                label="关注",
                headline=f"{actor.display_name}关注本季度机会",
                detail=objective,
                status="completed",
            ),
            PresentationCausalBeatV4(
                beat="observe",
                label="观察",
                headline="读取授权事实",
                detail="；".join(observed),
                status="completed",
            ),
            PresentationCausalBeatV4(
                beat="decide",
                label="决策",
                headline=ENGAGEMENT_LABELS[decision.engagement] if decision else "维持判断",
                detail=decision_summary,
                status="completed",
            ),
            PresentationCausalBeatV4(
                beat="action",
                label="行动",
                headline=action.label,
                detail=action.summary,
                status="completed",
            ),
            PresentationCausalBeatV4(
                beat="response",
                label="回应",
                headline=response.state_label if response else "等待回应",
                detail=response_summary,
                status="completed" if response else "active",
            ),
            PresentationCausalBeatV4(
                beat="settle",
                label="结算",
                headline="进入环境" if contributed else "尚未贡献",
                detail=result_summary,
                status=settle_status,
            ),
        ]
        evidence = list(
            dict.fromkeys(
                [
                    *session.evidence_refs,
                    *(decision.evidence_refs if decision else []),
                    *(response_decision.evidence_refs if response_decision else []),
                    *(ref for message in messages for ref in message.evidence_refs),
                ]
            )
        )
        return PresentationSpotlightV5(
            spotlight_id=f"spotlight:{role}:{session.session_id}:{node.node_id}",
            branch_id=role,
            tick=session.tick,
            wave=messages[-1].wave,
            session_id=session.session_id,
            actor=actor,
            counterpart=counterpart,
            objective=objective,
            strongest_constraint=strongest_constraint,
            observed_facts=observed,
            engagement_label=ENGAGEMENT_LABELS[decision.engagement] if decision else "维持判断",
            decision_summary=decision_summary,
            alternatives=(decision.alternatives if decision else [])[:4],
            opportunity_costs=(decision.opportunity_costs if decision else [])[:4],
            reconsideration_conditions=self._condition_labels(decision),
            action=action,
            response=response,
            settlement=self._settlement_view(
                branch,
                node,
                participant_ids=session.participant_ids,
                contributed=contributed,
                contribution=session.settled_contribution,
                result_summary=result_summary,
            ),
            beats=beats,
            fallback=bool(
                (decision and decision.fallback_used)
                or (response_decision and response_decision.fallback_used)
            ),
            evidence_refs=evidence[:24],
        )

    def _event_edges(
        self,
        branch: BranchRuntimeStateV9,
        role: str,
        node: PresentationTimelineNodeV3,
    ) -> list[PresentationGameEdgeV5]:
        if node.kind != "event" or not node.source_event_ids or node.tick is None:
            return []
        event_id = node.source_event_ids[0]
        visible_inboxes = [
            item
            for item in branch.inboxes
            if item.tick is node.tick
            and item.wave is node.wave
            and event_id in item.visible_event_ids
        ]
        visible_inboxes.sort(key=lambda item: (item.agent_kind.value, item.agent_id))
        source = self._subject(f"event:{event_id}")
        return [
            PresentationGameEdgeV5(
                edge_id=f"event-edge:{role}:{event_id}:{inbox.agent_id}",
                branch_id=role,
                source=source,
                target=self._subject(inbox.agent_id),
                relation="event_impact",
                relation_label="事件开始可见",
                line_style="pulse",
                weight=0.7,
                summary=f"{source.display_name}进入{self._subject(inbox.agent_id).display_name}的授权上下文。",
                session_id=f"event:{event_id}:{inbox.agent_id}",
                reveal_order=index,
                evidence_refs=[f"event:{event_id}", f"inbox:{inbox.inbox_id}"],
            )
            for index, inbox in enumerate(visible_inboxes[:3])
        ]

    def _branch_story(
        self,
        branch: BranchRuntimeStateV9,
        role: str,
        node: PresentationTimelineNodeV3,
    ) -> tuple[
        list[PresentationGameEdgeV5],
        list[PresentationSpotlightV5],
        list[PresentationSpotlightV5],
    ]:
        if node.tick is None:
            return [], [], []
        candidates: list[tuple[InteractionSession, list[InteractionMessage]]] = []
        for session in branch.sessions:
            if session.tick is not node.tick:
                continue
            messages = self._messages_for_session(branch, session, node)
            if not messages:
                continue
            if (
                node.kind == "wave"
                and node.wave is not None
                and not any(item.wave is node.wave for item in messages)
            ):
                continue
            candidates.append((session, messages))
        candidates.sort(
            key=lambda item: (
                not any(
                    participant in automaker_catalog() for participant in item[0].participant_ids
                ),
                (
                    item[0].state
                    if node.kind in {"settlement", "comparison"}
                    else item[1][-1].transaction_state
                )
                is not TransactionState.SETTLED,
                -len(item[1]),
                item[0].session_id,
            )
        )
        all_spotlights = [
            self._spotlight(branch, role, session, messages, node)
            for session, messages in candidates
        ]
        spotlights = all_spotlights[:3]
        edges: list[PresentationGameEdgeV5] = self._event_edges(branch, role, node)
        if node.kind == "event" and not edges:
            return [], [], []
        if node.kind == "event" and edges:
            spotlights = []
            for event_edge in edges:
                event_decision = self._decision_for(
                    branch,
                    subject_id=event_edge.target.subject_id,
                    tick=node.tick,
                    maximum_wave=node.wave,
                    preferred_wave=node.wave,
                )
                response_summary = self._decision_summary(event_decision)
                event_action = PresentationActionV4(
                    kind="event_release",
                    label="事件开始可见",
                    summary=event_edge.summary,
                    state="visible",
                    state_label="已进入授权上下文",
                )
                event_response = (
                    PresentationActionV4(
                        kind="event_response",
                        label="主体重新评估",
                        summary=response_summary,
                        state="reviewed",
                        state_label="已重新评估",
                    )
                    if event_decision
                    else None
                )
                spotlights.append(
                    PresentationSpotlightV5(
                        spotlight_id=f"spotlight:{role}:{event_edge.session_id}",
                        branch_id=role,
                        tick=node.tick,
                        wave=node.wave or InteractionWave.WAVE_0,
                        session_id=event_edge.session_id or f"event:{node.source_event_ids[0]}",
                        actor=event_edge.source,
                        counterpart=event_edge.target,
                        objective="检验冻结情景如何改变主体的授权上下文",
                        strongest_constraint="事件只通过已冻结机制通道传播，不直接写入结果",
                        observed_facts=[event_edge.summary],
                        engagement_label="触发重新评估" if event_decision else "等待主体评估",
                        decision_summary=response_summary,
                        alternatives=(event_decision.alternatives if event_decision else [])[:4],
                        opportunity_costs=(
                            event_decision.opportunity_costs if event_decision else []
                        )[:4],
                        reconsideration_conditions=self._condition_labels(event_decision),
                        action=event_action,
                        response=event_response,
                        settlement=PresentationSettlementV5(
                            contributed=False,
                            contribution=0,
                            direct_contribution_label="未进入环境贡献",
                            result_summary="事件影响将在本季度结算后进入权威世界状态。",
                        ),
                        beats=[
                            PresentationCausalBeatV4(
                                beat="focus",
                                label="关注",
                                headline=event_edge.source.display_name,
                                detail="冻结情景到达发布节点。",
                                status="completed",
                            ),
                            PresentationCausalBeatV4(
                                beat="observe",
                                label="观察",
                                headline=f"{event_edge.target.display_name}获得事件上下文",
                                detail=event_edge.summary,
                                status="completed",
                            ),
                            PresentationCausalBeatV4(
                                beat="decide",
                                label="决策",
                                headline="重新评估" if event_decision else "等待评估",
                                detail=response_summary,
                                status="completed" if event_decision else "active",
                            ),
                            PresentationCausalBeatV4(
                                beat="action",
                                label="行动",
                                headline="主体行动待冻结",
                                detail=response_summary,
                                status="completed" if event_decision else "pending",
                            ),
                            PresentationCausalBeatV4(
                                beat="response",
                                label="回应",
                                headline="市场回应待发生",
                                detail="后续互动只读取授权可见信息。",
                                status="pending",
                            ),
                            PresentationCausalBeatV4(
                                beat="settle",
                                label="结算",
                                headline="季度结算待完成",
                                detail="环境将在季末统一计算事件贡献。",
                                status="pending",
                            ),
                        ],
                        fallback=bool(event_decision and event_decision.fallback_used),
                        evidence_refs=event_edge.evidence_refs,
                    )
                )
            all_spotlights = spotlights
            return edges, spotlights, spotlights
        for reveal_order, (session, messages) in enumerate(candidates[:3]):
            for message_order, message in enumerate(messages):
                if not message.recipient_ids:
                    continue
                relation, label, line_style = self._edge_relation(message)
                edges.append(
                    PresentationGameEdgeV5(
                        edge_id=f"edge:{role}:{message.message_id}",
                        branch_id=role,
                        source=self._subject(message.sender_id),
                        target=self._subject(message.recipient_ids[0]),
                        relation=relation,
                        relation_label=label,
                        line_style=line_style,
                        weight=min(1.0, 0.35 + message.resource_amount * 4),
                        summary=message.public_summary,
                        session_id=session.session_id,
                        reveal_order=reveal_order,
                        message_order=message_order,
                        evidence_refs=message.evidence_refs,
                    )
                )
        return edges, spotlights, all_spotlights

    @staticmethod
    def _divergences(
        branch_spotlights: dict[str, list[PresentationSpotlightV5]],
    ) -> list[PresentationDivergenceV5]:
        control = {
            tuple(sorted((item.actor.subject_ref, item.counterpart.subject_ref))): item
            for item in branch_spotlights["control"]
        }
        treatment = {
            tuple(sorted((item.actor.subject_ref, item.counterpart.subject_ref))): item
            for item in branch_spotlights["treatment"]
        }
        results: list[PresentationDivergenceV5] = []
        for participant_key in sorted(set(control) | set(treatment)):
            left = control.get(participant_key)
            right = treatment.get(participant_key)
            left_state = (
                left.response.state_label
                if left and left.response
                else left.action.state_label
                if left
                else "未发生"
            )
            right_state = (
                right.response.state_label
                if right and right.response
                else right.action.state_label
                if right
                else "未发生"
            )
            left_decision = left.decision_summary if left else "未发生"
            right_decision = right.decision_summary if right else "未发生"
            if left is None:
                divergence_type = "treatment_only"
                summary = "该互动仅在干预方案中发生。"
            elif right is None:
                divergence_type = "control_only"
                summary = "该互动仅在原始方案中发生。"
            elif left_state != right_state:
                divergence_type = "state_changed"
                summary = f"原始方案为“{left_state}”，干预方案为“{right_state}”。"
            elif left_decision != right_decision:
                divergence_type = "decision_changed"
                summary = "两套方案的交易状态相同，但主体决策发生变化。"
            else:
                continue
            results.append(
                PresentationDivergenceV5(
                    divergence_id=f"divergence:{':'.join(participant_key)}",
                    divergence_type=divergence_type,
                    participants=[
                        (left or right).actor,
                        (left or right).counterpart,
                    ],
                    control_state_label=left_state,
                    treatment_state_label=right_state,
                    control_decision_summary=left_decision,
                    treatment_decision_summary=right_decision,
                    summary=summary,
                )
            )
        return results[:12]

    def _frame(self, node: PresentationTimelineNodeV3) -> PresentationFrameV5:
        branches: dict[str, PresentationBranchViewV5] = {}
        branch_spotlights: dict[str, list[PresentationSpotlightV5]] = {}
        checkpoints = {}
        for role in ("control", "treatment"):
            branch = self.world.branches.get(role)
            checkpoint = self._checkpoint_for_node(branch, node) if branch else None
            checkpoints[role] = checkpoint
            province_values = self._province_values(checkpoints, role)
            edges, spotlights, all_spotlights = (
                self._branch_story(branch, role, node) if branch else ([], [], [])
            )
            branch_spotlights[role] = all_spotlights
            branches[role] = PresentationBranchViewV5(
                branch_id=role,
                label="原始方案" if role == "control" else "干预方案",
                tick=checkpoint.tick if checkpoint else None,
                national_metrics=(
                    checkpoint.settlement.national_metrics if checkpoint else NationalMetrics()
                ),
                province_values=province_values,
                game_edges=edges,
                spotlights=spotlights[:3],
                fallback_count=sum(item.fallback for item in spotlights),
            )
        divergences = self._divergences(branch_spotlights)
        summary = {
            "policy": "中央政策解读、实验设计与同源基线已冻结。",
            "event": "外生事件按冻结季度与逻辑 Wave 批次发布。",
            "wave": "当前节点展示主体如何观察、决策、行动并获得真实回应。",
            "settlement": "确定性环境已提交不可变季度 Checkpoint。",
            "comparison": "Q4 年度结果完成同源 A/B 与中央复盘。",
        }[node.kind]
        evidence = [
            ref
            for branch in branches.values()
            for spotlight in branch.spotlights
            for ref in spotlight.evidence_refs
        ]
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
            "chapter_label": self._chapter_label(node),
            "question": self._question(node),
            "wave_label": WAVE_LABELS[node.wave] if node.wave else None,
            "branches": branches,
            "divergences": divergences,
            "shared_scale": self._shared_scale(),
            "event_plan_ids": node.source_event_ids,
            "evidence_refs": evidence,
        }
        return PresentationFrameV5(**payload, source_hash=canonical_hash(payload))
