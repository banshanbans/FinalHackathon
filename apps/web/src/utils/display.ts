import type { DataQuality, RunMode } from "../types";

export const RUN_MODE_LABELS: Record<RunMode, string> = {
  cache: "缓存模式",
  fake: "测试模式",
  live: "在线模型",
  fallback: "规则接管",
};

export const QUALITY_LABELS: Record<DataQuality, string> = {
  verified: "已核验",
  proxy: "代理数据",
  demo: "演示数据",
};

export const WORLD_STATUS_LABELS: Record<string, string> = {
  draft: "政策草案",
  awaiting_approval: "待审批",
  approved: "已审批",
  ready: "待运行",
  running: "运行中",
  awaiting_intervention: "待干预决策",
  branch_ready: "分支就绪",
  completed: "已完成",
  failed: "运行失败",
};

export function branchLabel(branchId: string) {
  if (branchId === "control") return "原始方案";
  if (branchId === "treatment") return "干预方案";
  return branchId.startsWith("treatment_") ? "干预方案" : branchId;
}
