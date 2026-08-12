import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { ApiError, policyScopeApi } from "../api/client";
import { SIMULATION_EVENT_TYPES } from "../events";
import type {
  Branch,
  CentralIntervention,
  ComparisonResult,
  Policy,
  RunMode,
  SimulationEvent,
  WorldState,
} from "../types";

const RECENT_EXPERIMENT_KEY = "policyscope.recent-experiment.v3";

function experimentIdFromPath(pathname: string) {
  return pathname.match(/^\/experiments\/([^/]+)\//)?.[1] ?? null;
}

export function usePolicyScope() {
  const location = useLocation();
  const routeExperimentId = experimentIdFromPath(location.pathname);
  const [world, setWorld] = useState<WorldState | null>(null);
  const [control, setControl] = useState<WorldState | null>(null);
  const [treatment, setTreatment] = useState<WorldState | null>(null);
  const [branch, setBranch] = useState<Branch | null>(null);
  const [intervention, setIntervention] = useState<CentralIntervention | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [events, setEvents] = useState<SimulationEvent[]>([]);
  const [connectionState, setConnectionState] = useState<"idle" | "connected" | "reconnecting">("idle");
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
  const personaTypesQuery = useQuery({
    queryKey: ["province-persona-types-v1"],
    queryFn: policyScopeApi.listProvincePersonaTypes,
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
  const replayQuery = useQuery({
    queryKey: ["experiment-replay-v3", routeExperimentId],
    queryFn: () => policyScopeApi.replay(routeExperimentId!),
    enabled: Boolean(routeExperimentId),
    staleTime: Number.POSITIVE_INFINITY,
  });
  const mergedEvents = useMemo(() => {
    const byId = new Map<string, SimulationEvent>();
    const replayEvents = Array.isArray(replayQuery.data) ? replayQuery.data : [];
    [...replayEvents, ...events].forEach((event) => byId.set(event.event_id, event));
    return [...byId.values()].sort((left, right) => {
      const timeDelta = Date.parse(left.timestamp) - Date.parse(right.timestamp);
      return timeDelta === 0 ? left.event_id.localeCompare(right.event_id) : timeDelta;
    });
  }, [events, replayQuery.data]);

  useEffect(() => {
    if (!routeExperimentId) {
      setHydrating(false);
      return;
    }
    if (world?.experiment_id === routeExperimentId) {
      localStorage.setItem(RECENT_EXPERIMENT_KEY, routeExperimentId);
      setHydrating(false);
      return;
    }
    setHydrating(true);
    setError(null);
    setControl(null);
    setTreatment(null);
    setBranch(null);
    setIntervention(null);
    setComparison(null);
    seenEvents.current.clear();
    setEvents([]);
    policyScopeApi
      .getState(routeExperimentId)
      .then((next) => {
        localStorage.setItem(RECENT_EXPERIMENT_KEY, routeExperimentId);
        setWorld(next);
      })
      .catch((reason: unknown) => {
        setWorld(null);
        setError(reason instanceof Error ? reason.message : "推演加载失败");
      })
      .finally(() => setHydrating(false));
  }, [routeExperimentId, world?.experiment_id]);

  useEffect(() => {
    if (!world?.experiment_id || world.experiment_id !== routeExperimentId || world.status === "completed") {
      setConnectionState("idle");
      return;
    }
    const source = new EventSource(policyScopeApi.streamUrl(world.experiment_id));
    setConnectionState("reconnecting");
    source.onopen = () => setConnectionState("connected");
    source.onerror = () => setConnectionState("reconnecting");
    const onEvent = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as SimulationEvent;
      if (seenEvents.current.has(event.event_id)) return;
      seenEvents.current.add(event.event_id);
      setEvents((current) => [...current.slice(-99), event]);
    };
    SIMULATION_EVENT_TYPES.forEach((name) =>
      source.addEventListener(name, onEvent as EventListener),
    );
    return () => {
      source.close();
      setConnectionState("idle");
    };
  }, [routeExperimentId, world?.experiment_id, world?.status]);

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
    execute("中央研判智能体正在生成政策草案…", async () => {
      const next = await policyScopeApi.createExperiment(objective, runMode);
      localStorage.setItem(RECENT_EXPERIMENT_KEY, next.experiment_id);
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
    execute("正在提交中央政策审批…", async () => {
      if (!world) throw new Error("请先生成政策草案");
      try {
        const next = await policyScopeApi.approveDirective(world.experiment_id, policy);
        setWorld(next);
        return next;
      } catch (reason) {
        if (
          reason instanceof ApiError
          && (
            reason.errorCode === "DIRECTIVE_NOT_AWAITING_APPROVAL"
            || reason.message === "directive is not awaiting approval"
          )
        ) {
          const current = await policyScopeApi.getState(world.experiment_id);
          setWorld(current);
          if (current.directive.approval_status === "approved") return current;
        }
        throw reason;
      }
    });

  const runToT3 = () =>
    execute("省级与企业智能体正在推演至 T3…", async () => {
      if (!world) throw new Error("请先新建推演");
      const next = await policyScopeApi.runExperiment(world.experiment_id, "T3");
      setWorld(next);
      return next;
    });

  const approveProposal = (proposalId: string, policy: Policy) =>
    execute("正在批准政策调整并创建干预方案…", async () => {
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
    execute("原始方案与干预方案正在运行至 T5…", async () => {
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
    execute("原始方案正在运行至 T5…", async () => {
      if (!world) throw new Error("请先新建推演");
      const next = await policyScopeApi.runExperiment(world.experiment_id, "T5", "control");
      setControl(next);
      setWorld(next);
      return next;
    });

  const loadEvidence = useCallback((evidenceId: string) => {
    if (!world) throw new Error("尚未新建推演");
    return policyScopeApi.evidence(world.experiment_id, evidenceId);
  }, [world]);

  const loadComparison = useCallback(() =>
    execute("正在加载双方案对照结果…", async () => {
      if (!world) throw new Error("尚未新建推演");
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
    localStorage.removeItem(RECENT_EXPERIMENT_KEY);
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

  const routedWorld = routeExperimentId && world?.experiment_id !== routeExperimentId ? null : world;

  return {
    profiles: profilesQuery.data ?? [],
    archetypes: archetypesQuery.data ?? [],
    personaTypes: personaTypesQuery.data ?? [],
    defaultPolicy: defaultPolicyQuery.data ?? null,
    metadataLoading:
      profilesQuery.isLoading
      || archetypesQuery.isLoading
      || personaTypesQuery.isLoading
      || defaultPolicyQuery.isLoading,
    metadataError:
      profilesQuery.error
      ?? archetypesQuery.error
      ?? personaTypesQuery.error
      ?? defaultPolicyQuery.error,
    configuredRunMode: healthQuery.data?.run_mode ?? "cache",
    world: routedWorld,
    control: routedWorld ? control : null,
    treatment: routedWorld ? treatment : null,
    branch,
    intervention,
    comparison,
    events: mergedEvents,
    connectionState,
    replayLoading: replayQuery.isLoading,
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
