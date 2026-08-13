import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { policyScopeApi } from "../api/client";
import { v32Api } from "../api/v32Client";
import type { ComparisonV6, ExperimentDesign, PolicyInterpretation, SimulationRound, V32Event, WorldStateV6 } from "../v32Types";

function experimentId(pathname: string) { return pathname.match(/^\/experiments\/([^/]+)\//)?.[1] ?? null; }

function useV32Flow() {
  const location = useLocation();
  const routeId = experimentId(location.pathname);
  const [world, setWorld] = useState<WorldStateV6 | null>(null);
  const [comparison, setComparison] = useState<ComparisonV6 | null>(null);
  const [events, setEvents] = useState<V32Event[]>([]);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<"idle" | "connected" | "reconnecting">("idle");
  const seen = useRef(new Set<string>());
  const profilesQuery = useQuery({ queryKey: ["v32-province-profiles"], queryFn: policyScopeApi.listProvinces, staleTime: Infinity });
  const automakersQuery = useQuery({ queryKey: ["v32-automakers"], queryFn: policyScopeApi.listAutomakers, staleTime: Infinity });
  const eventTemplatesQuery = useQuery({ queryKey: ["v32-event-templates"], queryFn: policyScopeApi.listEventScenarios, staleTime: Infinity });
  const baselineQuery = useQuery({ queryKey: ["m29-baseline-metadata"], queryFn: v32Api.baselineMetadata, staleTime: Infinity });

  useEffect(() => {
    if (!routeId || world?.experiment_id === routeId) return;
    setBusyLabel("正在恢复实验状态…");
    void Promise.all([v32Api.state(routeId), v32Api.replay(routeId)])
      .then(([next, replay]) => { setWorld(next); setEvents(replay); replay.forEach((item) => seen.current.add(item.event_id)); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "实验恢复失败"))
      .finally(() => setBusyLabel(null));
  }, [routeId, world?.experiment_id]);

  useEffect(() => {
    if (!world || world.experiment_id !== routeId || world.status === "completed") return;
    const source = new EventSource(v32Api.streamUrl(world.experiment_id));
    source.onopen = () => setConnectionStatus("connected");
    source.onerror = () => setConnectionStatus("reconnecting");
    const handler = (message: MessageEvent<string>) => {
      const event = JSON.parse(message.data) as V32Event;
      if (seen.current.has(event.event_id)) return;
      seen.current.add(event.event_id);
      setEvents((items) => [...items.slice(-99), event]);
    };
    ["interpretation.generated", "interpretation.confirmed", "design.confirmed", "baseline.confirmed", "branches.created", "round.completed", "comparison.completed"].forEach((type) => source.addEventListener(type, handler as EventListener));
    return () => { source.close(); setConnectionStatus("idle"); };
  }, [routeId, world]);

  const execute = useCallback(async <T,>(label: string, operation: () => Promise<T>) => {
    setBusyLabel(label); setError(null);
    try { return await operation(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "操作失败"); throw reason; }
    finally { setBusyLabel(null); }
  }, []);

  const create = (text: string) => execute("正在生成政策解读…", async () => { const next = await v32Api.create(text); setWorld(next); setComparison(null); setEvents([]); seen.current.clear(); return next; });
  const confirmInterpretation = (value: PolicyInterpretation) => execute("正在确认政策解读…", async () => { if (!world) throw new Error("请先创建实验"); const next = await v32Api.confirmInterpretation(world.experiment_id, { ...value, status: "confirmed" }); setWorld(next); return next; });
  const confirmDesign = (value: ExperimentDesign) => execute("正在确认方案…", async () => { if (!world) throw new Error("请先确认解读"); const next = await v32Api.confirmDesign(world.experiment_id, value); setWorld(next); return next; });
  const confirmBaseline = () => execute("正在准备推演…", async () => { if (!world) throw new Error("请先确认实验设计"); if (!baselineQuery.data) throw new Error("数据尚未准备完成"); const next = await v32Api.confirmBaseline(world.experiment_id, baselineQuery.data.data_version); setWorld(next); return next; });
  const run = (round?: SimulationRound) => execute(round ? "正在推进推演…" : "正在完成推演…", async () => { if (!world) throw new Error("请先确认方案"); const next = await v32Api.run(world.experiment_id, round); setWorld(next); if (next.status === "completed") setComparison(await v32Api.compare(next.experiment_id)); return next; });
  const loadComparison = () => execute("正在生成结果对比…", async () => { if (!world) throw new Error("尚未创建实验"); const result = await v32Api.compare(world.experiment_id); setComparison(result); return result; });
  const reset = () => { setWorld(null); setComparison(null); setEvents([]); setError(null); seen.current.clear(); };

  return { world, comparison, events, busyLabel, error, connectionStatus, baselineMetadata: baselineQuery.data ?? null, profiles: profilesQuery.data ?? [], automakers: automakersQuery.data ?? [], eventTemplates: eventTemplatesQuery.data ?? [], metadataLoading: profilesQuery.isLoading || automakersQuery.isLoading || eventTemplatesQuery.isLoading || baselineQuery.isLoading, create, confirmInterpretation, confirmDesign, confirmBaseline, run, loadComparison, reset };
}

export type V32Flow = ReturnType<typeof useV32Flow>;
const Context = createContext<V32Flow | null>(null);
export function V32Provider({ children }: { children: ReactNode }) { return <Context.Provider value={useV32Flow()}>{children}</Context.Provider>; }
// eslint-disable-next-line react-refresh/only-export-components
export function useV32() { const value = useContext(Context); if (!value) throw new Error("V32Provider is missing"); return value; }
