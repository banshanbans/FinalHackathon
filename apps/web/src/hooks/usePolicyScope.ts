import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { policyScopeApi } from "../api/client";
import type { Branch, CentralIntervention, ComparisonResult, Policy, RunMode, SimulationEvent, WorldState } from "../types";

function experimentIdFromPath(pathname: string) { return pathname.match(/^\/experiments\/([^/]+)\//)?.[1] ?? null; }

export function usePolicyScope() {
  const location = useLocation();
  const routeId = experimentIdFromPath(location.pathname);
  const [world, setWorld] = useState<WorldState | null>(null);
  const [control, setControl] = useState<WorldState | null>(null);
  const [treatment, setTreatment] = useState<WorldState | null>(null);
  const [branch, setBranch] = useState<Branch | null>(null);
  const [intervention, setIntervention] = useState<CentralIntervention | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [events, setEvents] = useState<SimulationEvent[]>([]);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<"idle" | "connecting" | "connected" | "reconnecting">("idle");
  const [hydrating, setHydrating] = useState(Boolean(routeId));
  const seen = useRef(new Set<string>());

  const profilesQuery = useQuery({ queryKey: ["province-profile-v4"], queryFn: policyScopeApi.listProvinces, staleTime: Infinity });
  const automakersQuery = useQuery({ queryKey: ["automaker-profile-v1"], queryFn: policyScopeApi.listAutomakers, staleTime: Infinity });
  const defaultPolicyQuery = useQuery({ queryKey: ["policy-v3"], queryFn: policyScopeApi.defaultPolicy, staleTime: Infinity });
  const healthQuery = useQuery({ queryKey: ["health-v3"], queryFn: policyScopeApi.health, staleTime: 30_000 });

  useEffect(() => {
    if (!routeId || world?.experiment_id === routeId) { setHydrating(false); return; }
    setHydrating(true); setError(null);
    void Promise.all([policyScopeApi.getState(routeId), policyScopeApi.listBranches(routeId)])
      .then(async ([nextWorld, branches]) => {
        const treatmentBranch = branches.find((item) => item.kind === "treatment") ?? null;
        const nextTreatment = treatmentBranch
          ? await policyScopeApi.getState(routeId, treatmentBranch.branch_id)
          : null;
        setWorld(nextWorld);
        setControl(nextWorld);
        setBranch(treatmentBranch);
        setTreatment(nextTreatment);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "推演加载失败"))
      .finally(() => setHydrating(false));
  }, [routeId, world?.experiment_id]);

  useEffect(() => {
    if (!world?.experiment_id || world.experiment_id !== routeId || world.status === "completed") { setConnectionStatus("idle"); return; }
    setConnectionStatus("connecting");
    const source = new EventSource(policyScopeApi.streamUrl(world.experiment_id));
    source.onopen = () => setConnectionStatus("connected");
    source.onerror = () => setConnectionStatus("reconnecting");
    const handler = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as SimulationEvent;
      if (seen.current.has(event.event_id)) return;
      seen.current.add(event.event_id); setEvents((items) => [...items.slice(-119), event]);
    };
    ["phase.completed", "province.decision.completed", "automaker.decision.completed", "province.feedback.completed", "central.intervention.proposed", "comparison.completed"].forEach((type) => source.addEventListener(type, handler as EventListener));
    return () => { source.close(); setConnectionStatus("idle"); };
  }, [routeId, world?.experiment_id, world?.status]);

  const execute = useCallback(async <T,>(label: string, operation: () => Promise<T>) => {
    setBusyLabel(label); setError(null);
    try { return await operation(); } catch (reason) { setError(reason instanceof Error ? reason.message : "操作失败"); throw reason; } finally { setBusyLabel(null); }
  }, []);

  const createDraft = (objective: string, mode: RunMode) => execute("中央 Agent 正在生成政策草案…", async () => { const next = await policyScopeApi.createExperiment(objective, mode); setWorld(next); setControl(null); setTreatment(null); setBranch(null); setComparison(null); seen.current.clear(); setEvents([]); return next; });
  const approveDirective = (policy: Policy) => execute("正在提交人工审批…", async () => { if (!world) throw new Error("请先生成草案"); const next = await policyScopeApi.approveDirective(world.experiment_id, policy); setWorld(next); return next; });
  const runYearOne = () => execute("正在运行首年四季度与年末复盘…", async () => { if (!world) throw new Error("请先审批政策"); const next = await policyScopeApi.runExperiment(world.experiment_id, "YEAR1_REVIEW"); setWorld(next); return next; });
  const approveProposal = (proposalId: string, policy: Policy) => execute("正在批准干预并派生同源分支…", async () => { if (!world) throw new Error("请先完成首年复盘"); const approved = await policyScopeApi.approveIntervention(world.experiment_id, proposalId, policy); const created = await policyScopeApi.createBranch(world.experiment_id, approved.intervention_id); setIntervention(approved); setBranch(created); return created; });
  const rejectProposal = (proposalId: string, reason: string) => execute("正在保留原始方案…", async () => { if (!world) throw new Error("请先完成首年复盘"); const next = await policyScopeApi.rejectIntervention(world.experiment_id, proposalId, reason); setWorld(next); setBranch(null); return next; });
  const runComparison = () => execute("正在运行次年同源 A/B…", async () => { if (!world || !branch) throw new Error("请先批准干预并创建分支"); const [c, t] = await Promise.all([policyScopeApi.runExperiment(world.experiment_id, "Y2_Q4", "control"), policyScopeApi.runBranch(branch.branch_id)]); const result = await policyScopeApi.compare(world.experiment_id); setControl(c); setTreatment(t); setComparison(result); setWorld(c); return result; });
  const runSingleBranch = () => execute("正在运行原始方案次年…", async () => { if (!world) throw new Error("请先拒绝或批准干预"); const next = await policyScopeApi.runExperiment(world.experiment_id, "COMPLETE", "control"); setControl(next); setWorld(next); return next; });
  const loadComparison = useCallback(() => execute("正在加载 A/B 对照…", async () => { if (!world) throw new Error("尚未创建实验"); const result = await policyScopeApi.compare(world.experiment_id); const [c, t] = await Promise.all([policyScopeApi.getState(world.experiment_id, result.control_branch_id), policyScopeApi.getState(world.experiment_id, result.treatment_branch_id)]); setControl(c); setTreatment(t); setComparison(result); return result; }), [execute, world]);

  useEffect(() => {
    const controlReady = world?.phase === "Y2_Q4" || world?.phase === "COMPLETE";
    const treatmentReady = treatment?.phase === "Y2_Q4" || treatment?.phase === "COMPLETE";
    if (!location.pathname.endsWith("/compare") || !branch || !controlReady || !treatmentReady || comparison) return;
    void loadComparison().catch(() => undefined);
  }, [branch, comparison, loadComparison, location.pathname, treatment?.phase, world?.phase]);

  const loadEvidence = useCallback((id: string) => { if (!world) throw new Error("尚未创建实验"); return policyScopeApi.evidence(world.experiment_id, id); }, [world]);
  const resetExperiment = () => { setWorld(null); setControl(null); setTreatment(null); setBranch(null); setIntervention(null); setComparison(null); setEvents([]); setError(null); };

  return {
    profiles: profilesQuery.data ?? [], automakers: automakersQuery.data ?? [], defaultPolicy: defaultPolicyQuery.data ?? null,
    metadataLoading: profilesQuery.isLoading || automakersQuery.isLoading || defaultPolicyQuery.isLoading,
    metadataError: profilesQuery.error ?? automakersQuery.error ?? defaultPolicyQuery.error,
    configuredRunMode: healthQuery.data?.run_mode ?? "cache" as RunMode,
    world, control, treatment, branch, intervention, comparison, events, busyLabel, error, hydrating, connectionStatus,
    createDraft, approveDirective, runYearOne, approveProposal, rejectProposal,
    runComparison, runSingleBranch, loadComparison, loadEvidence, resetExperiment,
  };
}

export type PolicyScopeFlow = ReturnType<typeof usePolicyScope>;
