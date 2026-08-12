import type {
  DataQuality,
  DecisionPosture,
  EnterpriseArchetype,
  InterprovincialStrategy,
  ProvinceConstraint,
  ProvincePersonaType,
  ProvincePriorityGoal,
  RunMode,
} from "../types";

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

export const PERSONA_TYPE_LABELS: Record<ProvincePersonaType, string> = {
  execution_driven: "执行攻坚型",
  fiscally_prudent: "财政审慎型",
  inclusive_diffusion: "普惠扩散型",
  technology_leap: "技术跃迁型",
  green_transition: "绿色转型型",
  regional_collaboration: "区域协同型",
};

export const PERSONA_AXIS_LABELS = {
  execution_drive: "执行驱动力",
  fiscal_prudence: "财政审慎度",
  sme_inclusiveness: "中小企业普惠倾向",
  technology_ambition: "技术跃迁倾向",
  green_priority: "绿色转型倾向",
  cooperation_orientation: "区域协同倾向",
} as const;

export const PRIORITY_GOAL_LABELS: Record<ProvincePriorityGoal, string> = {
  equipment_renewal: "设备更新",
  fiscal_sustainability: "财政可持续",
  sme_financing_access: "中小企业融资可达",
  digital_upgrade: "数字化升级",
  green_equipment_renewal: "绿色设备更新",
  cross_regional_coordination: "跨区域协同",
};

export const CONSTRAINT_LABELS: Record<ProvinceConstraint, string> = {
  fiscal_gap: "财政空间约束",
  financing_gap: "融资可得性约束",
  transition_pressure: "转型压力",
  weak_digital_base: "数字基础偏弱",
  employment_pressure: "就业稳定压力",
  industrial_concentration: "产业结构单一",
};

export const POSTURE_LABELS: Record<DecisionPosture, string> = {
  proactive: "积极推进",
  balanced: "平衡推进",
  cautious: "审慎推进",
};

export const STRATEGY_LABELS: Record<InterprovincialStrategy, string> = {
  collaborate: "合作联动",
  benchmark: "对标跟进",
  compete: "竞争争取",
  independent: "独立推进",
};

export const ARCHETYPE_LABELS: Record<EnterpriseArchetype, string> = {
  large_state_owned: "大型国有制造企业",
  large_private: "大型民营制造企业",
  technology_sme: "科技型中小企业",
  traditional_sme: "传统制造中小企业",
  high_energy_industrial: "高耗能工业企业",
  export_manufacturer: "出口制造企业",
};

export function branchLabel(branchId: string) {
  if (branchId === "control") return "原始方案";
  if (branchId === "treatment") return "干预方案";
  return branchId.startsWith("treatment_") ? "干预方案" : branchId;
}
