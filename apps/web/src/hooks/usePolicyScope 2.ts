import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { policyScopeApi } from "../api/client";
import type {
  Branch,
  CentralIntervention,
  ComparisonResult,
  RunMode,
  SimulationEvent,
  WorldState,
} from "../types";

export type ProductStage = "directive" | "situation" | "intervention" | "compare";

export function usePolicyScope() {
  const [world, setWorld] = useState<WorldState | null>(null);
  const [control, setControl] = useState<WorldState | null>(null);
  const [treatment, setTreatment] = useState<WorldState | null>(null);
  const [branch, setBranch] = useState<Branch | null>(null);
  const [intervention, setIntervention] = useState<CentralIntervention | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [events, setEvents] = useState<SimulationEvent[]>([]);
  const [stage, setStage] = useState<ProductStage>("directive");
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seenEvents = useRef(new Set<string>());

  const profilesQuery = useQuery({
    queryKey: ["province-profiles"],
    queryFn: policyScopeApi.listProvinces,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const healthQuery = useQuery({
    queryKey: ["api-health"],
    queryFn: policyScopeApi.health,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (!world?.experiment_id) return;
    const source = new EventSource(policyScopeApi.streamUrl(world.experiment_id));
    const eventTypes = [
      "experiment.started",
      "central.directive.completed",
      "central.directive.approved",
      "phase.started",
      "agent.decision.started",
      "agent.decision.completed",
      "agent.decision.fallback",
      "environment.updated",
      "world_state.updated",
      "central.intervention.proposed",
      "central.intervention.approved",
      "checkpoint.created",
      "branch.created",
      "phase.completed",
      "experiment.completed",
    ];
    const onEvent = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as SimulationEvent;
      if (seenEvents.current.has(event.event_id)) return;
      seenEvents.current.add(event.event_id);
      setEvents((current) => [...current.slice(-79), event]);
    };
    eventTypes.forEach((name) => source.addEventListener(name, onEvent as EventListener));
    return () => source.close();
  }, [world?.experiment_id]);

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
    execute("国务院 Agent 正在生成政策草案…", async () => {
      const next = await policyScopeApi.createExperiment(objective, runMode);
      seenEvents.current.clear();
      setEvents([]);
      setWorld(next);
      setControl(null);
      setTreatment(null);
      setBranch(null);
      setIntervention(null);
      setComparison(null);
      setStage("directive");
      return next;
    });

  const approveDirective = () =>
    execute("正在确认中央指令…", async () => {
      if (!world) throw new Error("请先生成政策草案");
      const next = await policyScopeApi.approveDirective(world.experiment_id, world.policy);
      setWorld(next);
      setStage("situation");
      return next;
    });

  const runToT3 = () =>
    execute("31 个省级 Agent 正在并发推演至 T3…", async () => {
      if (!world) throw new Error("请先创建实验");
      const next = await policyScopeApi.runExperiment(world.experiment_id, "T3");
      setWorld(next);
      setStage("situation");
      return next;
    });

  const approveProposal = (proposalId: string) =>
    execute("正在审批干预并创建 Treatment 分支…", async () => {
      if (!world) throw new Error("请先运行到 T3");
      const approved = await policyScopeApi.approveIntervention(
        world.experiment_id,
        proposalId,
      );
      const created = await policyScopeApi.createBranch(
        world.experiment_id,
        approved.intervention_id,
      );
      setIntervention(approved);
      setBranch(created);
      setStage("intervention");
      return created;
    });

  const runComparison = () =>
    execute("Control / Treatment 正在独立演化至 T5…", async () => {
      if (!world || !branch) throw new Error("请先审批干预并创建分支");
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
      setStage("compare");
      return result;
    });

  return {
    profiles: profilesQuery.data ?? [],
    profilesLoading: profilesQuery.isLoading,
    profilesError: profilesQuery.error,
    configuredRunMode: healthQuery.data?.run_mode ?? "fake",
    world,
    control,
    treatment,
    branch,
    intervention,
    comparison,
    events,
    stage,
    setStage,
    busyLabel,
    error,
    createDraft,
    approveDirective,
    runToT3,
    approveProposal,
    runComparison,
  };
}
