import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

import { m34Client } from "../api/m34Client";
import type { M34Comparison, M34Design, M34InteractionMarket, M34World, MacroTick } from "../m34Types";

function routeExperimentId(pathname: string) {
  return pathname.match(/^\/experiments\/([^/]+)\//)?.[1] ?? null;
}

function useM34Flow() {
  const location = useLocation();
  const routeId = routeExperimentId(location.pathname);
  const [world, setWorld] = useState<M34World | null>(null);
  const [market, setMarket] = useState<M34InteractionMarket | null>(null);
  const [comparison, setComparison] = useState<M34Comparison | null>(null);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: string) => {
    const next = await m34Client.state(id);
    setWorld(next);
    if (next.branches.control) setMarket(await m34Client.interactions(id));
    if (next.status === "completed") setComparison(await m34Client.comparison(id));
    return next;
  }, []);

  useEffect(() => {
    if (!routeId || world?.experiment_id === routeId) return;
    setBusyLabel("正在恢复季度实验…");
    void load(routeId).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "实验恢复失败")).finally(() => setBusyLabel(null));
  }, [load, routeId, world?.experiment_id]);

  useEffect(() => {
    if (!routeId || !world || world.status === "completed") return;
    const stream = new EventSource(m34Client.streamUrl(routeId));
    const refresh = () => { void load(routeId); };
    ["interaction.wave.completed", "environment.quarter.completed", "comparison.completed"].forEach((type) => stream.addEventListener(type, refresh));
    return () => stream.close();
  }, [load, routeId, world]);

  const execute = async <T,>(label: string, operation: () => Promise<T>) => {
    setBusyLabel(label); setError(null);
    try { return await operation(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "操作失败"); throw reason; }
    finally { setBusyLabel(null); }
  };
  const create = (text: string) => execute("正在生成政策解读…", async () => { const next = await m34Client.create(text); setWorld(next); return next; });
  const confirmInterpretation = () => execute("正在确认解读…", async () => { if (!world) throw new Error("请先创建实验"); const next = await m34Client.confirmInterpretation(world.experiment_id, world.interpretation); setWorld(next); return next; });
  const confirmDesign = (design: M34Design) => execute("正在冻结年度设计…", async () => { if (!world) throw new Error("请先确认解读"); const next = await m34Client.confirmDesign(world.experiment_id, design); setWorld(next); return next; });
  const confirmBaseline = () => execute("正在冻结同源基线…", async () => { if (!world) throw new Error("请先确认设计"); const metadata = await m34Client.baselineMetadata(); const next = await m34Client.confirmBaseline(world.experiment_id, metadata.data_version); setWorld(next); return next; });
  const run = (tick: MacroTick) => execute(`正在运行 ${tick}…`, async () => { if (!world) throw new Error("请先冻结基线"); const next = await m34Client.run(world.experiment_id, tick); setWorld(next); setMarket(await m34Client.interactions(world.experiment_id)); if (next.status === "completed") setComparison(await m34Client.comparison(world.experiment_id)); return next; });
  const reset = () => { setWorld(null); setMarket(null); setComparison(null); setError(null); };
  return { world, market, comparison, busyLabel, error, create, confirmInterpretation, confirmDesign, confirmBaseline, run, load, reset };
}

export type M34Flow = ReturnType<typeof useM34Flow>;
const Context = createContext<M34Flow | null>(null);
export function M34Provider({ children }: { children: ReactNode }) { return <Context.Provider value={useM34Flow()}>{children}</Context.Provider>; }
// eslint-disable-next-line react-refresh/only-export-components
export function useM34() { const value = useContext(Context); if (!value) throw new Error("M34Provider is missing"); return value; }
