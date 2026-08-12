export const SIMULATION_EVENT_TYPES = [
  "experiment.started", "province.persona.ready", "central.directive.completed",
  "central.directive.approved", "province.decision.completed",
  "automaker.decision.completed", "province.feedback.completed",
  "central.intervention.proposed", "central.intervention.approved",
  "central.intervention.rejected", "branch.created", "phase.completed",
  "comparison.completed",
] as const;

export const EVENT_LABELS: Record<string, string> = {
  "experiment.started": "实验已创建",
  "province.persona.ready": "省级实验画像已冻结",
  "central.directive.completed": "中央草案已生成",
  "central.directive.approved": "中央草案已审批",
  "province.decision.completed": "省级政策已生成",
  "automaker.decision.completed": "车企模拟响应已生成",
  "province.feedback.completed": "省级年末复盘已形成",
  "central.intervention.proposed": "中央干预建议已生成",
  "central.intervention.approved": "干预已获人工批准",
  "central.intervention.rejected": "用户保留原始方案",
  "branch.created": "同源干预分支已创建",
  "phase.completed": "季度阶段已完成",
  "comparison.completed": "同源 A/B 已结算",
};
