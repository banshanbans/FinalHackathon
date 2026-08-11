import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { policyScopeApi } from "../api/client";
import type {
  Branch,
  CentralIntervention,
  ComparisonResult,
  Policy,
  RunMode,
  SimulationEvent,
  WorldState,
} from "../types";

const ACTIVE_EXPERIMENT_KEY = "policyscope.active-experiment.v2";

export function usePolicyScope() {
  const [world, setWorld] = useState<WorldState | null>(null);
  const [control, setControl] = useState<WorldState | null>(null);
  const [treatment, setTreatment] = useState<WorldState | null>(null);
  const [branch, setBranch] = useState<Branch | null>(null);
  const [intervention, setIntervention] = useState<CentralIntervention | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [events, setEvents] = useState<SimulationEvent[]>([]);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hydrating, setHydrating] = useState(true);
  const seenEvents = useRef(new Set<string>());

  const profilesQuery = useQuery({
    queryKey: ["province-profiles-v2"],
    queryFn: policyScopeApi.listProvinces,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const archetypesQuery = useQuery({
    queryKey: ["enterprise-archetypes-v2"],
    queryFn: policyScopeApi.listEnterpriseArchetypes,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const defaultPolicyQuery = useQuery({
    queryKey: ["default-policy-v2"],
    queryFn: policyScopeApi.defaultPolicy,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const healthQuery = useQuery({
    queryKey: ["api-health-v2"],
    queryFn: policyScopeApi.health,
    staleTime: 30_000,
  });

  useEffect(() => {
    const experimentId = localStorage.getItem(ACTIVE_EXPERIMENT_KEY);
    if (!experimentId) {
      setHydrating(false);
      return;
    }
    policyScopeApi
      .getState(experimentId)
      .then(setWorld)
      .catch(() => localStorage.removeItem(ACTIVE_EXPERIMENT_KEY))
      .finally(() => setHydrating(false));
  }, []);

  useEffect(() => {
    if (!world?.experiment_id || world.status === "completed") return;
    const source = new EventSource(policyScopeApi.streamUrl(world.experiment_id));
    const eventTypes = [
      "experiment.started",
      "central.directive.completed",
      "central.directive.approved",
      "phase.started",
      "agent.decision.started",
      "agent.decision.completed",
      "agent.decision.fallback",
      "enterprise.batch.started",
      "enterprise.batch.completed",
      "enterprise.batch.fallback",
      "enterprise.aggregate.updated",
      "province.feedback.completed",
      "environment.updated",
      "world_state.updated",
      "central.intervention.proposed",
      "central.intervention.approved",
      "central.intervention.rejected",
      "checkpoint.created",
      "branch.created",
      "phase.completed",
      "experiment.completed",
    ];
    const onEvent = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as SimulationEvent;
      if (seenEvents.current.has(event.event_id)) return;
      seenEvents.current.add(event.event_id);
      setEvents((current) => [...current.slice(-99), event]);
    };
    eventTypes.forEach((name) => source.addEventListener(name, onEvent as EventListener));
    return () => source.close();
  }, [world?.experiment_id, world?.status]);

  const execute = useCallback(async <T,>(label: string, task: () => Promise<T>) => {
    setBusyLabel(label);
    setError(null);
    try {
      return await task();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "发生未知错误");
      throw reason;
    } finally {
      setBusyLabel(null);
    }
  }, []);

  const createDraft = (objective: string, runMode: RunMode) =>
    execute("国务院 Agent 正在形成结构化政策草案…", async () => {
      const next = await policyScopeApi.createExperiment(objective, runMode);
      localStorage.setItem(ACTIVE_EXPERIMENT_KEY, next.experiment_id);
      seenEvents.current.clear();
      setEvents([]);
      setWorld(next);
      setControl(null);
      setTreatment(null);
      setBranch(null);
      setIntervention(null);
      setComparison(null);
      return next;
    });

  const approveDirective = (policy: Policy) =>
    execute("正在确认中央政策指令…", async () => {
      if (!world) throw new Error("请先生成政策草案");
      const next = await policyScopeApi.approveDirective(world.experiment_id, policy);
      setWorld(next);
      return next;
    });

  const runToT3 = () =>
    execute("地方与企业 Agent 正在推演至 T3…", async () => {
      if (!world) throw new Error("请先创建实验");
      const next = await policyScopeApi.runExperiment(world.experiment_id, "T3");
      setWorld(next);
      return next;
    });

  const approveProposal = (proposalId: string, policy: Policy) =>
    execute("正在批准建议并创建干预方案…", async () => {
      if (!world) throw new Error("请先运行到 T3");
      const approved = await policyScopeApi.approveIntervention(
        world.experiment_id,
        proposalId,
        policy,
      );
      const created = await policyScopeApi.createBranch(
        world.experiment_id,
        approved.intervention_id,
      );
      setIntervention(approved);
      setBranch(created);
      setWorld((current) => current ? { ...current, approved_intervention: approved, intervention_decision: "approved" } : current);
      return created;
    });

  const rejectProposal = (proposalId: string, reason: string) =>
    execute("正在记录用户决定…", async () => {
      if (!world) throw new Error("请先运行到 T3");
      const next = await policyScopeApi.rejectIntervention(
        world.experiment_id,
        proposalId,
        reason,
      );
      setWorld(next);
      setBranch(null);
      setIntervention(null);
      return next;
    });

  const runComparison = () =>
    execute("原始方案与干预方案正在同源演化至 T5…", async () => {
      if (!world || !branch) throw new Error("请先批准建议并创建分支");
      const controlState = await policyScopeApi.runExperiment(
        world.experiment_id,
        "T5",
        "control",
      );
      const treatmentState = await policyScopeApi.runBranch(branch.branch_id);
      const result = await policyScopeApi.compare(world.experiment_id);
      setControl(controlState);
      setTreatment(treatmentState);
      setWorld(controlState);
      setComparison(result);
      return result;
    });

  const runSingleBranch = () =>
    execute("原始方案正在继续演化至 T5…", async () => {
      if (!world) throw new Error("请先创建实验");
      const next = await policyScopeApi.runExperiment(world.experiment_id, "T5", "control");
      setControl(next);
      setWorld(next);
      return next;
    });

  const loadEvidence = useCallback((evidenceId: string) => {
    if (!world) throw new Error("尚未创建实验");
    return policyScopeApi.evidence(world.experiment_id, evidenceId);
  }, [world]);

  const loadComparison = useCallback(() =>
    execute("正在读取同源对照结果…", async () => {
      if (!world) throw new Error("尚未创建实验");
      const result = await policyScopeApi.compare(world.experiment_id);
      const [controlState, treatmentState] = await Promise.all([
        policyScopeApi.getState(world.experiment_id, result.control_branch_id),
        policyScopeApi.getState(world.experiment_id, result.treatment_branch_id),
      ]);
      setControl(controlState);
      setTreatment(treatmentState);
      setComparison(result);
      return result;
    }), [execute, world]);

  const resetExperiment = () => {
    localStorage.removeItem(ACTIVE_EXPERIMENT_KEY);
    seenEvents.current.clear();
    setEvents([]);
    setWorld(null);
    setControl(null);
    setTreatment(null);
    setBranch(null);
    setIntervention(null);
    setComparison(null);
    setError(null);
  };

  return {
    profiles: profilesQuery.data ?? [],
    archetypes: archetypesQuery.data ?? [],
    defaultPolicy: defaultPolicyQuery.data ?? null,
    metadataLoading:
      profilesQuery.isLoading || archetypesQuery.isLoading || defaultPolicyQuery.isLoading,
    metadataError:
      profilesQuery.error ?? archetypesQuery.error ?? defaultPolicyQuery.error,
    configuredRunMode: healthQuery.data?.run_mode ?? "cache",
    world,
    control,
    treatment,
    branch,
    intervention,
    comparison,
    events,
    busyLabel,
    error,
    hydrating,
    createDraft,
    approveDirective,
    runToT3,
    approveProposal,
    rejectProposal,
    runComparison,
    runSingleBranch,
    loadEvidence,
    loadComparison,
    resetExperiment,
  };
}

export type PolicyScopeFlow = ReturnType<typeof usePolicyScope>;
